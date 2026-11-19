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
  |  Pin 2 (5V) -------------> [5V Relay VCC]                 |     |
  |  Pin 6 (GND) ------------> [5V Relay GND]                 |     |
  |  Pin 11 (GPIO 17) -------> [5V Relay IN]                  |     |
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
| **5V Relay Module** | `VCC` | Pi Physical Pin 2 (`5V`) | Relay coil power |
| **5V Relay Module** | `GND` | Pi Physical Pin 6 (`GND`) | Common ground |
| **5V Relay Module** | `IN` | Pi Physical Pin 11 (`GPIO 17`) | Control signal |
| **USB Breakout** | `VBUS (+5V)` | Relay `NO` (Normally Open) | Switched 5V positive line |
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
