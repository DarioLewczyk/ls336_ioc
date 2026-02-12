# Lake Shore 336 EPICS IOC  
A lightweight EPICS IOC for controlling **Output 3** of a Lake Shore Model 336 temperature controller using SCPI commands over VISA.

This IOC exposes a clean set of PVs for temperature readback, PID control, heater output, ramping, and autotuning.  
All PVs map directly to LS336 SCPI commands, shown explicitly below.

---

## 📡 Overview

The IOC communicates with the LS336 using `MagicScpi` and polls the instrument at two rates:

- **Fast loop (1 Hz)**  
  - Temperatures  
  - Setpoint  
  - Ramp state  
  - Heater output  

- **Slow loop (10 s)**  
  - PID parameters  
  - Output mode  
  - Manual output  
  - Autotune status (`ATUNE?`)  
  - Autotune diagnostics (`TUNEST?`)  

Autotune termination is supported via `ATUNE 3,<mode>,0`.

---

# 📘 PV → SCPI Command Mapping

Each PV below corresponds directly to a Lake Shore 336 SCPI command.  
This table reflects the IOC implementation exactly.

---

## 🔥 Temperatures (Celsius)

| PV Name | Description | SCPI Command | Direction |
|--------|-------------|--------------|-----------|
| `LS336:TEMP_C` | Channel C temperature | `CRDG? C` | Read |
| `LS336:TEMP_D` | Channel D temperature | `CRDG? D` | Read |

---

## 🔧 Output 3 — Setpoint, Ramp, Range, PID, Heater Output

### Setpoint

| PV | Description | SCPI | Dir |
|----|-------------|------|-----|
| `LS336:SETP3` | Write setpoint | `SETP 3,<value>` | Write |
| `LS336:SETP3_RBV` | Readback | `SETP? 3` | Read |

---

### Ramp

| PV | Description | SCPI | Dir |
|----|-------------|------|-----|
| `LS336:RAMP3` | Set ramp rate (enables ramp) | `RAMP 3,1,<rate>` | Write |
| `LS336:RAMP3_RBV` | Ramp rate readback | `RAMP? 3` → field 2 | Read |
| `LS336:RAMP3_ON` | Enable/disable ramp | `RAMP 3,<0/1>,<rate>` | Write |
| `LS336:RAMP3_ON_RBV` | Ramp enable readback | `RAMP? 3` → field 1 | Read |

---

### Heater Range

| PV | Description | SCPI | Dir |
|----|-------------|------|-----|
| `LS336:RANGE3` | Heater range | `RANGE 3,<0/1>` | Write |
| `LS336:RANGE3_RBV` | Range readback | `RANGE? 3` | Read |

---

### PID Parameters

| PV | Description | SCPI | Dir |
|----|-------------|------|-----|
| `LS336:P3` | Proportional gain | `PID 3,P,I,D` | Write |
| `LS336:I3` | Integral gain | `PID 3,P,I,D` | Write |
| `LS336:D3` | Derivative gain | `PID 3,P,I,D` | Write |
| *(implicit)* | PID readback | `PID? 3` | Read |

---

### Heater Output

| PV | Description | SCPI | Dir |
|----|-------------|------|-----|
| `LS336:HEATER3_OUT` | Heater output (%) | `HTR? 3` | Read |
| `LS336:MANUAL3_OUT` | Manual output write | `MOUT 3,<pct>` | Write |
| `LS336:MANUAL3_OUT_RBV` | Manual output readback | `MOUT? 3` | Read |

---

### Output Mode

| PV | Description | SCPI | Dir |
|----|-------------|------|-----|
| `LS336:OUTMODE3` | Output mode | `OUTMODE 3,<mode>,3,0` | Write |
| `LS336:OUTMODE3_RBV` | Mode readback | `OUTMODE? 3` | Read |

Modes supported:  
- `0` = Off  
- `1` = PID  
- `3` = Open Loop (Manual)

---

# 🧠 Autotune (Loop 3)

### Start / Status / Termination

| PV | Description | SCPI | Dir |
|----|-------------|------|-----|
| `LS336:ATUNE3` | Start autotune | `ATUNE 3,<mode>` | Write |
| `LS336:ATUNE3_RBV` | Autotune active? | `ATUNE? 3` | Read |
| `LS336:ATUNE3_TERM` | Terminate autotune | `ATUNE 3,<mode>,0` | Write |

---

### Autotune Diagnostics (`TUNEST?`)

`TUNEST? 3` returns:  

