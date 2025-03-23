#!/usr/bin/env python3
"""
Vertical Text Display | OLED I2C [128x32] @ Radxa Rock 5C Lite
Author: Deepseek R1 + https://github.com/c0m4r
License: Public Domain
"""

import time

from periphery import I2C
from PIL import Image, ImageDraw, ImageFont

class OLEDi2c:
    """SSD1306 OLED controller with vertical text display support."""

    def __init__(self, bus: str="/dev/i2c-8", address: int=0x3C) -> None:
        self.bus = bus
        self.address = address
        self.i2c = I2C(self.bus)
        self.width = 128
        self.height = 32
        self.initialize_oled()

    def ssd1306_command(self, cmd: int) -> None:
        """Send a command to the SSD1306 controller."""
        msg = I2C.Message([0x00, cmd])
        self.i2c.transfer(self.address, [msg])

    def initialize_oled(self) -> None:
        """Initialize display with rotation support."""
        commands = [
            0xAE,       # Display off
            0xD5, 0x80, # Set display clock divide ratio
            0xA8, 0x1F, # Set multiplex ratio
            0xD3, 0x00, # Set display offset
            0x40 | 0x0, # Set start line
            0x8D, 0x14, # Enable charge pump
            0x20, 0x00, # Horizontal addressing mode
            0xA0,       # Segment remap (normal)
            0xC0,       # COM output scan direction (normal)
            0xDA, 0x02, # COM pins configuration
            0x81, 0xCF, # Set contrast control
            0xD9, 0xF1, # Set pre-charge period
            0xDB, 0x40, # Set VCOMH deselect level
            0xA4,       # Resume RAM display
            0xA6,       # Normal display
            0xAF        # Display on
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
            data = [0x40] + [0x00] * self.width
            msg = I2C.Message(data)
            self.i2c.transfer(self.address, [msg])

    def draw_vertical_text(self, text: str="HELLO") -> None:
        """Draw vertical text on rotated display."""
        # Create vertical image (32x128) and rotate to match physical display
        font_size = 24
        font = ImageFont.truetype("/usr/share/fonts/truetype/pixelmix.ttf", font_size)

        # Get character height from the font
        char_height = font_size + 2

        # Create portrait orientation image
        img = Image.new("1", (32, 128), 1)
        draw = ImageDraw.Draw(img)

        # Calculate vertical position
        total_height = len(text) * char_height
        y_start = (128 - total_height) // 2

        # Draw each character vertically centered
        y = y_start
        for char in text:
            bbox = font.getbbox(char)
            char_width = bbox[2] - bbox[0]  # right - left
            x = (32 - char_width) // 2
            draw.text((x, y), char, font=font, fill=0)
            y += char_height  # Move down by character height

        # Rotate image 90 degrees clockwise for physical display
        img = img.rotate(90, expand=True)

        # Convert image to display format
        for page in range(4):
            self.ssd1306_command(0xB0 + page)
            self.ssd1306_command(0x00)
            self.ssd1306_command(0x10)

            page_data = []
            for col in range(self.width):
                byte = 0
                for bit in range(8):
                    try:
                        pixel = img.getpixel((col, page * 8 + bit))
                        byte |= (not pixel) << bit
                    except IndexError:
                        pass
                page_data.append(byte)

            msg = I2C.Message([0x40] + page_data)
            self.i2c.transfer(self.address, [msg])

    def close(self) -> None:
        """Close I2C connection."""
        self.i2c.close()

if __name__ == "__main__":
    oled = OLEDi2c()
    try:
        oled.draw_vertical_text()
        # Keep display active
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        oled.clear_display()
        oled.close()
        print("Display cleared and closed.")
