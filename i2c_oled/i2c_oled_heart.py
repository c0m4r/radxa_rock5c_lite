#!/usr/bin/env python3
"""
Heart | OLED I2C [128x32] @ Radxa Rock 5C Lite
Author: Deepseek R1 + https://github.com/c0m4r
License: Public Domain
"""

from time import sleep

from periphery import I2C
from PIL import Image, ImageDraw


class OLEDi2c:
    """A class to control SSD1306-based OLED displays over I2C.

    Attributes:
        bus (str): Path to the I2C device file
        address (int): I2C device address
        i2c (I2C): I2C connection object
        width (int): Display width in pixels
        height (int): Display height in pixels
    """

    def __init__(self, bus: str="/dev/i2c-8", address: int=0x3C) -> None:
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
        self.initialize_oled()

    def ssd1306_command(self, cmd: int) -> None:
        """Send a single command to the SSD1306 controller.

        Args:
            cmd (int): Command byte to send to the display controller
        """
        msg = I2C.Message([0x00, cmd])
        self.i2c.transfer(self.address, [msg])

    def initialize_oled(self) -> None:
        """Initialize the display with required configuration commands."""
        commands = [
            0xAE,       # Display off
            0xD5, 0x80, # Set display clock divide ratio
            0xA8, 0x1F, # Set multiplex ratio (height-1 = 31 for 32px)
            0xD3, 0x00, # Set display offset
            0x40 | 0x0, # Set start line
            0x8D, 0x14, # Enable charge pump
            0x20, 0x00, # Set memory addressing mode
            0xA1,       # Segment remap (horizontal flip)
            0xC8,       # COM output scan direction (vertical flip)
            0xDA, 0x02, # COM pins configuration
            0x81, 0xCF, # Set contrast control
            0xD9, 0xF1, # Set pre-charge period
            0xDB, 0x40, # Set VCOMH deselect level
            0xA4,       # Resume to RAM content display
            0xA6,       # Set normal display (not inverted)
            0xAF        # Display on
        ]
        for cmd in commands:
            self.ssd1306_command(cmd)
        self.clear_display()

    def clear_display(self) -> None:
        """Clear the display."""
        # Clear all 4 pages (32px height)
        for page in range(4):
            self.ssd1306_command(0xB0 + page)
            self.ssd1306_command(0x00)
            self.ssd1306_command(0x10)
            # Send 128 white pixels (0xFF) per page
            data = [0x40] + [0x00] * self.width
            msg = I2C.Message(data)
            self.i2c.transfer(self.address, [msg])

    def draw_heart(self, heart_size: int=16) -> None:
        """Draw a black heart shape on a white background.

        Args:
            heart_size (int): Diameter of the heart in pixels. Default is 12.
        """
        # Create all-white image
        image = Image.new("1", (self.width, self.height), 1)
        draw = ImageDraw.Draw(image)

        # Calculate center position
        x_center = self.width // 2
        y_center = self.height // 2

        # Draw left circle of the heart
        draw.ellipse((
            x_center - heart_size,
            y_center - heart_size//2,
            x_center,
            y_center + heart_size//2
        ), fill=0)

        # Draw right circle of the heart
        draw.ellipse((
            x_center,
            y_center - heart_size//2,
            x_center + heart_size,
            y_center + heart_size//2
        ), fill=0)

        # Draw bottom triangle to complete heart shape
        draw.polygon([
            (x_center - heart_size, y_center),
            (x_center + heart_size, y_center),
            (x_center, y_center + heart_size)
        ], fill=0)

        # Send image data to display
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
                        # Invert pixel value for black-on-white display
                        byte |= (not pixel) << bit
                    except IndexError:
                        pass
                page_data.append(byte)

            msg = I2C.Message([0x40] + page_data)
            self.i2c.transfer(self.address, [msg])

    def close(self) -> None:
        """Close the I2C connection and clean up resources."""
        self.i2c.close()


if __name__ == "__main__":
    # Example usage: Create display and draw heart
    oled = OLEDi2c()
    try:
        oled.draw_heart()
        # Keep display active until interrupted
        while True:
            sleep(1)
    except KeyboardInterrupt:
        print("bye")
        oled.clear_display()
        oled.close()
