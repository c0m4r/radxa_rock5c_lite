#!/usr/bin/env python3

"""
Heart | OLED I2C [128x32] @ Radxa Rock 5C Lite
Author: Deepseek R1 + https://github.com/c0m4r
License: Public Domain
"""

from textwrap import wrap

from periphery import I2C
from PIL import Image, ImageDraw, ImageFont


class OledI2C:
    """OledI2C Class"""
    def __init__(self, bus:str="/dev/i2c-8", address:int=0x3C) -> None:
        """Init"""
        self.bus = bus
        self.address = address
        self.i2c = I2C(self.bus)
        self.width = 128
        self.height = 32  # Adjusted for 128x32 display
        self.font = ImageFont.truetype("/usr/share/fonts/truetype/pixelmix.ttf", 8)  # Adjusted font size

        self.initialize_oled()

    def ssd1306_command(self, cmd:int) -> None:
        """SSD1306 Command"""
        msg = I2C.Message([0x00, cmd])
        self.i2c.transfer(self.address, [msg])

    def initialize_oled(self) -> None:
        """Initialize OLED"""
        commands = [
            0xAE,       # Display off
            0xD5, 0x80, # Set display clock divide
            0xA8, 0x1F, # Multiplex ratio for 32 rows (0x1F = 31)
            0xD3, 0x00, # Display offset
            0x40 | 0x0, # Start line
            0x8D, 0x14, # Charge pump
            0x20, 0x00, # Memory mode
            0xA1,       # Segment remap
            0xC8,       # COM output scan direction
            0xDA, 0x02, # COM pins config (sequential for 32px)
            0x81, 0xCF, # Contrast
            0xD9, 0xF1, # Pre-charge
            0xDB, 0x40, # VCOMH deselect
            0xA4,       # Display resume
            0xA6,       # Normal display
            0xAF        # Display on
        ]
        for cmd in commands:
            self.ssd1306_command(cmd)
        self.clear_display()

    def clear_display(self) -> None:
        """Clear display"""
        # Clear all 4 pages (32px height)
        for page in range(4):
            self.ssd1306_command(0xB0 + page)
            self.ssd1306_command(0x00)
            self.ssd1306_command(0x10)
            # Send 128 zeros per page in one transfer
            data = [0x40] + [0x00] * self.width  # Co=0, D/C=1 with continuous data
            msg = I2C.Message(data)
            self.i2c.transfer(self.address, [msg])

    def display_text(self, text:str) -> None:
        """Display text"""
        image = Image.new("1", (self.width, self.height))
        draw = ImageDraw.Draw(image)

        # Adjust text wrapping and positioning for 32px height
        lines = wrap(text, width=21)  # ~21 chars per line for 8px font
        y_text = 0
        for line in lines:
            if y_text + 8 > self.height:
                break
            draw.text((0, y_text), line, font=self.font, fill=255)
            y_text += 8

        # Send entire pages in single transfers
        for page in range(4):
            self.ssd1306_command(0xB0 + page)
            self.ssd1306_command(0x00)
            self.ssd1306_command(0x10)

            page_data = []
            for col in range(self.width):
                byte = 0
                for bit in range(8):
                    try:
                        pixel = image.getpixel((col, page * 8 + bit))
                    except IndexError:
                        pixel = 0
                    byte |= (pixel & 0x1) << bit
                page_data.append(byte)

            # Send Co=1 (continuous), D/C=1 followed by all data bytes
            msg = I2C.Message([0x40] + page_data)  # Co=0 for single byte, but optimized transfer
            self.i2c.transfer(self.address, [msg])

    def close(self) -> None:
        """Close"""
        self.i2c.close()

# Execute
oled = OledI2C()
oled.display_text("Yo, listen up here's the story, about a little guy that lives in a blue world.")
oled.close()
