#  Authorship: {{{           
"""  
Written by: Dario C. Lewczyk
Based on ls336-ioc maintained by: fboariu
Date: 02/05/2026
"""
#}}}
from caproto.server import pvproperty, PVGroup
from caproto import ChannelType
import logging, asyncio, time
from os import environ

import pyvisa
from emmi.scpi import MagicScpi
import ls336_ioc.flags as fflg

logger = logging.getLogger(__name__)


class LakeShoreIoc(PVGroup): 
    main_state = pvproperty(value=False)

    # --- Temperatures (Celsius) ---
    TEMP_C = pvproperty(value=0.0, dtype=float, doc="Channel C temperature (°C)")
    TEMP_D = pvproperty(value=0.0, dtype=float, doc="Channel D temperature (°C)")

    # --- Output 3: setpoint, ramp, range, PID, heater output ---
    SETP3 = pvproperty(value=25.0, dtype=float, doc="Output 3 temperature setpoint (°C)")
    SETP3_RBV = pvproperty(value=0.0, dtype=float, doc="Output 3 setpoint readback (°C)")

    RAMP3 = pvproperty(value=0.0, dtype=float, doc="Output 3 ramp rate (°C/min)")
    RAMP3_ON = pvproperty(value = 0, dtype=int, doc = "Ramp enable for output 3 (0 =off, 1 = on)")
    RAMP3_ON_RBV = pvproperty(value = 0, dtype=int, doc = "Readback value for the ramp (0 =off, 1 = on)")
    RAMP3_RBV = pvproperty(value=0.0, dtype=float, doc="Output 3 ramp rate readback (°C/min)")

    RANGE3 = pvproperty(value=0, dtype=int, doc="Output 3 heater range (0=Off,1=On)")
    RANGE3_RBV = pvproperty(value=0, dtype=int, doc="Output 3 heater range readback")

    P3 = pvproperty(value=30.0, dtype=float, doc="Output 3 PID P")
    I3 = pvproperty(value=25.0, dtype=float, doc="Output 3 PID I")
    D3 = pvproperty(value=0.0, dtype=float, doc="Output 3 PID D")

    HEATER3_OUT = pvproperty(value=0.0, dtype=float, doc="Output 3 heater output (%)") # RB Val for heater
    MANUAL3_OUT = pvproperty(value=0.0, dtype=float, doc="Manual output percentage for a heater")
    MANUAL3_OUT_RBV = pvproperty(value=0.0, dtype=float)

    OUTMODE3 = pvproperty(
            value=1, dtype=int, 
            doc="Output 3 Mode switch: (0=OFF, 1 = PID, 2=Zone, 3=OpenLoop)"
    )
    OUTMODE3_RBV = pvproperty(value=1, dtype=int)

    ATUNE3 = pvproperty(value = 0, dtype=int, doc="Start autotune for loop 3 (0: P only, 1: PI, 2: PID)")
    ATUNE3_RBV = pvproperty(value= 0, dtype=int, doc = "Autotune status for loop 3")

    ATUNE3_TERM = pvproperty(value=0, dtype=int)
    """ 
    Returned <tuning status>,<output>,<error status>,<stage status>[term]
    Format n,n,n,nn
    <tuning status> <output> Remarks 0 = no active tuning, 1 = active tuning.
        Heater output of the control loop being tuned (if tuning):
        1 = output 1, 2 = output 2
    <error status> <stage status> 0 = no tuning error, 1 = tuning error
        Specifies the current stage in the Autotune process.
    If tuning error occurred, stage status represents stage
    that failed.
    If initial conditions are not met when starting the autotune 
    """
    TUNEST3_OUTPUT = pvproperty(value=0, dtype=int)

    TUNEST3_RBV = pvproperty(value=0, dtype=int) # EXPOSES Autotuning errors
    TUNEST3_STATUS = pvproperty(value=0, dtype=int)
    TUNEST3_STAGE = pvproperty(value=0, dtype=int)
    TUNEST3_ERROR = pvproperty(value=0, dtype=int)



    # keep your existing cryo/heater PVs etc. as needed...

    def __init__(self, prefix, dev=None, rman=None, motors=None):
        self.ls336 = self._init_device(dev, rman)
        self.prefix = prefix
        self._last_atune_mode = 2 # Defaults to PID
        super().__init__(prefix)

    def _init_device(self, dev=None, rman=None):
        if dev is None:
            dev = self.param_dev
        else:
            self.param_dev = dev

        if rman is None:
            rman = self.param_rman
        else:
            self.param_rman = rman

        ls336 = MagicScpi(
            device=dev,
            resource_manager=rman,
            device_conf={"read_termination": "\r\n", "write_termination": "\r\n"},
        )
        helo = ls336.kdev.query("*IDN?")
        if not helo.startswith("LSCI,MODEL336"):
            raise RuntimeError(f"Unexpected model string: {helo}")
        self.ls336_version = helo[30:]
        logger.info(f"Lake Shore Model 336 version: {self.ls336_version}")
        return ls336

    async def ls336_write(self, cmd: str):
        nr = self.ls336.kdev.write(cmd)
        tmp = len(cmd) + len(self.ls336.kdev.write_termination)
        if nr != tmp:
            raise RuntimeError(f"Error writing {cmd}: should have {tmp} bytes, were {nr}")

    async def ls336_query(self, cmd: str) -> str:
        nr = self.ls336.kdev.write(cmd)
        tmp = len(cmd) + len(self.ls336.kdev.write_termination)
        if nr != tmp:
            raise RuntimeError(f"Error writing {cmd}: should have {tmp} bytes, were {nr}")
        return self.ls336.kdev.read()

    async def status_query(self):
        status = {}

        # Use CRDG for Celsius
        input_queries = ("CRDG", "TLIMIT")
        heater_queries = ("HTR", "OUTMODE", "PID", "RAMP", "RANGE", "SETP")
        aoutput_queries = ("AOUT",)
        status_queries = ("OPST", "OPSTE", "OPSTR")

        for cmd in input_queries:
            for n in ["A", "B", "C", "D"]:
                ret = self.ls336.kdev.query(f"{cmd}? {n}")
                status[f"{cmd}{n}"] = ret

        for cmd in heater_queries:
            for n in [1, 2, 3, 4]:
                ret = self.ls336.kdev.query(f"{cmd}? {n}")
                status[f"{cmd}{n}"] = ret

        for cmd in aoutput_queries:
            for n in [3, 4]:
                ret = self.ls336.kdev.query(f"{cmd}? {n}")
                status[f"{cmd}{n}"] = ret

        for cmd in status_queries:
            ret = self.ls336.kdev.query(f"{cmd}?")
            status[cmd] = ret

        return status

    # --- Putters for Output 3 control ---

    @SETP3.putter
    async def SETP3(self, inst, val):
        await self.ls336_write(f"SETP 3,{float(val)}")

    @RAMP3.putter
    async def RAMP3(self, inst, val):
        # enable ramp, set rate
        await self.ls336_write(f"RAMP 3,1,{float(val)}")

    @RAMP3_ON.putter
    async def RAMP3_ON(self, inst, val):
        ramp_on_str, rate_str = (await self.ls336_query("RAMP? 3")).split(",")
        rate = float(rate_str)
        await self.ls336_write(f"RAMP 3,{int(val)},{rate}")

    @RANGE3.putter
    async def RANGE3(self, inst, val):
        await self.ls336_write(f"RANGE 3,{int(val)}")

    @P3.putter
    async def P3(self, inst, val):
        # read current I,D then write full PID
        pid = (await self.ls336_query("PID? 3")).split(",")
        _, I, D = pid
        await self.ls336_write(f"PID 3,{float(val)},{float(I)},{float(D)}")

    @I3.putter
    async def I3(self, inst, val):
        P, _, D = (await self.ls336_query("PID? 3")).split(",")
        await self.ls336_write(f"PID 3,{float(P)},{float(val)},{float(D)}")

    @D3.putter
    async def D3(self, inst, val):
        P, I, _ = (await self.ls336_query("PID? 3")).split(",")
        await self.ls336_write(f"PID 3,{float(P)},{float(I)},{float(val)}")
    @MANUAL3_OUT.putter
    async def MANUAL3_OUT(self, inst, val):
        pct = float(val)
        if pct <0 or pct > 100:
            raise ValueError("Manual output must be between 0 and 100")
        await self.ls336_write(f'MOUT 3,{pct}')

    @OUTMODE3.putter
    async def OUTMODE3(self, inst, val):
        mode = int(val)
        if mode not in (0, 1, 3):
            raise ValueError("OUTMODE3 must be 0 (OFF), 1 (PID), or 3 (OpenLoop)")
        # Keep input = 3 and powerup = 0 (default)
        await self.ls336_write(f'OUTMODE 3,{mode},3,0')

    @ATUNE3.putter
    async def ATUNE3(self, inst, val):
        mode = int(val)
        if mode in (0, 1, 2):
            # Store the mode so termination uses the same
            self._last_atune_mode = mode
            # Val is the mode
            await self.ls336_write(f"ATUNE 3,{mode}")
    @ATUNE3_TERM.putter
    async def ATUNE3_TERM(self, inst, val):
        if int(val) == 1:
            # First read active mode from ATUNE? 3
            raw = await self.ls336_query("ATUNE? 3")
            try:
                active_mode = int(raw.strip())
            except:
                active_mode = self._last_atune_mode
            # Terminate autotune and clear screen
            await self.ls336_write(f"ATUNE 3,{active_mode},0")  # or use last mode dynamically
            await self.ATUNE3_TERM.write(0)

    @main_state.scan(period=1.0)
    async def _update(self, inst, async_lib):
        # --- Fast-changing values ---
        temp_c = float(await self.ls336_query("CRDG? C"))
        temp_d = float(await self.ls336_query("CRDG? D"))
        setp3 = float(await self.ls336_query("SETP? 3")) 
        ramp3 = await self.ls336_query("RAMP? 3")
        htr3 = float(await self.ls336_query("HTR? 3"))
    
        await self.TEMP_C.write(temp_c)
        await self.TEMP_D.write(temp_d)
        await self.SETP3_RBV.write(setp3)
    
        ramp_on, ramp_rate = ramp3.split(",") 
        await self.RAMP3_RBV.write(float(ramp_rate))
        await self.RAMP3_ON_RBV.write(int(ramp_on))
    
        await self.HEATER3_OUT.write(htr3)
    
        # --- Slow-changing values (every 10 seconds) ---
        now = time.time()
        if not hasattr(self, "_last_slow_update"):
            self._last_slow_update = 0
    
        if now - self._last_slow_update > 10:
            # Autotune safety: 
            raw = (await self.ls336_query("ATUNE? 3")).strip()
            atune_status = int(raw) if raw else 0

            range3 = int(await self.ls336_query("RANGE? 3"))
            pid3 = await self.ls336_query("PID? 3")
            P, I, D = map(float, pid3.split(","))


            outmode = await self.ls336_query("OUTMODE? 3")
            mode, inp, pwr = map(int, outmode.split(','))
            mout = float(await self.ls336_query("MOUT? 3"))

            tunest_raw = await self.ls336_query("TUNEST? 3")
            status_str, output_str, error_str, stage_str = tunest_raw.split(",")

            status = int(status_str)
            output = int(output_str)
            error = int(error_str)
            stage = int(stage_str)
          
            await self.RANGE3_RBV.write(range3)
            await self.ATUNE3_RBV.write(atune_status)
            await self.P3.write(P)
            await self.I3.write(I)
            await self.D3.write(D)
            await self.OUTMODE3_RBV.write(mode)
            await self.MANUAL3_OUT_RBV.write(mout)

            # You can expose all four, or just the status 
            await self.TUNEST3_STATUS.write(status)
            await self.TUNEST3_OUTPUT.write(output)
            await self.TUNEST3_ERROR.write(error)
            await self.TUNEST3_STAGE.write(stage)
    
            self._last_slow_update = now
    
