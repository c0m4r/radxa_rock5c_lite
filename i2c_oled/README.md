# I2C OLED 128x32 scripts

Tested on Radxa OS / Debian 12 (bookworm) | Python 3.11

## How to

Connect OLED SDA/SCL to Pins 3/5, choose pin 1 or 17 for 3.3V and any ground pins. Don't connect anything to the red +5V or else you gonna fry the OLED module.

See:

- [I2C OLED](https://gist.github.com/c0m4r/b3fea6342bcf5a1b25b608fc36100d68#I2C-OLED)
- [GPIO Pinout](https://docs.radxa.com/en/rock5/rock5c/hardware-design/hardware-interface?target=rk3582#gpio-pinout)

## Setup

### Step 1 - Enable I2C Overlay

```
rsetup # Overlays => Yes => Manage overlays => Select "Enable I2C8-M2" => Ok => Ok => Cancel => Cancel
reboot
```

### Step 2 - Install Python's dependencies

```
apt install python3-venv python3-wheel python3-pip
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Internet radio script also depends on `libportaudio2`, `mpv` and `pulseaudio` (or another sound server) and possibly `ffmpeg`.

### Notes

- Don't run rsetup while in python's venv, it won't work properly.
- Press CTRL + C to exit any of the scripts
