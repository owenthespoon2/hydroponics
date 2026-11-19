# ⚡ Wiring Diagrams & Thermal Bath Safety

Hardware integration guide for the **Phase 2 Raspberry Pi Thermostat & Monitoring Rig**.

---

## 1. Circuit Schematic

```text
                       RASPBERRY PI (3.3V Logic)
  +-----------------------------------------------------------------+
  |  Pin 1 (3.3V) --------+-----------------------------------+     |
  |  Pin 7 (GPIO 4) ------+---[DS18B20 Adapter Board]         |     |
  |  Pin 9 (GND) ---------+       (4.7kΩ Built-in)            |     |
  |                                   |                       |     |
  |                                   v                       |     |
  |                        [Waterproof DS18B20 Probe]         |     |
  |                         (Submerged in Water Bath)         |     |
  |                                                           |     |
  |  Pin 17 (3.3V) -----------> [Relay Vcc  (logic side)]     |     |
  |  Pin 29 (GPIO 5) ---------> [Relay In1]                   |     |
  |  Pin 14 (GND) ------------> [Relay Gnd  (input header)]   |     |
  |  Pin 2 (5V) --------------> [Relay RVcc (coil, jumper off)]     |
  |  Pin 6 (GND) -------------> [Relay Gnd  (jumper header)]  |     |
  +-----------------------------------------------------------------+
                                     |
                          (Isolated Dry Contacts)
                                     |
  [5V 2A USB Wall Adapter]           v
        |                     +-------------+
        +--- (+5V VBUS) ----->| COM      NO |----+
        |                     +-------------+    |
        |                                        v
        |                            +-----------------------+
        |                            | USB Type-A Breakout   |
        |                            |  [VBUS]  [D-] [D+] [G]|
        +--- (GND) ----------------->|   |                 | |
                                     +---|-----------------|-+
                                         |                 |
                                         +--------+--------+
                                                  |
                                         [10W 5V USB Heater]
                                         (Submerged in Bath)
```

---

## 2. Pinout Summary

| Component | Pin / Wire | Connects To | Notes |
| :--- | :--- | :--- | :--- |
| **DS18B20 Adapter** | `VCC` | Pi Physical Pin 1 (`3.3V`) | Uses 3.3V logic safely |
| **DS18B20 Adapter** | `DAT` | Pi Physical Pin 7 (`GPIO 4`) | Default Linux 1-Wire pin |
| **DS18B20 Adapter** | `GND` | Pi Physical Pin 9 (`GND`) | Common ground |
| **Relay (BTE13-003)** | `Vcc` (input header) | Pi Physical Pin 17 (`3.3V`) | Logic side at 3.3 V so a HIGH pin fully switches the optocoupler off |
| **Relay (BTE13-003)** | `In1` | Pi Physical Pin 29 (`GPIO 5`) | GPIO 5 is pulled HIGH at power-on, so an active-low relay stays OFF while the Pi boots |
| **Relay (BTE13-003)** | `Gnd` (input header) | Pi Physical Pin 14 (`GND`) | |
| **Relay (BTE13-003)** | `RVcc` (jumper removed) | Pi Physical Pin 2 (`5V`) | Relay coil power (~70 mA per relay) |
| **Relay (BTE13-003)** | `Gnd` (jumper header) | Pi Physical Pin 6 (`GND`) | |
| **USB Breakout** | `VBUS (+5V)` | Relay 1 `NO` (Normally Open) | Switched 5V positive line. Relay 1 `COM` goes to the PSU +5V. Never use `NC`: the heater must be off when the relay is unpowered |
| **USB Breakout** | `GND` | Dedicated 5V 2A PSU `GND` | Do NOT draw heater current from Pi |

---

## 3. Thermal Water Bath Physics & Safety Rules

1. **Maintain 5–6 cm Bath Depth (Anti-Float Rule):**
   * The outer Daiso tub measures `35 × 25 × 16 cm`.
   * Keep bath water at **5–6 cm** (just enough to fully submerge the 10W heater lying flat).
   * *Why:* Over 3 weeks, plants drink down the liquid inside their jars, making them lighter. Water deeper than 7–8 cm will cause half-empty jars to float and tip over.
2. **Cover the Bath Surface (Anti-Evaporation & Heat Trap):**
   * Cover open water gaps around the jars with a cut lid, aluminum foil, or cling film.
   * Reduces evaporation over 3 weeks so the heater stays submerged, boosts thermal efficiency of the 10W heater, and blocks light from growing algae in the bath.
3. **Account for Thermal Lag (1°C – 2°C Offset):**
   * Heat conducts through the plastic jar walls into the nutrient solution.
   * Target **22.0°C – 25.0°C** in the outer bath so the inner root zone stays around **20.0°C – 23.0°C**.
4. **Software Hysteresis + Hardware Fail-Safe:**
   * Program a hysteresis band (e.g., `ON <= 20.0°C`, `OFF >= 24.0°C`) so the mechanical relay does not chatter.
   * The DONGFANGB heater's listing claims an internal **26°C cutoff** and an **out-of-water dry-run shutoff** as a hardware failsafe if the Pi crashes. **Not yet verified.** Test both before relying on them (see [heating-project.md](heating-project.md)).
5. **Check the relay's trigger logic.** Many 5 V relay modules switch on a LOW signal (active-low). Confirm which yours is on the bench, with the heater unplugged, before writing the thermostat code, and make sure the "safe" state at boot and on a crash is heater off.
6. **Relay pin and boot state (decided 2026-11-20).** The relay input moved from GPIO 17 to **GPIO 5** (pin 29). GPIO 17 is pulled LOW at power-on, which an active-low relay could read as "on" while the Pi boots. GPIO 5 is pulled HIGH. As a second layer, `/boot/firmware/config.txt` gets `gpio=5=op,dh` so the firmware drives it HIGH (relay off) before Linux even starts.
7. **Why the Vcc/RVcc jumper comes off.** With the jumper on, the optocoupler LED is fed from 5 V, and a 3.3 V HIGH from the Pi may not switch it fully off (relay chatters or stays on). With the jumper off, the logic side runs at 3.3 V and the coil at 5 V.
