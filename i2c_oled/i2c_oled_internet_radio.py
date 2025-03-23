#!/usr/bin/env python3

"""
Internet Radio | OLED I2C [128x32] @ Radxa Rock 5C Lite
Author: Deepseek R1 + https://github.com/c0m4r
License: Public Domain
"""

import sys
import json
import socket
import subprocess
import threading
from time import sleep, time
from typing import Optional

from periphery import I2C
from PIL import Image, ImageDraw, ImageFont


class RadioDisplay:
    """A class to display radio metadata on an OLED screen with scrolling text.

    Attributes:
        url: URL of the radio stream to play
        i2c: I2C connection object
        address: I2C device address
        width: OLED display width in pixels
        height: OLED display height in pixels
        current_title: Current track title to display
        previous_title: Previously displayed track title
        scroll_pos: Current horizontal scroll position
        font: Font used for text rendering
        running: Flag to control execution threads
        title_changed: Flag indicating title update
        last_update: Timestamp of last scroll update
        scroll_speed: Scrolling speed in pixels per second
        sock_path: Path for MPV IPC socket
        mpv_process: MPV player subprocess handle
    """

    def __init__(self, url: str, bus: str = "/dev/i2c-8", address: int = 0x3C) -> None:
        """Initialize the RadioDisplay instance.

        Args:
            url: URL of the radio stream to play
            bus: I2C bus device path
            address: I2C device address
        """
        self.url = url
        self.i2c = I2C(bus)
        self.address = address
        self.width = 128
        self.height = 32
        self.current_title = "d(^__^)b"
        self.previous_title = ""
        self.scroll_pos = 0
        self.font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        self.running = True
        self.title_changed = False
        self.last_update = 0
        self.scroll_speed = 20  # pixels per second
        self.sock_path = "/tmp/mpv_socket"
        self.mpv_process: Optional[subprocess.Popen] = None
        self._initialize_display()

    def _send_command(self, cmd: int) -> None:
        """Send a command to the OLED controller.

        Args:
            cmd: Command byte to send to the display controller
        """
        msg = I2C.Message([0x00, cmd])
        self.i2c.transfer(self.address, [msg])

    def _initialize_display(self) -> None:
        """Initialize the OLED display with required configuration commands."""
        init_commands = [
            0xAE, 0xD5, 0x80, 0xA8, 0x1F, 0xD3, 0x00, 0x40,
            0x8D, 0x14, 0x20, 0x00, 0xA1, 0xC8, 0xDA, 0x02,
            0x81, 0xCF, 0xD9, 0xF1, 0xDB, 0x40, 0xA4, 0xA6, 0xAF
        ]
        for cmd in init_commands:
            self._send_command(cmd)
        self.clear_display()

    def clear_display(self) -> None:
        """Clear the entire display by writing blank pixels."""
        for page in range(4):
            self._send_command(0xB0 + page)
            self._send_command(0x00)
            self._send_command(0x10)
            blank_data = [0x40] + [0x00] * self.width
            msg = I2C.Message(blank_data)
            self.i2c.transfer(self.address, [msg])

    def _draw_text(self) -> None:
        """Render the current title on the display with scrolling or centering.

        Uses Pillow's ImageDraw to create a frame buffer and sends it to the OLED.
        Handles both static centered text and smooth scrolling for long titles.
        """
        img = Image.new("1", (self.width, self.height))
        draw = ImageDraw.Draw(img)

        text = self.current_title
        text_width = draw.textlength(text, font=self.font)
        x_pos = int(self.scroll_pos)

        if text_width <= self.width:
            # Center text if it fits
            x = (self.width - text_width) // 2
            draw.text((x, 10), text, font=self.font, fill=1)
        else:
            # Draw scrolling text with wrap-around
            draw.text((x_pos, 10), text, font=self.font, fill=1)
            draw.text((x_pos - text_width - 20, 10), text, font=self.font, fill=1)

        # Update display
        for page in range(4):
            self._send_command(0xB0 + page)
            self._send_command(0x00)
            self._send_command(0x10)
            page_data = []
            for col in range(self.width):
                byte = 0
                for bit in range(8):
                    try:
                        pixel = img.getpixel((col, page * 8 + bit))
                    except IndexError:
                        pixel = 0
                    byte |= pixel << bit
                page_data.append(byte)
            msg = I2C.Message([0x40] + page_data)
            self.i2c.transfer(self.address, [msg])

    def _mpv_ipc_handler(self) -> None:
        """Manage MPV IPC connection and metadata updates.

        Starts the MPV player with IPC socket and continuously polls for metadata updates.
        Handles connection errors and retries automatically.
        """
        mpv_cmd = [
            "mpv",
            "--no-video",
            "--idle=yes",
            f"--input-ipc-server={self.sock_path}",
            self.url
        ]
        self.mpv_process = subprocess.Popen(mpv_cmd)

        while self.running:
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                    s.connect(self.sock_path)
                    while self.running:
                        s.send(b'{ "command": ["get_property", "metadata"] }\n')
                        data = s.recv(4096)
                        try:
                            metadata = json.loads(data.decode())["data"]
                            new_title = ""
                            if "icy-title" in metadata:
                                new_title = metadata["icy-title"]
                            elif "Title" in metadata:
                                new_title = metadata["Title"]

                            if new_title and new_title != self.current_title:
                                self.previous_title = self.current_title
                                self.current_title = new_title
                                self.title_changed = True

                        except (KeyError, json.JSONDecodeError):
                            pass
                        sleep(1)
            except (ConnectionRefusedError, FileNotFoundError):
                sleep(1)

    def _title_scroller(self) -> None:
        """Manage text scrolling animation and display updates.

        Implements smooth scrolling logic with configurable speed and pause durations.
        Handles both static text centering and animated scrolling based on text length.
        """
        text_width = 0
        last_title = ""
        scroll_cycle = 0
        pause_duration = 2  # Seconds to pause at start/end

        while self.running:
            img = Image.new("1", (self.width, self.height))
            draw = ImageDraw.Draw(img)
            text_width = draw.textlength(self.current_title, font=self.font)

            if self.title_changed:
                self.scroll_pos = 0
                self.title_changed = False
                last_title = self.current_title
                scroll_cycle = text_width + self.width + 20
                self.last_update = int(time())

            if text_width > self.width:
                elapsed = time() - self.last_update
                self.scroll_pos = int((elapsed * self.scroll_speed) % scroll_cycle)

                if self.scroll_pos > scroll_cycle - self.width:
                    self.scroll_pos = 0
                    self.last_update = int(time())
                    sleep(pause_duration)
            else:
                self.scroll_pos = 0
                if self.current_title != last_title:
                    self.last_update = int(time())
                    last_title = self.current_title
                    sleep(pause_duration)

            self._draw_text()
            sleep(0.05)

    def run(self) -> None:
        """Main execution method to start radio playback and display.

        Starts IPC handler thread and title scroller in main thread.
        Handles keyboard interrupts for clean shutdown.
        """
        try:
            ipc_thread = threading.Thread(target=self._mpv_ipc_handler)
            ipc_thread.start()
            self._title_scroller()
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        """Cleanup method to stop playback and reset display.

        Terminates MPV process, clears display, and closes I2C connection.
        """
        self.running = False
        if self.mpv_process:
            self.mpv_process.terminate()
        self.clear_display()
        self.i2c.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <radio-url>")
        sys.exit(1)

    display = RadioDisplay(sys.argv[1])
    try:
        display.run()
    except KeyboardInterrupt:
        display.stop()
