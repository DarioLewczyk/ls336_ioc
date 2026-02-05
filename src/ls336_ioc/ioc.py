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
    RAMP3_RBV = pvproperty(value=0.0, dtype=float, doc="Output 3 ramp rate readback (°C/min)")

    RANGE3 = pvproperty(value=0, dtype=int, doc="Output 3 heater range (0=Off,1=On)")
    RANGE3_RBV = pvproperty(value=0, dtype=int, doc="Output 3 heater range readback")

    P3 = pvproperty(value=30.0, dtype=float, doc="Output 3 PID P")
    I3 = pvproperty(value=25.0, dtype=float, doc="Output 3 PID I")
    D3 = pvproperty(value=0.0, dtype=float, doc="Output 3 PID D")

    HEATER3_OUT = pvproperty(value=0.0, dtype=float, doc="Output 3 heater output (%)")

    # keep your existing cryo/heater PVs etc. as needed...

    def __init__(self, prefix, dev=None, rman=None, motors=None):
        self.ls336 = self._init_device(dev, rman)
        self.prefix = prefix
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

    @main_state.scan(period=1.0)
    async def _update(self, inst, async_lib):
        status = await self.status_query()

        # Temps (C)
        await self.TEMP_C.write(float(status["CRDGC"]))
        await self.TEMP_D.write(float(status["CRDGD"]))

        # Output 3 setpoint, ramp, range, PID, heater
        await self.SETP3_RBV.write(float(status["SETP3"]))
        ramp_on, ramp_rate = status["RAMP3"].split(",")
        await self.RAMP3_RBV.write(float(ramp_rate))
        await self.RANGE3_RBV.write(int(status["RANGE3"]))

        P, I, D = status["PID3"].split(",")
        await self.P3.write(float(P))
        await self.I3.write(float(I))
        await self.D3.write(float(D))

        await self.HEATER3_OUT.write(float(status["HTR3"]))

