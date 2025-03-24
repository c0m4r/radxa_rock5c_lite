#!/usr/bin/env python3
"""
Clock | OLED I2C [128x32] @ Radxa Rock 5C Lite
Author: Deepseek R1 + https://github.com/c0m4r
License: Public Domain
"""

from datetime import datetime
from time import sleep

from periphery import I2C
from PIL import Image, ImageDraw, ImageFont

class OLEDi2c:
    """A class to control SSD1306-based OLED displays over I2C."""

    def __init__(self, bus: str = "/dev/i2c-8", address: int = 0x3C) -> None:
        """Initialize the OLED display controller."""
        self.bus = bus
        self.address = address
        self.i2c = I2C(self.bus)
        self.width = 128
        self.height = 32
        self.font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        self.font_size = 29
        self.initialize_oled()

    def ssd1306_command(self, cmd: int) -> None:
        """Send a single command to the SSD1306 controller."""
        msg = I2C.Message([0x00, cmd])
        self.i2c.transfer(self.address, [msg])

    def initialize_oled(self) -> None:
        """Initialize the display with required configuration commands."""
        contrast_bit: int = 0x00  # 0x00 = dim, 0xCF = bright
        commands = [
            0xAE, 0xD5, 0x80, 0xA8, 0x1F, 0xD3, 0x00, 0x40,
            0x8D, 0x14, 0x20, 0x00, 0xA1, 0xC8, 0xDA, 0x02,
            0x81, contrast_bit, 0xD9, 0xF1, 0xDB, 0x40, 0xA4, 0xA6, 0xAF
        ]
        for cmd in commands:
            self.ssd1306_command(cmd)
        self.clear_display()

    def clear_display(self) -> None:
        """Clear the display."""
        for page in range(4):
            self.ssd1306_command(0xB0 + page)
            self.ssd1306_command(0x00)
            self.ssd1306_command(0x10)
            msg = I2C.Message([0x40] + [0x00] * 128)
            self.i2c.transfer(self.address, [msg])

    def display(self) -> None:
        """Display the current time on the OLED."""
        image = Image.new("1", (self.width, self.height))
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(self.font_path, self.font_size)
        text = datetime.now().strftime('%H:%M:%S')

        # Calculate centered text position
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (self.width - text_width) // 2 - bbox[0]
        y = (self.height - text_height) // 2 - bbox[1]

        draw.text((x, y), text, font=font, fill=1)

        # Send image data to display
        for page in range(4):
            self.ssd1306_command(0xB0 + page)
            self.ssd1306_command(0x00)
            self.ssd1306_command(0x10)
            page_data = [0] * 128
            for col in range(self.width):
                byte = 0
                for bit in range(8):
                    try:
                        pixel = image.getpixel((col, page * 8 + bit))
                    except IndexError:
                        pixel = 0
                    byte |= pixel << bit
                page_data[col] = byte
            msg = I2C.Message([0x40] + page_data)
            self.i2c.transfer(self.address, [msg])

# Initialize OLED and run the clock
oled = OLEDi2c()
oled.display()
previous_second = datetime.now().second

try:
    while True:
        current_second = datetime.now().second
        if current_second != previous_second:
            oled.display()
            previous_second = current_second
        sleep(0.01)
except KeyboardInterrupt:
    oled.clear_display()
finally:
    oled.clear_display()
