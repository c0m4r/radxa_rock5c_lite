#!/usr/bin/env python3

"""
Vibe-coded with Gemini 2.5 Pro Experimental 03-25
https://github.com/c0m4r
License: Public Domain
"""

import time
import spidev
import gpiod
from gpiod.line import Direction, Value # Import constants as shown in example
import numpy as np
import subprocess
from PIL import Image
import sys
import os

# --- Configuration ---

# GPIO Configuration (Update these paths and offsets for your hardware)
# If DC and RST are on DIFFERENT chips, this script needs modification
# using gpiod.Chip() for each.
GPIO_CHIP_PATH = "/dev/gpiochip4" # Assume both lines are on this chip for now
DC_LINE_OFFSET = 12               # Offset for DC line
RST_LINE_OFFSET = 5               # Offset for RST line
GPIO_CONSUMER = "st7789-player-py" # Consumer name for GPIO requests

# Display Parameters
WIDTH = 320
HEIGHT = 240
# Common rotation values for MADCTL (0x36) command:
# 0x00: Portrait (0 degrees)
# 0x60: Landscape (90 degrees, Y Mirror, X/Y Swap)
# 0xC0: Inverted Portrait (180 degrees)
# 0xA0: Inverted Landscape (270 degrees, X Mirror, X/Y Swap)
ROTATION = 0x60 # Example: Landscape

# SPI Configuration
SPI_BUS = 0
SPI_DEVICE = 0
SPI_MAX_SPEED_HZ = 80000000 # 80 MHz (adjust if needed)
SPI_CHUNK_SIZE = 4096       # Max bytes to write in one SPI call

# Video Processing
TARGET_FPS = 25

# Global SPI object
spi = None

# --- Helper Functions ---

def spi_write(data_list):
    """Writes a list of bytes to SPI, handling chunking."""
    global spi
    if not spi:
        print("Error: SPI not initialized.", file=sys.stderr)
        return
    try:
        for i in range(0, len(data_list), SPI_CHUNK_SIZE):
            spi.writebytes(data_list[i:i+SPI_CHUNK_SIZE])
    except Exception as e:
        print(f"Error during SPI write: {e}", file=sys.stderr)
        # Depending on error, might want to re-init SPI or exit

def write_command(cmd, gpio_request):
    """Sets DC low and sends a command byte via SPI."""
    gpio_request.set_value(DC_LINE_OFFSET, Value.INACTIVE) # DC low
    spi_write([cmd])

def write_data(data, gpio_request):
    """Sets DC high and sends data byte(s) via SPI."""
    gpio_request.set_value(DC_LINE_OFFSET, Value.ACTIVE) # DC high
    data_list = []
    if isinstance(data, int):
        data_list = [data]
    elif isinstance(data, (bytes, bytearray)):
        data_list = list(data) # Convert bytes/bytearray to list of ints
    elif isinstance(data, list):
        data_list = data # Assume list of ints
    else:
        print(f"Warning: Unsupported data type for write_data: {type(data)}", file=sys.stderr)
        return
    spi_write(data_list)

def reset_display(gpio_request):
    """Resets the display using the RST line."""
    print("Resetting display...")
    gpio_request.set_value(RST_LINE_OFFSET, Value.INACTIVE) # RST low
    time.sleep(0.1)
    gpio_request.set_value(RST_LINE_OFFSET, Value.ACTIVE)   # RST high
    time.sleep(0.1)
    print("Reset complete.")

def init_display(gpio_request):
    """Initializes the ST7789 display sequence."""
    print("Initializing display...")
    reset_display(gpio_request)

    write_command(0x11, gpio_request) # Sleep out
    time.sleep(0.12)

    write_command(0x3A, gpio_request) # Color mode
    write_data(0x55, gpio_request)    # 16-bit/pixel (RGB565)

    write_command(0x36, gpio_request) # MADCTL (Memory Data Access Control)
    write_data(ROTATION, gpio_request) # Apply chosen rotation

    # Optional: Inversion Commands (uncomment if colors are inverted)
    # write_command(0x21, gpio_request) # Display Inversion ON
    # write_command(0x20, gpio_request) # Display Inversion OFF (Default)

    # Optional: Brightness Control (if supported and needed)
    # write_command(0x51, gpio_request) # Write Display Brightness Value
    # write_data(0xFF, gpio_request)    # Max brightness (0x00 to 0xFF)

    write_command(0x29, gpio_request) # Display on
    time.sleep(0.1)
    print("Display initialized.")

def set_address_window(x0, y0, x1, y1, gpio_request):
    """Sets the drawing window area on the display."""
    write_command(0x2A, gpio_request) # Column address set (CASET)
    write_data([ (x0 >> 8) & 0xFF, x0 & 0xFF, (x1 >> 8) & 0xFF, x1 & 0xFF ], gpio_request)
    write_command(0x2B, gpio_request) # Row address set (RASET)
    write_data([ (y0 >> 8) & 0xFF, y0 & 0xFF, (y1 >> 8) & 0xFF, y1 & 0xFF ], gpio_request)
    write_command(0x2C, gpio_request) # Memory write command (RAMWR) - data follows

def display_frame_rgb565(img, gpio_request):
    """Converts PIL RGB Image to RGB565 and sends to display."""
    if img.mode != 'RGB':
        img = img.convert('RGB')

    # Convert to NumPy array
    pixel_data_rgb888 = np.array(img, dtype=np.uint8)

    # Convert RGB888 to RGB565
    r = (pixel_data_rgb888[:,:,0].astype(np.uint16) >> 3)
    g = (pixel_data_rgb888[:,:,1].astype(np.uint16) >> 2)
    b = (pixel_data_rgb888[:,:,2].astype(np.uint16) >> 3)
    pixel_data_rgb565 = (r << 11) | (g << 5) | b

    # Convert to big-endian bytes (>u2 = big-endian unsigned 16-bit)
    pixel_data_bytes = pixel_data_rgb565.astype('>u2').tobytes()

    # Set window to full screen
    set_address_window(0, 0, WIDTH - 1, HEIGHT - 1, gpio_request)

    # Send pixel data
    write_data(pixel_data_bytes, gpio_request)

def extract_frames(input_file):
    """Starts ffmpeg to extract frames as raw RGB24 data pipe."""
    print(f"Starting ffmpeg for {input_file} at {TARGET_FPS} FPS...")
    command = [
        'ffmpeg',
        '-loglevel', 'warning',  # Reduce verbose output, show errors/warnings
        '-nostdin',             # Don't read from stdin
        '-i', input_file,
        '-vf', f'fps={TARGET_FPS},scale={WIDTH}:{HEIGHT}:flags=lanczos', # Filtergraph
        '-pix_fmt', 'rgb24',    # Output format: 8-bit R, G, B
        '-f', 'rawvideo',       # Output container format
        '-',                    # Output to stdout
    ]
    try:
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=-1)
        # Check immediately if it errored on startup
        time.sleep(0.1) # Give ffmpeg a moment
        if proc.poll() is not None:
            stderr_output = proc.stderr.read().decode(errors='ignore')
            print(f"Error: ffmpeg failed to start. Exit code: {proc.returncode}", file=sys.stderr)
            print("FFmpeg stderr:\n", stderr_output, file=sys.stderr)
            return None
        print("ffmpeg process started.")
        return proc
    except FileNotFoundError:
        print("Error: 'ffmpeg' command not found. Is ffmpeg installed and in PATH?", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error starting ffmpeg: {e}", file=sys.stderr)
        return None

# --- Main Playback Logic ---

def play_video(video_path):
    global spi
    if not os.path.isfile(video_path):
        print(f"Error: Video file not found: '{video_path}'", file=sys.stderr)
        return

    frame_size = WIDTH * HEIGHT * 3 # 3 bytes per pixel (RGB24)
    frame_interval = 1.0 / TARGET_FPS
    ffmpeg_proc = None

    try:
        # --- Initialize SPI ---
        print("Initializing SPI...")
        spi = spidev.SpiDev()
        spi.open(SPI_BUS, SPI_DEVICE)
        spi.max_speed_hz = SPI_MAX_SPEED_HZ
        spi.mode = 0
        print(f"SPI initialized: Bus {SPI_BUS}, Device {SPI_DEVICE}, Speed {SPI_MAX_SPEED_HZ} Hz")

        # --- Initialize GPIO using gpiod.request_lines ---
        print(f"Requesting GPIO lines on {GPIO_CHIP_PATH}...")
        # Define settings for each line
        line_config = {
            DC_LINE_OFFSET: gpiod.LineSettings(
                direction=Direction.OUTPUT,
                output_value=Value.INACTIVE # Start DC low for initial commands
            ),
            RST_LINE_OFFSET: gpiod.LineSettings(
                direction=Direction.OUTPUT,
                output_value=Value.ACTIVE   # Start RST high (not in reset)
            )
        }

        # Use 'with' for automatic GPIO cleanup
        with gpiod.request_lines(
            GPIO_CHIP_PATH,
            consumer=GPIO_CONSUMER,
            config=line_config
        ) as gpio_request:
            print("GPIO lines acquired.")

            # --- Initialize Display ---
            init_display(gpio_request)

            # Optional: Clear display
            print("Clearing display...")
            black_frame = Image.new('RGB', (WIDTH, HEIGHT), (0, 0, 0))
            display_frame_rgb565(black_frame, gpio_request)
            print("Display cleared.")

            # --- Start FFmpeg ---
            ffmpeg_proc = extract_frames(video_path)
            if not ffmpeg_proc:
                return # Exit if ffmpeg failed to start

            # --- Playback Loop ---
            print("Starting video playback loop...")
            frame_count = 0
            start_time = time.monotonic()
            last_fps_update_time = start_time

            while True:
                loop_start_time = time.monotonic()

                # Read frame from ffmpeg
                try:
                    in_bytes = ffmpeg_proc.stdout.read(frame_size)
                except Exception as read_err:
                    print(f"Error reading frame from ffmpeg: {read_err}", file=sys.stderr)
                    break # Exit loop

                if not in_bytes:
                    print("End of video stream (ffmpeg stdout closed).")
                    break # End of stream

                if len(in_bytes) < frame_size:
                    print(f"Warning: Incomplete frame received ({len(in_bytes)}/{frame_size}). Assuming end.", file=sys.stderr)
                    break

                # Convert bytes to PIL Image
                try:
                    frame_image = Image.frombytes('RGB', (WIDTH, HEIGHT), in_bytes)
                except Exception as img_err:
                    print(f"Error creating Image from bytes: {img_err}", file=sys.stderr)
                    continue # Skip this frame

                # Display the frame
                display_frame_rgb565(frame_image, gpio_request)
                frame_count += 1

                # --- Frame Rate Control ---
                loop_end_time = time.monotonic()
                processing_time = loop_end_time - loop_start_time
                sleep_time = frame_interval - processing_time
                if sleep_time > 0:
                    time.sleep(sleep_time)
                # else:
                #     print(f"Frame {frame_count}: Took too long ({processing_time:.4f}s)")

                # Optional: Periodic FPS update
                current_time = time.monotonic()
                if current_time - last_fps_update_time >= 2.0: # Update every 2 seconds
                    elapsed_total = current_time - start_time
                    if elapsed_total > 0:
                        actual_fps = frame_count / elapsed_total
                        print(f"Frames: {frame_count}, Time: {elapsed_total:.2f}s, FPS: {actual_fps:.2f}")
                    last_fps_update_time = current_time

            # --- End of Playback ---
            end_time = time.monotonic()
            total_time = end_time - start_time
            print(f"\nPlayback finished. Played {frame_count} frames in {total_time:.2f} seconds.")
            if total_time > 0:
                avg_fps = frame_count / total_time
                print(f"Average FPS: {avg_fps:.2f}")


    except FileNotFoundError as e:
        # Handle specific case of GPIO chip not found
        if GPIO_CHIP_PATH in str(e):
             print(f"Error: GPIO chip device not found: {e}", file=sys.stderr)
             print(f"Verify '{GPIO_CHIP_PATH}' exists and you have permissions.", file=sys.stderr)
        else:
            print(f"Error: File not found: {e}", file=sys.stderr)
    except PermissionError as e:
         print(f"Error: Permission denied accessing GPIO/SPI: {e}", file=sys.stderr)
         print("Try running with 'sudo' or check user group memberships (e.g., gpio, spi).", file=sys.stderr)
    except OSError as e:
         # Catch other OS-level errors like device busy or invalid argument
         print(f"Error interacting with device: {e}", file=sys.stderr)
    except ImportError as e:
        print(f"Error: Missing Python library: {e}", file=sys.stderr)
        print("Ensure 'spidev', 'gpiod', 'Pillow', 'numpy' are installed (`pip install ...`)")
    except KeyboardInterrupt:
        print("\nPlayback stopped by user (Ctrl+C).")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        # --- Cleanup ---
        print("Cleaning up resources...")

        # Terminate ffmpeg process if it's running
        if ffmpeg_proc and ffmpeg_proc.poll() is None:
            print("Terminating ffmpeg process...")
            ffmpeg_proc.terminate()
            try:
                ffmpeg_proc.wait(timeout=1.0) # Wait briefly
                print("ffmpeg terminated.")
            except subprocess.TimeoutExpired:
                print("ffmpeg did not terminate, killing...")
                ffmpeg_proc.kill()
            except Exception as kill_err:
                 print(f"Error during ffmpeg cleanup: {kill_err}", file=sys.stderr)
            # Close pipes
            if ffmpeg_proc.stdout: ffmpeg_proc.stdout.close()
            if ffmpeg_proc.stderr: ffmpeg_proc.stderr.close()


        # Close SPI
        if spi:
            spi.close()
            print("SPI closed.")

        # GPIO lines are released automatically by the 'with' statement

        print("Cleanup complete.")

# --- Script Entry Point ---

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <video_file_path>")
        # Example: Try a default file if none provided
        default_video = "video.webm"
        print(f"No video file provided. Trying default: '{default_video}'")
        if os.path.exists(default_video):
            video_file = default_video
        else:
            print(f"Default video '{default_video}' not found. Exiting.", file=sys.stderr)
            sys.exit(1)
    else:
        video_file = sys.argv[1]

    play_video(video_file)
