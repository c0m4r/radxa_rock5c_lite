# Race game
# Author: Grok 3
# License: Public Domain

# up arrow - move up
# down arrow - move down

import curses
import time
import random
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306

# Initialize the OLED display (I2C port 8, address 0x3C)
serial = i2c(port=8, address=0x3C)
device = ssd1306(serial, width=128, height=32)

# Initialize curses for keyboard input
stdscr = curses.initscr()
curses.cbreak()
stdscr.keypad(True)
stdscr.nodelay(True)  # Non-blocking input

# Define the Formula 1 car shape as rectangles (left, top, right, bottom) relative to its top-left corner
car_parts = [
    (2, 2, 21, 5),   # Main body
    (0, 3, 1, 4),    # Front wing
    (22, 3, 23, 4),  # Rear wing
    (4, 6, 5, 7),    # Front wheel
    (18, 6, 19, 7)   # Rear wheel
]

# Game variables
car_slot = 1  # Start in the middle slot (0, 1, 2)
obstacles = []  # List of (x, slots_occupied)
game_over = False
frame_count = 0
obstacle_width = 4  # Fixed width of obstacles

try:
    while not game_over:
        # Handle user input
        key = stdscr.getch()
        if key == curses.KEY_UP and car_slot > 0:
            car_slot -= 1  # Move car up
        elif key == curses.KEY_DOWN and car_slot < 2:
            car_slot += 1  # Move car down

        # Update obstacle positions
        for i in range(len(obstacles)):
            obstacles[i] = (obstacles[i][0] - 2, obstacles[i][1])
        # Remove off-screen obstacles
        obstacles = [obs for obs in obstacles if obs[0] + obstacle_width >= 0]

        # Generate new obstacles every 30 frames (50% less frequent than 20)
        if frame_count % 30 == 0:
            if random.random() < 0.5:
                # Single-slot obstacle
                slot = random.randint(0, 2)
                obstacles.append((127, [slot]))
            else:
                # Double-slot obstacle
                slots = random.choice([[0, 1], [1, 2]])
                obstacles.append((127, slots))

        # Check for collisions
        for obs_x, obs_slots in obstacles:
            if car_slot in obs_slots and obs_x <= 23:
                game_over = True
                break

        # Render the scene
        with canvas(device) as draw:
            # Draw the car
            car_y = car_slot * 8
            for left, top, right, bottom in car_parts:
                draw.rectangle((0 + left, car_y + top, 0 + right, car_y + bottom), fill="white")
            # Draw obstacles
            for obs_x, obs_slots in obstacles:
                y_min = min(obs_slots) * 8
                y_max = (max(obs_slots) + 1) * 8 - 1
                draw.rectangle((obs_x, y_min, obs_x + obstacle_width - 1, y_max), fill="white")

        # Increment frame counter
        frame_count += 1

        # Control frame rate (20 FPS)
        time.sleep(0.05)

finally:
    # Clean up
    curses.endwin()  # Restore terminal
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, fill="black")  # Clear display
