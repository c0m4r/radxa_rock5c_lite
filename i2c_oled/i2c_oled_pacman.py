#!/usr/bin/env python3
"""
OLED Image Display | OLED I2C [128x32] @ Radxa Rock 5C Lite
Modified to support PNG images
Author: Deepseek R1 + https://github.com/c0m4r
License: Public Domain
"""

import time
from periphery import I2C
from PIL import Image, ImageDraw, ImageFont

class OLEDi2c:
    """A class to control SSD1306-based OLED displays over I2C.

    Attributes:
        bus (str): Path to the I2C device file
        address (int): I2C device address
        i2c (I2C): I2C connection object
        width (int): Display width in pixels
        height (int): Display height in pixels
    """

    def __init__(self, bus:str="/dev/i2c-8", address:int=0x3C) -> None:
        """Initialize the OLED display controller.

        Args:
            bus (str): Path to I2C device file. Default is '/dev/i2c-8'.
            address (int): I2C device address. Default is 0x3C.
        """
        self.bus = bus
        self.address = address
        self.i2c = I2C(self.bus)
        self.width = 128
        self.height = 32
        self.font_path = "/usr/share/fonts/truetype/pixelmix.ttf"
        self.initialize_oled()

    def ssd1306_command(self, cmd:int) -> None:
        """Send a single command to the SSD1306 controller.

        Args:
            cmd (int): Command byte to send to the display controller
        """
        msg = I2C.Message([0x00, cmd])
        self.i2c.transfer(self.address, [msg])

    def initialize_oled(self) -> None:
        """Initialize the display with required configuration commands."""
        commands = [
            0xAE, 0xD5, 0x80, 0xA8, 0x1F, 0xD3, 0x00, 0x40,
            0x8D, 0x14, 0x20, 0x00, 0xA1, 0xC8, 0xDA, 0x02,
            0x81, 0xCF, 0xD9, 0xF1, 0xDB, 0x40, 0xA4, 0xA6, 0xAF
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
            msg = I2C.Message([0x40] + [0x00]*128)
            self.i2c.transfer(self.address, [msg])

    def draw_text(self, text:str, font_size:int=18) -> None:
        """Draw text on the display.

        Args:
            text (str): Text to display
            font_size (int): Font size. Default is 18.
        """
        image = Image.new("1", (self.width, self.height))
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(self.font_path, font_size)

        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]  # right - left
        text_height = bbox[3] - bbox[1] # bottom - top

        # Calculate centered position
        x = (self.width - text_width) // 2 - bbox[0]
        y = (self.height - text_height) // 2 - bbox[1]

        draw.text((x, y), text, font=font, fill=1)

        # Send to display
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

    def draw_image(self, image_path: str) -> None:
        """Draw a 128x32 PNG image on the display.

        Args:
            image_path (str): Path to the PNG image file
        """
        # Open and convert image to 1-bit monochrome
        image = Image.open(image_path).convert('L').convert('1')

        # Ensure correct size
        if image.size != (self.width, self.height):
            print("wrong size")
            image = image.resize((self.width, self.height))

        # Send to display
        for page in range(4):
            self.ssd1306_command(0xB0 + page)
            self.ssd1306_command(0x00)
            self.ssd1306_command(0x10)
            page_data = []
            for col in range(self.width):
                byte = 0
                for bit in range(8):
                    try:
                        # Invert: White (255) becomes 1, Black (0) becomes 0
                        pixel = 1 if image.getpixel((col, page * 8 + bit)) > 0 else 0
                    except IndexError:
                        pixel = 0
                    byte |= pixel << bit
                page_data.append(byte)
            msg = I2C.Message([0x40] + page_data)
            self.i2c.transfer(self.address, [msg])

    def animate_frames(self, seq: list[tuple[str, float, str]]) -> None:
        """Animate frames with support for both text and images.

        Args:
            seq (list[tuple[str, float, str]]): Sequence of frames to display.
                Each frame is a tuple of (content, display_time, content_type).
                content_type can be 'text' or 'image'.
        """
        try:
            while True:
                for content, delay, content_type in seq:
                    if content_type == 'text':
                        self.draw_text(content)  # delay repurposed as font size
                    elif content_type == 'image':
                        self.draw_image(content)
                    time.sleep(delay)
        except KeyboardInterrupt:
            self.clear_display()

    def close(self) -> None:
        """Close the I2C connection."""
        self.i2c.close()

# Frame sequence
# content | display_time | content_type
frames = [
    ("P     ", 0.5, 'text'),
    ("PA    ", 0.5, 'text'),
    ("PAC   ", 0.5, 'text'),
    ("PACM  ", 0.5, 'text'),
    ("PACMA ", 0.5, 'text'),
    ("PACMAN", 0.5, 'text'),
    ("img/pacman1.png", 0.5, 'image'),
    ("img/pacman2.png", 0.5, 'image'),
    ("img/pacman3.png", 0.5, 'image'),
    ("img/pacman4.png", 0.5, 'image'),
    ("img/pacman5.png", 0.1, 'image'),
    ("img/pacman6.png", 0.1, 'image'),
    ("img/pacman7.png", 0.1, 'image'),
    ("img/pacman8.png", 0.1, 'image'),
    ("img/pacman9.png", 0.1, 'image'),
    ("img/pacman10.png", 0.1, 'image'),
    ("img/pacman11.png", 0.2, 'image'),
    ("img/pacman12.png", 0.2, 'image'),
    ("img/pacman13.png", 0.2, 'image'),
    ("img/pacman14.png", 0.2, 'image'),
]

# Run animation
oled = OLEDi2c()
oled.animate_frames(frames)
oled.close()
