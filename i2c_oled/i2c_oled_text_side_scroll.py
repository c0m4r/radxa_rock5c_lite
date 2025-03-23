#!/usr/bin/env python3
"""
Text Side Scroll | OLED I2C [128x32] @ Radxa Rock 5C Lite
Author: Deepseek R1 + https://github.com/c0m4r
License: Public Domain
"""

import time

from periphery import I2C
from PIL import Image, ImageDraw, ImageFont


class OledI2C:
    """A class to interface with an SSD1306-based OLED display over I2C.

    Attributes:
        bus (str): Path to I2C bus device
        address (int): Device I2C address
        width (int): Display width in pixels
        height (int): Display height in pixels
        font_path (str): Path to default font file
    """

    def __init__(self, bus:str="/dev/i2c-8", address:int=0x3C) -> None:
        """Initialize I2C connection and display hardware.

        Args:
            bus (str): I2C bus device path (default: "/dev/i2c-8")
            address (int): I2C device address (default: 0x3C)
        """
        self.bus = bus
        self.address = address
        self.i2c = I2C(self.bus)
        self.width = 128
        self.height = 32
        self.font_path = "/usr/share/fonts/truetype/pixelmix.ttf"
        self.initialize_oled()

    def ssd1306_command(self, cmd:int) -> None:
        """Send a single command byte to SSD1306 controller.

        Args:
            cmd (int): Command byte to send
        """
        msg = I2C.Message([0x00, cmd])
        self.i2c.transfer(self.address, [msg])

    def initialize_oled(self) -> None:
        """Initialize display with standard SSD1306 configuration sequence."""
        commands = [
            0xAE, 0xD5, 0x80, 0xA8, 0x1F, 0xD3, 0x00, 0x40,
            0x8D, 0x14, 0x20, 0x00, 0xA1, 0xC8, 0xDA, 0x02,
            0x81, 0xCF, 0xD9, 0xF1, 0xDB, 0x40, 0xA4, 0xA6, 0xAF
        ]
        for cmd in commands:
            self.ssd1306_command(cmd)
        self.clear_display()

    def clear_display(self) -> None:
        """Clear display by writing zeros to all pixels."""
        for page in range(4):
            self.ssd1306_command(0xB0 + page)
            self.ssd1306_command(0x00)
            self.ssd1306_command(0x10)
            msg = I2C.Message([0x40] + [0x00]*128)
            self.i2c.transfer(self.address, [msg])

    def draw_image(self, image) -> None:
        """Draw a 1-bit PIL Image to the display.

        Args:
            image (PIL.Image): Image to display, must be 1-bit mode and match
                display dimensions (128x32 pixels)
        """
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
                    byte |= pixel << bit
                page_data.append(byte)
            msg = I2C.Message([0x40] + page_data)
            self.i2c.transfer(self.address, [msg])

    def side_scroll(self, text:str, font_size:int=18, speed:int=30) -> None:
        """Display smooth horizontal scrolling text with speed control.

        Runs continuously until KeyboardInterrupt (Ctrl+C), then clears display.

        Args:
            text (str): Text to scroll
            font_size (int): Font size in points (default: 18)
            speed (int): Scroll speed in frames per second (default: 30)
        """
        font = ImageFont.truetype(self.font_path, font_size)

        # Calculate text dimensions
        temp_img = Image.new("1", (self.width, self.height))
        draw = ImageDraw.Draw(temp_img)
        bbox = draw.textbbox((0, 0), text + " ", font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Create scrolling buffer
        buffer = Image.new("1", (text_width + self.width, text_height))
        bdraw = ImageDraw.Draw(buffer)
        bdraw.text((-bbox[0], -bbox[1]), text + " ", font=font, fill=1)

        x_pos = 0
        y_pos = (self.height - text_height) // 2
        scroll_width = text_width + self.width

        try:
            while True:
                start_time = time.time()

                img = Image.new("1", (self.width, self.height))
                src_x = x_pos % scroll_width

                # Copy visible portion from buffer
                img.paste(buffer.crop((
                    src_x, 0,
                    src_x + self.width, text_height
                )), (0, y_pos))

                self.draw_image(img)

                # Speed control
                x_pos += 1
                elapsed = time.time() - start_time
                delay = max(0, (1 / speed) - elapsed)
                time.sleep(delay)

        except KeyboardInterrupt:
            self.clear_display()

    def close(self) -> None:
        """Close the I2C connection."""
        self.i2c.close()

# Test with full text and working speed control
if __name__ == "__main__":
    oled = OledI2C()
    oled.side_scroll("        send nudes", font_size=24, speed=60)
    oled.close()
