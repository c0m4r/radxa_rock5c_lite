#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to control an ST7789-based 2.0 inch TFT Display (240x320)
connected to a Radxa Rock 5C via SPI using python3-spidev and python3-gpiod v2+.

Handles displaying images, text, or clearing the screen.

Vibe-coded with Gemini 2.5 Pro Experimental 03-25
https://github.com/c0m4r/
License: Public Domain
"""

import spidev
import gpiod # Use the v2 API (python3-gpiod >= 2.0)
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import argparse
import os
import sys
from typing import Union, List, Tuple, Optional, Sequence

# --- Configuration ---
# Display dimensions (configured for landscape where 320 is width)
# NOTE: The ST7789 native resolution might be 240x320 (Portrait).
#       The MADCTL command (0x36) is used to rotate logically.
WIDTH: int = 320
HEIGHT: int = 240

# --- ST7789 Commands ---
# Reference: Search for "ST7789 Datasheet"
# Note: Not all commands are used in this basic driver.

# System Function Commands
ST7789_NOP        = 0x00 # No Operation
ST7789_SWRESET    = 0x01 # Software Reset (clears registers, delays needed)
ST7789_RDDID      = 0x04 # Read Display ID (returns 3 bytes: Manuf ID, Ver, Driver ID)
ST7789_RDDST      = 0x09 # Read Display Status (returns 4 bytes: info about display state)
ST7789_RDDPM      = 0x0A # Read Display Power Mode (returns 1 byte)
ST7789_RDDMADCTL  = 0x0B # Read Display MADCTL (returns 1 byte: current orientation/color order)
ST7789_RDDCOLMOD  = 0x0C # Read Display Pixel Format (returns 1 byte: current COLMOD)
ST7789_RDDIM      = 0x0D # Read Display Image Mode (returns 1 byte)
ST7789_RDDSM      = 0x0E # Read Display Signal Mode (returns 1 byte)
ST7789_RDDSDR     = 0x0F # Read Display Self-Diagnostic Result (returns 1 byte)

ST7789_SLPIN      = 0x10 # Enter Sleep Mode (display off, low power)
ST7789_SLPOUT     = 0x11 # Exit Sleep Mode (requires delay to stabilize)
ST7789_PTLON      = 0x12 # Partial Display Mode ON
ST7789_NORON      = 0x13 # Normal Display Mode ON (default)

ST7789_INVOFF     = 0x20 # Display Inversion OFF (colors are normal)
ST7789_INVON      = 0x21 # Display Inversion ON (colors inverted)
ST7789_GAMSET     = 0x26 # Gamma Set (selects gamma curve)
ST7789_DISPOFF    = 0x28 # Display OFF (output disabled, contents preserved)
ST7789_DISPON     = 0x29 # Display ON (output enabled)
ST7789_CASET      = 0x2A # Column Address Set (defines horizontal drawing window)
ST7789_RASET      = 0x2B # Row Address Set (defines vertical drawing window)
ST7789_RAMWR      = 0x2C # Memory Write (starts writing pixel data to RAM window)
ST7789_RAMRD      = 0x2E # Memory Read (starts reading pixel data from RAM window)

ST7789_PTLAR      = 0x30 # Partial Area (defines window for Partial Display Mode)
ST7789_VSCRDEF    = 0x33 # Vertical Scrolling Definition
ST7789_TEOFF      = 0x34 # Tearing Effect Line OFF
ST7789_TEON       = 0x35 # Tearing Effect Line ON
ST7789_MADCTL     = 0x36 # Memory Data Access Control (controls orientation, color order)
                         # Bits: MY (Row Addr Order), MX (Col Addr Order), MV (Row/Col Swap),
                         #       ML (Vert Refresh Order), RGB (BGR vs RGB color order), MH (Horiz Refresh Order)
ST7789_VSCSAD     = 0x37 # Vertical Scroll Start Address of RAM
ST7789_IDMOFF     = 0x38 # Idle Mode OFF
ST7789_IDMON      = 0x39 # Idle Mode ON (reduced color depth for power saving)
ST7789_COLMOD     = 0x3A # Interface Pixel Format (defines color depth: RGB444, RGB565, RGB666)
                         # Common values: 0x55 = 16-bit/pixel (RGB565), 0x66 = 18-bit/pixel (RGB666)
ST7789_WRMEMC     = 0x3C # Write Memory Continue
ST7789_RDMEMC     = 0x3E # Read Memory Continue

ST7789_STE        = 0x44 # Set Tear Scanline
ST7789_GSCAN      = 0x45 # Get Scanline
ST7789_WRDISBV    = 0x51 # Write Display Brightness Value
ST7789_RDDISBV    = 0x52 # Read Display Brightness Value
ST7789_WRCTRLD    = 0x53 # Write CTRL Display
ST7789_RDCTRLD    = 0x54 # Read CTRL Display
ST7789_WRCACE     = 0x55 # Write Content Adaptive Brightness Control & Color Enhancement
ST7789_RDCABC     = 0x56 # Read Content Adaptive Brightness Control
ST7789_WRCABCMB   = 0x5E # Write CABC Minimum Brightness
ST7789_RDCABCMB   = 0x5F # Read CABC Minimum Brightness

# Extended Commands (Register Set 2 - usually prefixed by command 0xFF)
# Note: This driver doesn't explicitly use command 0xFF to switch register sets,
# it assumes commands below are directly accessible or handled by specific init sequences.
ST7789_FRMCTR1    = 0xB1 # Frame Rate Control (In normal mode/ Full colors)
ST7789_FRMCTR2    = 0xB2 # Frame Rate Control (In Idle mode/ 8-colors)
ST7789_FRMCTR3    = 0xB3 # Frame Rate control (In Partial mode/ full colors)
ST7789_INVCTR     = 0xB4 # Display Inversion Control
ST7789_BPC        = 0xB5 # Blanking Porch Control
ST7789_DISSET5    = 0xB6 # Display Function Control (controls non-display areas, etc.)
ST7789_PWCTR1     = 0xC0 # Power Control 1 (GVDD voltage level)
ST7789_PWCTR2     = 0xC1 # Power Control 2 (VGH / VGL voltage levels)
ST7789_PWCTR3     = 0xC2 # Power Control 3 (OPAMP settings in Normal mode)
ST7789_PWCTR4     = 0xC3 # Power Control 4 (OPAMP settings in Idle mode)
ST7789_PWCTR5     = 0xC4 # Power Control 5 (OPAMP settings in Partial mode)
ST7789_VMCTR1     = 0xC5 # VCOM Control 1 (VCOMH / VCOML voltage levels)
ST7789_VMCTR2     = 0xC6 # VCOM Control 2 (VCOM offset voltage) - Datasheet might list as FRCTRL2

ST7789_PWCTRL1    = 0xD0 # Power Control Setting (Seems duplicate/alternative name for PWCTR1? AVDD/VGH/VGL related)
ST7789_RDID1      = 0xDA # Read ID1 (Read manufacturer ID) - Alternative to 0x04
ST7789_RDID2      = 0xDB # Read ID2 (Read driver version ID) - Alternative to 0x04
ST7789_RDID3      = 0xDC # Read ID3 (Read driver ID) - Alternative to 0x04

ST7789_GMCTRP1    = 0xE0 # Positive Gamma Correction Setting
ST7789_GMCTRN1    = 0xE1 # Negative Gamma Correction Setting
ST7789_DGCTRL1    = 0xE2 # Digital Gamma Control 1
ST7789_DGCTRL2    = 0xE3 # Digital Gamma Control 2
ST7789_PWCTR6     = 0xFC # Power Control 6 (possibly related to gate driving) - Name may vary

# --- ST7789 Driver Class ---

class ST7789:
    """
    Driver class for ST7789 TFT LCD displays using SPI and gpiod v2.

    Manages SPI communication, GPIO control for DC/RST pins, display
    initialization, and drawing operations.
    """
    def __init__(self,
                 spi_port: int,
                 spi_device: int,
                 spi_speed_hz: int,
                 gpio_chip_dc_path: str,
                 dc_pin: int,    # dc_pin is Linux GPIO number (e.g., 140)
                 gpio_chip_rst_path: str,
                 rst_pin: int,   # rst_pin is Linux GPIO number (e.g., 37)
                 width: int = WIDTH,
                 height: int = HEIGHT) -> None:
        """
        Initialize the ST7789 display driver.

        Args:
            spi_port: SPI bus number (e.g., 0 for /dev/spidev0.0).
            spi_device: SPI device (chip select) number (e.g., 0 for /dev/spidev0.0).
            spi_speed_hz: SPI clock speed in Hertz (e.g., 40_000_000 for 40MHz).
            gpio_chip_dc_path: Full path to the GPIO chip for the DC pin (e.g., '/dev/gpiochip4').
            dc_pin: Linux system GPIO number for the Data/Command (DC) pin.
            gpio_chip_rst_path: Full path to the GPIO chip for the RST pin (e.g., '/dev/gpiochip1').
            rst_pin: Linux system GPIO number for the Reset (RST) pin.
            width: Width of the display in pixels (default: WIDTH).
            height: Height of the display in pixels (default: HEIGHT).
        """
        self.width = width
        self.height = height
        self.spi_speed_hz = spi_speed_hz

        # Store GPIO pin numbers and calculate gpiod offsets
        self.dc_pin = dc_pin
        self.rst_pin = rst_pin
        self.dc_offset = self.dc_pin % 32 # Offset within the 32-line bank
        self.rst_offset = self.rst_pin % 32

        # --- Internal GPIO state ---
        self._spi: Optional[spidev.SpiDev] = None
        self._dc_request: Optional[gpiod.LineRequest] = None
        self._rst_request: Optional[gpiod.LineRequest] = None

        try:
            # --- Initialize SPI ---
            print(f"Initializing SPI: /dev/spidev{spi_port}.{spi_device} at {spi_speed_hz/1_000_000:.1f} MHz")
            self._spi = spidev.SpiDev()
            self._spi.open(spi_port, spi_device)
            self._spi.max_speed_hz = self.spi_speed_hz
            # Mode 0: CPOL=0 (Clock Idle Low), CPHA=0 (Data sampled on rising edge)
            self._spi.mode = 0b00
            print("  SPI initialized successfully.")

            # --- Initialize GPIO using gpiod v2 ---
            print(f"Initializing GPIO (using gpiod v2 API):")
            print(f"  DC: Chip='{gpio_chip_dc_path}' LinuxPin={self.dc_pin} -> Offset={self.dc_offset}")
            print(f"  RST: Chip='{gpio_chip_rst_path}' LinuxPin={self.rst_pin} -> Offset={self.rst_offset}")

            # --- Request DC Pin ---
            print(f"  Requesting DC line {self.dc_offset} from {gpio_chip_dc_path}")
            self._dc_request = gpiod.request_lines(
                gpio_chip_dc_path,
                consumer=f"{os.path.basename(__file__)}-DC",
                config={
                    self.dc_offset: gpiod.LineSettings(
                        direction=gpiod.line.Direction.OUTPUT,
                        output_value=gpiod.line.Value.INACTIVE # Start low (Command mode)
                    )
                }
            )
            print(f"    DC line requested successfully.")

            # --- Request RST Pin ---
            print(f"  Requesting RST line {self.rst_offset} from {gpio_chip_rst_path}")
            # If RST chip is different, this opens it. If same, it reuses the underlying chip access.
            self._rst_request = gpiod.request_lines(
                gpio_chip_rst_path,
                consumer=f"{os.path.basename(__file__)}-RST",
                config={
                    self.rst_offset: gpiod.LineSettings(
                        direction=gpiod.line.Direction.OUTPUT,
                        output_value=gpiod.line.Value.ACTIVE # Start high (not resetting)
                    )
                }
            )
            print(f"    RST line requested successfully.")

        except FileNotFoundError as e:
            print(f"ERROR: GPIO chip path or SPI device not found.")
            print(f" -> Check if SPI is enabled ('ls /dev/spi*').")
            print(f" -> Check if GPIO chip paths are correct ('ls /dev/gpiochip*').")
            print(f" -> Original error: {e}")
            self.close() # Attempt cleanup
            sys.exit(1)
        except PermissionError as e:
             print(f"ERROR: Permission denied accessing SPI or GPIO.")
             print(f" -> Run the script as root (sudo) or add your user to the 'spi' and 'gpio' groups:")
             print(f"      sudo usermod -a -G spi $USER")
             print(f"      sudo usermod -a -G gpio $USER")
             print(f" -> Then, log out and log back in for group changes to take effect.")
             print(f" -> Original error: {e}")
             self.close()
             sys.exit(1)
        except Exception as e:
            print(f"ERROR: Could not initialize SPI or GPIO lines using gpiod v2.")
            print(f" -> Check if chip paths '{gpio_chip_dc_path}'/'{gpio_chip_rst_path}' are correct.")
            print(f" -> Check if requested offsets (DC:{self.dc_offset}, RST:{self.rst_offset}) exist on those chips (use 'gpioinfo {gpio_chip_dc_path}' etc.).")
            print(f" -> Check if libgpiod and python3-gpiod (v2+) are installed correctly.")
            print(f" -> Original error: {e}")
            self.close() # Attempt cleanup
            sys.exit(1)

        # --- Initialize Display Hardware ---
        self.reset()
        self.init_display()
        print("Display initialized successfully.")

    def close(self) -> None:
        """Clean up resources: Turn off display, release GPIO lines, close SPI."""
        print("Closing display resources...")
        try:
            # Optional: Put display into a safe state before closing
            if self._spi and self._dc_request: # Check if partially initialized
                self.command(ST7789_DISPOFF) # Turn display off
                # self.command(ST7789_SLPIN) # Put display to sleep (optional)
                time.sleep(0.05) # Short delay
        except Exception as e:
            # Don't prevent cleanup if display commands fail
            print(f"Warning: Error during display shutdown commands: {e}")

        # Close GPIO Requests (Releases the lines)
        if self._dc_request:
            try:
                self._dc_request.close()
                print("  DC GPIO request closed.")
            except Exception as e:
                 print(f"Warning: Error closing DC GPIO request: {e}")
            self._dc_request = None
        if self._rst_request:
             try:
                self._rst_request.close()
                print("  RST GPIO request closed.")
             except Exception as e:
                  print(f"Warning: Error closing RST GPIO request: {e}")
             self._rst_request = None

        # Close SPI
        if self._spi:
            try:
                self._spi.close()
                print("  SPI closed.")
            except Exception as e:
                print(f"Warning: Error closing SPI device: {e}")
            self._spi = None

        print("Resource cleanup finished.")

    def command(self, cmd: int) -> None:
        """Send a command byte to the display."""
        if not self._dc_request or not self._spi:
            # Avoid errors if initialization failed or already closed
            # print("Warning: Attempted to send command but resources not ready.")
            return
        try:
            # Set DC line low for command mode
            self._dc_request.set_value(self.dc_offset, gpiod.line.Value.INACTIVE)
            # Send the command byte
            self._spi.writebytes([cmd])
        except Exception as e:
            print(f"Error sending command 0x{cmd:02X}: {e}")
            # Consider re-raising or handling more robustly depending on needs

    def data(self, data_val: Union[int, Sequence[int], bytes, bytearray]) -> None:
        """Send data byte(s) to the display."""
        if not self._dc_request or not self._spi:
            # Avoid errors if initialization failed or already closed
            # print("Warning: Attempted to send data but resources not ready.")
            return
        try:
            # Set DC line high for data mode
            self._dc_request.set_value(self.dc_offset, gpiod.line.Value.ACTIVE)

            # Send the data
            if isinstance(data_val, int):
                self._spi.writebytes([data_val])
            elif isinstance(data_val, (bytes, bytearray)):
                self._spi.writebytes2(data_val) # Preferred for potentially large buffers
            elif isinstance(data_val, list):
                self._spi.writebytes2(bytes(data_val)) # Convert list of ints to bytes
            else:
                # Attempt conversion for other sequence types, might fail
                self._spi.writebytes2(bytes(data_val))
        except Exception as e:
            print(f"Error sending data: {e}")
            # Consider re-raising or handling

    def reset(self) -> None:
        """Perform a hardware reset of the display."""
        if not self._rst_request: return # Avoid error if not initialized
        print("Performing hardware reset...")
        try:
            # Ensure RST is high initially
            self._rst_request.set_value(self.rst_offset, gpiod.line.Value.ACTIVE)
            time.sleep(0.050) # 50ms
            # Pull RST low to reset
            self._rst_request.set_value(self.rst_offset, gpiod.line.Value.INACTIVE)
            time.sleep(0.050) # 50ms (Hold low time)
            # Pull RST high again to release from reset
            self._rst_request.set_value(self.rst_offset, gpiod.line.Value.ACTIVE)
            time.sleep(0.150) # 150ms (Wait for oscillator stabilization etc.)
            print("Reset complete.")
        except Exception as e:
            print(f"Error during hardware reset: {e}")
            # Initialization might fail after this

    def init_display(self) -> None:
        """Initialize the ST7789 controller with a standard sequence."""
        print("Sending initialization sequence...")
        # This sequence is typical but might need adjustment for specific panels.
        self.command(ST7789_SWRESET) # 1: Software Reset
        time.sleep(0.150) # Need 120ms delay after SWRESET

        self.command(ST7789_SLPOUT) # 2: Exit Sleep Mode
        time.sleep(0.500) # Needs 500ms delay after SLPOUT (long!)

        # 3: Memory Data Access Control (MADCTL) - Crucial for orientation
        #    Sets rotation and color order (RGB vs BGR)
        #    0x60 = MY=0, MX=1, MV=1, ML=0, RGB=1(BGR), MH=0
        #      MV=1: Row/Column exchanged (for landscape on 240x320 panel)
        #      MX=1: Col Address L-to-R
        #      MY=0: Row Address T-to-B
        #      RGB=1: BGR color order (IMPORTANT!) - If colors are swapped (red/blue), use 0x68 (RGB order)
        #    Common alternatives:
        #      0x00: Portrait (0deg), RGB
        #      0xC0: Portrait inverted (180deg), RGB
        #      0xA0: Landscape inverted (270deg), RGB
        #      0x60: Landscape (90deg), BGR <--- USED HERE
        #      0x70: Landscape (90deg), RGB
        self.command(ST7789_MADCTL)
        self.data(0x60) # Set for Landscape (320W x 240H), BGR color order

        # 4: Interface Pixel Format (COLMOD)
        #    0x55 = 16 bits/pixel (RGB565)
        #    0x66 = 18 bits/pixel (RGB666) - Less common for SPI
        self.command(ST7789_COLMOD)
        self.data(0x55) # Set RGB565 format

        # 5: Display Inversion ON (Optional)
        #    Some panels require inversion for correct colors.
        #    If colors look inverted (like a negative photo), use INVOFF (0x20) instead.
        self.command(ST7789_INVON) # 0x21

        # 6: Gamma Settings, Power Controls, Frame Rates etc. (Optional - using defaults)
        #    These can be fine-tuned using commands like GMCTRP1, GMCTRN1, PWCTR1, VMCTR1 etc.
        #    Defaults are often sufficient.

        # 7: Turn display ON
        self.command(ST7789_NORON) # Normal Display Mode ON
        time.sleep(0.01) # Small delay before DISPON
        self.command(ST7789_DISPON) # Main screen turn on
        time.sleep(0.100) # Delay after display on
        print("Initialization sequence sent.")

    def set_window(self, x0: int = 0, y0: int = 0, x1: Optional[int] = None, y1: Optional[int] = None) -> None:
        """
        Set the drawing window area (clip rectangle) in display RAM.

        Args:
            x0: Start column (0 to width-1).
            y0: Start row (0 to height-1).
            x1: End column (0 to width-1). Defaults to width-1.
            y1: End row (0 to height-1). Defaults to height-1.
        """
        if x1 is None: x1 = self.width - 1
        if y1 is None: y1 = self.height - 1

        # Ensure coordinates are within bounds
        x0 = max(0, min(x0, self.width - 1))
        x1 = max(0, min(x1, self.width - 1))
        y0 = max(0, min(y0, self.height - 1))
        y1 = max(0, min(y1, self.height - 1))

        # Set Column Address Range (CASET)
        self.command(ST7789_CASET)
        self.data([
            (x0 >> 8) & 0xFF, x0 & 0xFF,   # Start Column High Byte, Low Byte
            (x1 >> 8) & 0xFF, x1 & 0xFF    # End Column High Byte, Low Byte
        ])

        # Set Row Address Range (RASET)
        self.command(ST7789_RASET)
        self.data([
            (y0 >> 8) & 0xFF, y0 & 0xFF,   # Start Row High Byte, Low Byte
            (y1 >> 8) & 0xFF, y1 & 0xFF    # End Row High Byte, Low Byte
        ])

        # Enable RAM Writing (RAMWR) - subsequent data() calls write pixels
        self.command(ST7789_RAMWR)

    def display_image(self, image: Image.Image) -> None:
        """
        Display a PIL Image object on the screen.

        The image is automatically resized to fit the display and converted
        to the required RGB565 format.

        Args:
            image: A PIL (Pillow) Image object.
        """
        # Ensure image is in RGB format
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Resize the image to fit the display dimensions
        img_resized = image.resize((self.width, self.height))

        # Convert PIL image to NumPy array
        pixels = np.array(img_resized).astype(np.uint16)

        # Convert 24-bit RGB to 16-bit RGB565 format
        # RRRRRGGG GGGBBBBB
        # Red:   Top 5 bits (xxxxx...)
        # Green: Top 6 bits (...yyyyyy..)
        # Blue:  Top 5 bits (.......zzzzz)
        r = (pixels[:, :, 0] & 0xF8) << 8  # Shift red bits to MSB position
        g = (pixels[:, :, 1] & 0xFC) << 3  # Shift green bits to middle position
        b = (pixels[:, :, 2] & 0xF8) >> 3  # Shift blue bits to LSB position

        # Combine the channels into a single 16-bit value
        rgb565 = r | g | b

        # Convert the 16-bit data to bytes
        # ST7789 expects data in Big Endian order (Most Significant Byte first)
        # NumPy arrays are usually Little Endian by default on x86/ARM
        # .byteswap() swaps the byte order within each 16-bit element
        # .tobytes() converts the NumPy array to a flat byte sequence
        pixel_bytes = rgb565.byteswap().tobytes()

        # Set the drawing window to the full screen
        self.set_window()

        # Write the pixel data
        self.data(pixel_bytes)

    def clear(self, color: Tuple[int, int, int] = (0, 0, 0)) -> None:
        """
        Fill the entire display with a single solid color.

        Args:
            color: A tuple representing the RGB color (e.g., (255, 0, 0) for red).
                   Defaults to black (0, 0, 0).
        """
        # Create a blank image with the specified background color
        # Although slightly less efficient than sending a repeated color value,
        # this reuses the optimized display_image path.
        img = Image.new('RGB', (self.width, self.height), color)
        self.display_image(img)

    def draw_text(self,
                  text: str,
                  font_path: str,
                  font_size: int = 20,
                  position: Tuple[int, int] = (10, 10),
                  text_color: Tuple[int, int, int] = (255, 255, 255),
                  bg_color: Tuple[int, int, int] = (0, 0, 0)) -> None:
        """
        Draw text onto the display using a specified TTF font.

        Creates an image buffer, draws the text onto it, and then displays
        the buffer.

        Args:
            text: The string to display.
            font_path: Path to the TrueType (.ttf) font file.
            font_size: The desired font size in points.
            position: A tuple (x, y) for the top-left corner of the text.
            text_color: RGB tuple for the text color.
            bg_color: RGB tuple for the background color.
        """
        # Create a new image with the desired background color
        image = Image.new('RGB', (self.width, self.height), bg_color)
        draw = ImageDraw.Draw(image)

        # Load the font
        try:
            font = ImageFont.truetype(font_path, font_size)
        except IOError:
            print(f"Warning: Could not load font '{font_path}'. Using default PIL font.")
            try:
                 # Pillow >= 9. PIL.ImageFont.load_default has a size parameter
                 font = ImageFont.load_default(size=font_size)
            except TypeError:
                 # Older Pillow or basic PIL fallback
                 font = ImageFont.load_default()


        # Get text bounding box to optionally center or align
        # text_bbox = draw.textbbox(position, text, font=font) # Pillow >= 8.0.0
        # text_width = text_bbox[2] - text_bbox[0]
        # text_height = text_bbox[3] - text_bbox[1]

        # Draw the text onto the image buffer
        draw.text(position, text, font=font, fill=text_color)

        # Display the image buffer on the screen
        self.display_image(image)

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Control ST7789 display via SPI (gpiod v2). Display image, text, or clear.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter # Show default values in help
    )

    # --- Display Content Arguments ---
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--image', type=str, metavar='PATH', help='Path to the image file to display.')
    group.add_argument('--text', type=str, metavar='STRING', help='Text string to display.')
    group.add_argument('--clear', action='store_true', help='Clear the display to the background color (default: black).')

    # --- Text Specific Arguments ---
    parser.add_argument('--font', type=str, metavar='PATH', default=None,
                        help='Path to TTF font file (required for --text).')
    parser.add_argument('--fontsize', type=int, default=24, metavar='POINTS', help='Font size for text.')
    parser.add_argument('--text-color', type=str, default="255,255,255", metavar='"R,G,B"',
                        help='Text color (0-255).')
    parser.add_argument('--bg-color', type=str, default="0,0,0", metavar='"R,G,B"',
                        help='Background color (0-255). Used for --clear and --text.')
    parser.add_argument('--position', type=str, default="10,10", metavar='"X,Y"',
                        help='Top-left position (pixels) for text.')

    # --- Hardware Configuration Arguments ---
    parser.add_argument('--spi-port', type=int, default=0, metavar='N',
                        help='SPI port number (e.g., 0 for /dev/spidevN.x)')
    parser.add_argument('--spi-device', type=int, default=0, metavar='N',
                        help='SPI device/chip-select number (e.g., 0 for /dev/spidevX.n)')
    parser.add_argument('--spi-speed', type=int, default=40_000_000, metavar='HZ',
                        help='SPI clock speed in Hz (e.g., 40000000 for 40MHz)')
    parser.add_argument('--dc-pin', type=int, required=True, metavar='NUM', # Made required
                        help='GPIO pin number (Linux sysfs numbering) for DC.')
    parser.add_argument('--rst-pin', type=int, required=True, metavar='NUM', # Made required
                        help='GPIO pin number (Linux sysfs numbering) for RST.')
    # Use gpioinfo to find the correct chip paths for your specific board/setup
    parser.add_argument('--gpio-chip-dc', type=str, required=True, metavar='PATH', # Made required
                        help="GPIO chip FULL PATH for DC pin (e.g., '/dev/gpiochip4'). Found via 'gpioinfo'.")
    parser.add_argument('--gpio-chip-rst', type=str, required=True, metavar='PATH', # Made required
                        help="GPIO chip FULL PATH for RST pin (e.g., '/dev/gpiochip1'). Found via 'gpioinfo'.")

    args = parser.parse_args()

    # --- Input Validation & Parsing ---
    if args.text and not args.font:
        parser.error("--font FONT_PATH is required when using --text")
    if args.font and not os.path.exists(args.font):
        parser.error(f"Font file not found: {args.font}")
    if args.image and not os.path.exists(args.image):
        parser.error(f"Image file not found: {args.image}")

    def parse_color(color_str: str) -> Tuple[int, int, int]:
        """Helper to parse 'R,G,B' color strings."""
        try:
            parts = tuple(map(int, color_str.split(',')))
            if len(parts) == 3 and all(0 <= c <= 255 for c in parts):
                return parts # type: ignore
            else:
                raise ValueError("Color must have 3 components (0-255).")
        except ValueError as e:
            parser.error(f"Invalid color format: '{color_str}'. Use 'R,G,B'. Error: {e}")

    def parse_position(pos_str: str) -> Tuple[int, int]:
        """Helper to parse 'X,Y' position strings."""
        try:
            parts = tuple(map(int, pos_str.split(',')))
            if len(parts) == 2:
                return parts # type: ignore
            else:
                raise ValueError("Position must have 2 components (X,Y).")
        except ValueError as e:
            parser.error(f"Invalid position format: '{pos_str}'. Use 'X,Y'. Error: {e}")

    text_color = parse_color(args.text_color)
    bg_color = parse_color(args.bg_color)
    position = parse_position(args.position)

    # --- Initialize and Run ---
    display: Optional[ST7789] = None
    try:
        print("Starting ST7789 display control script...")
        # Create the display driver instance
        display = ST7789(
            spi_port=args.spi_port,
            spi_device=args.spi_device,
            spi_speed_hz=args.spi_speed,
            gpio_chip_dc_path=args.gpio_chip_dc,
            dc_pin=args.dc_pin,
            gpio_chip_rst_path=args.gpio_chip_rst,
            rst_pin=args.rst_pin
            # width and height use defaults unless overridden
        )

        # Perform the requested action
        if args.image:
            print(f"Loading image: {args.image}")
            img = Image.open(args.image)
            print("Displaying image...")
            start_time = time.monotonic()
            display.display_image(img)
            end_time = time.monotonic()
            print(f"Image displayed in {end_time - start_time:.3f} seconds.")
        elif args.text:
            print(f"Rendering text: '{args.text}'")
            start_time = time.monotonic()
            display.draw_text(args.text, args.font, args.fontsize, position, text_color, bg_color)
            end_time = time.monotonic()
            print(f"Text displayed in {end_time - start_time:.3f} seconds.")
        elif args.clear:
             print(f"Clearing display to color {bg_color}...")
             start_time = time.monotonic()
             display.clear(bg_color)
             end_time = time.monotonic()
             print(f"Display cleared in {end_time - start_time:.3f} seconds.")

        print("Operation complete. Script will keep running to maintain display.")
        print("Press Ctrl+C to exit.")
        # Keep the script alive to prevent the display from clearing or
        # to allow for future interactions if extended.
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nCaught Ctrl+C, exiting gracefully...")
    except ImportError as e:
         print(f"\nImport Error: {e}")
         print("Please ensure required libraries are installed:")
         print("  pip install Pillow numpy python-spidev python-gpiod")
         print("Make sure you are using python3.")
    except Exception as e:
         print(f"\nAn unexpected error occurred: {e}")
         import traceback
         traceback.print_exc()
    finally:
        # Ensure resources are always released
        if display:
            display.close()
        print("Script finished.")
