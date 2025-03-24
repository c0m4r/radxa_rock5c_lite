# I2C OLED 128x32 scripts

Tested on Radxa OS / Debian 12 (bookworm) | Python 3.11

| script | description |
| ---- | ---- |
| i2c_oled_clock.py | Full display clock (HH:MM:SS) |
| i2c_oled_heart.py | draws a heart in the center of the display |
| i2c_oled_internet_radio.py | let's you listen to the internet radio and prints icy-title on the display |
| i2c_oled_monitoring.sh | system monitoring (temperature, CPU/MEM usage, current IP address, time, etc. |
| i2c_oled_pacman.py | Pacman animation based on png files |
| i2c_oled_text_long.py | Long text with auto-wraping |
| i2c_oled_text_sequence.py | Text sequence |
| i2c_oled_text_side_scroll.py | Side scrolling text |
| i2c_oled_text_vertical.py | Use of the display in the vertical position |

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

or

```
mv /boot/dtbo/rk3588-i2c8-m2.dtbo.disabled /boot/dtbo/rk3588-i2c8-m2.dtbo
u-boot-update
reboot
```

### Step 2 - Install Python's dependencies

Radxa OS / Debian / Ubuntu:

```
sudo apt install python3-venv python3-wheel python3-pip
```

Arch Linux:

```
sudo pacman -S python-virtualenv python-wheel python-pip
```

and then:


```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Internet radio script also depends on `libportaudio2`, `mpv` and `pulseaudio` (or another sound server) and possibly `ffmpeg`.

Radxa OS / Debian / Ubuntu:

```
sudo apt install libportaudio2 mpv pulseaudio
```

Arch Linux:

```
sudo pacman -S portaudio python-pyaudio mpv pulseaudio
```

### Notes

- Don't run rsetup while in python's venv, it won't work properly.
- Press CTRL + C to exit any of the scripts
