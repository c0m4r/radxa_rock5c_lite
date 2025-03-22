#!/usr/bin/env python3

from periphery import I2C
from PIL import Image, ImageDraw, ImageFont
import textwrap
import time
import sys

class i2c_oled:
    def __init__(self, bus="/dev/i2c-8", address=0x3C):
        self.bus = bus
        self.address = address
        self.i2c = I2C(self.bus)
        self.width = 128
        self.height = 64
        self.font = ImageFont.truetype("/usr/share/fonts/truetype/pixelmix.ttf", 16)
        self.font2 = ImageFont.truetype("/usr/share/fonts/truetype/pixelmix.ttf", 14)

        self.initialize_oled()

    def ssd1306_command(self, cmd):
        msg = I2C.Message([0x00, cmd])
        self.i2c.transfer(self.address, [msg])

    def initialize_oled(self):
        commands = [
            0xAE, 0xD5, 0x80, 0xA8, 0x3F, 0xD3, 0x00, 0x40 | 0x0,
            0x8D, 0x14, 0x20, 0x00, 0xA1, 0xC8, 0xDA, 0x12,
            0x81, 0xCF, 0xD9, 0xF1, 0xDB, 0x40, 0xA4, 0xA6, 0xAF
        ]
        for cmd in commands:
            self.ssd1306_command(cmd)
        self.clear_display()

    def clear_display(self):
        for i in range(8):
            self.ssd1306_command(0xB0 + i)
            self.ssd1306_command(0x00)
            self.ssd1306_command(0x10)
            for j in range(self.width):
                msg = I2C.Message([0x40, 0x00])
                self.i2c.transfer(self.address, [msg])

    def display_text(self, text, text2):
        image = Image.new("1", (self.width, self.height))
        draw = ImageDraw.Draw(image)

        lines = textwrap.wrap(text, width=20)
        lines2 = textwrap.wrap(text2, width=20)

        y = 0
        for line in lines:
            if y > self.height - 8:
                break
            draw.text((0, y), line, font=self.font, fill=255)
            y += 8
        y = 40
        for line in lines2:
            if y > self.height - 8:
                break
            draw.text((0, y), line, font=self.font2, fill=255)
            y += 8

        for page in range(8):
            self.ssd1306_command(0xB0 + page)
            self.ssd1306_command(0x00)
            self.ssd1306_command(0x10)
            for col in range(self.width):
                byte = 0
                for bit in range(8):
                    pixel = image.getpixel((col, page * 8 + bit))
                    if pixel:
                        byte |= (1 << bit)
                msg = I2C.Message([0x40, byte])
                self.i2c.transfer(self.address, [msg])

    def close(self):
        self.i2c.close()

# Execute

oled = i2c_oled()
oled.display_text(sys.argv[1], sys.argv[2])
# time.sleep(5)
# oled.clear_display()
# oled.close()
