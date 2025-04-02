## SPI TFT IPS

For Radxa Rock 5C Lite

2.0 inch TFT Display OLED LCD Drive IC ST7789V 240RGBx320 Dot-Matrix SPI Interface for Arduio Full Color LCD Display Module

https://gist.github.com/c0m4r/b3fea6342bcf5a1b25b608fc36100d68#SPI-TFT-IPS

```
apt install python3-numpy python3-pip python3-spidev python3-venv python3-wheel libgpiod2 python3-libgpiod
python3 -m venv venv
source venv/bin/activate
pip install Pillow numpy spidev gpiod
python3 display_st7789_v4.py --image example.jpg  --dc-pin 140 --rst-pin 37 --gpio-chip-dc /dev/gpiochip4 --gpio-chip-rst /dev/gpiochip1
python3 display_st7789_v4.py --text "Hello world" --font "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf" --fontsize 36 --dc-pin 140 --rst-pin 37 --gpio-chip-dc /dev/gpiochip4 --gpio-chip-rst /dev/gpiochip1
```

Overlay: /boot/dtbo/rk3588-spi0-m1-cs0-spidev.dtbo

Debug:

```bash
dmesg | grep -i spi
gpiodetect
gpioinfo
ls -la /dev/spidev0.0
```
