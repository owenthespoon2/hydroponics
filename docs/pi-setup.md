# Raspberry Pi setup (headless)

Run-book for setting up the Pi 4 Model B that does the camera, logging and remote access. See [heating-project.md](heating-project.md) for what it is for and [wiring-diagrams.md](wiring-diagrams.md) for the wiring.

## What I'm using
- **Board:** Raspberry Pi 4 Model B (2018 board). It has built-in dual-band Wi-Fi and Bluetooth, so no Wi-Fi module is needed.
- **Card:** Amazon Basics 64 GB microSDXC (V30, U3). The 2 GB SanDisk card is too small for the OS.
- **Reader:** Kingston USB microSD reader, plugged into my computer.
- **Camera:** Raspberry Pi Camera Module V2.1 on the ribbon cable.
- **Power:** a plain 5 V / 3 A USB-C supply. Avoid e-marked laptop cables on an early Pi 4, which can fail to power it.

## 1. Write the card
1. Install **Raspberry Pi Imager** on my computer (from raspberrypi.com/software).
2. Choose the Pi 4, then **Raspberry Pi OS Lite (64-bit)** (no desktop needed), then the 64 GB card.
3. Fill in the customisation screen before writing:
   - hostname: `hydro-pi`
   - my own username and a strong password
   - Wi-Fi name and password, Wi-Fi country **JP**
   - time zone **Asia/Tokyo**
   - enable **SSH**
4. Write. Imager verifies the card when it finishes.

## 2. First boot
1. Put the card in the Pi. Do not connect the camera or any wiring yet. Power on.
2. Wait a few minutes, then from my computer: `ssh <username>@hydro-pi.local`
3. Update: `sudo apt update && sudo apt full-upgrade -y`, then `sudo reboot`.

## 3. Remote access that survives travel
Install **Tailscale** so I can reach the Pi from anywhere without opening any port on my router:
```
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh
```
Then check I can SSH to it from my phone or laptop while **off** the home Wi-Fi.

## 4. Turn on the probe interface
Power off first, then wire the DS18B20 per [wiring-diagrams.md](wiring-diagrams.md). Then:
1. Add this line to `/boot/firmware/config.txt`: `dtoverlay=w1-gpio`
2. Reboot, then `ls /sys/bus/w1/devices/`. A folder starting with `28-` is the probe.
3. `cat /sys/bus/w1/devices/28-*/w1_slave` shows the temperature (the number after `t=` is thousandths of a degree).

## 5. Camera
1. Power off. Peel the protective film off the lens. Fit the ribbon into the camera port (between the HDMI ports and the audio jack) with the contacts facing the HDMI side. Check against the official camera guide before powering on.
2. Boot, then `rpicam-hello --list-cameras` should list the camera.
3. `rpicam-still -o test.jpg` takes a photo.

## 6. Make it survive three weeks alone
- Clone the finished card once to an image file, so a corrupted card can be replaced in minutes.
- Keep writes low: log to RAM and flush in batches, and don't keep every photo on the card.
- Make sure it comes back by itself after a power cut (services enabled at boot).
- Confirm the whole chain still works after pulling the power and plugging it back in.

## Checklist
| Step | Done |
| :--- | :--- |
| Card written, Pi boots, SSH works | [ ] |
| Updated | [ ] |
| Tailscale works from off the home network | [ ] |
| Probe reads temperature | [ ] |
| Camera takes a photo | [ ] |
| Card image backed up | [ ] |
| Power-cut test passed | [ ] |
