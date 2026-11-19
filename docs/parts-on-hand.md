# Parts on hand (2026-11-19)

What I already own that could go into the build. Identified from photos on 2026-11-19. Anything marked "confirm" still needs checking against the board or part itself.

![Parts overview](images/parts-overview-2026-11-19.jpg)

## Computers and controllers
| Item | Notes | Confirm |
| :--- | :--- | :--- |
| Raspberry Pi 4 Model B | Board marked "Raspberry Pi 4 Model B © 2018". Blue heatsink. Red 3D-printed case. USB-C power. | RAM size |
| Raspberry Pi, original Model B | Has RCA video and 2 USB ports. No Wi-Fi. Very slow, unlikely to be useful. | |
| Third Raspberry Pi | Looks like a Pi 3 Model B (4 USB, full-size HDMI, micro-USB power). | Model, printed on the board |
| Arduino Uno | ATmega328P in a socket. 5 V logic. | Works with a blink test |
| Pro Micro (ATmega32U4) | Micro-USB. Small. | 5 V/16 MHz or 3.3 V/8 MHz variant |
| ESP32-CAM | OV2640 camera, microSD slot, no USB port (needs a USB-serial adapter to program). | Whether I have a USB-serial adapter |

## Sensors and modules
| Item | Notes | Confirm |
| :--- | :--- | :--- |
| DS18B20 waterproof probes (2-pack) | Bought for this project. Came with PlugableTerminal V1738 adapter boards (4.7 kΩ pull-up built in). Probe 1 working on GPIO 4 since 2026-11-19. | |
| Raspberry Pi Camera Module V2.1 + ribbon | IMX219 sensor. Working in the Pi 4's CAMERA slot since 2026-11-20. | |
| Ultrasonic distance sensor, HC-SR04 | Possible reservoir level sensor later. Echo pin is 5 V: needs a voltage divider for the Pi. [Photo](images/hc-sr04.jpg) | |
| DHT11 temperature and humidity module | 3-pin module. Air temperature and humidity near the plants, later. [Photo](images/dht11-module.jpg) | |
| Soil/moisture sensor | Not photographed. Probably not needed. | Resistive or capacitive |
| Adafruit Ultimate GPS breakout v3 | Not needed for this project. | |
| Waveshare 2.8 inch RPi LCD (320×240, touch, 4 buttons) | Optional local display on a Pi. | |

## Switching and power
| Item | Notes | Confirm |
| :--- | :--- | :--- |
| Small 5 V relay modules (new, from Amazon) | For switching the 5 V USB heater. | Contact rating (heater needs about 2 A at 5 V), and whether the board has a driver transistor or optocoupler |
| 2-channel relay module, BTE13-003 | Two SONGLE-style JQX-3F 5 V relays, 10 A at 30 V DC contacts. PC817 optocoupler inputs, Vcc/RVcc jumper (JD-VCC). Chosen for the heater. Used on 5 V DC only, never mains. [Photo](images/relay-2ch-bte13-003.jpg) | Active-low (expected), bench test |
| USB Type-A female breakout boards (10-pack) | For wiring the heater's USB plug to the relay and power supply. Bare holes: need header pins soldered or wires soldered in. [Photo](images/usb-a-breakouts.jpg) | |
| Pi GPIO screw-terminal breakout board | Wires a Pi's 40-pin header to screw terminals without soldering. | |
| microSD card, Amazon Basics 64 GB (microSDXC, V30, U3) | For the Pi's operating system. | |
| microSD card, SanDisk 2 GB | Too small for the Pi OS. | |
| Kingston USB microSD reader | For writing the Pi's card from my computer. | |
| 40 mm fan | For Pi cooling if needed. | |
| Jumper wires | Plenty. | |

## Rule for this build
The heater is a 5 V DC device. Nothing in the heating project needs to touch mains voltage. Keep it that way.
