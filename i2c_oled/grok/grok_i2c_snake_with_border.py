# Snake game
# Author: Grok 3
# Licence: Public Domain

import curses
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from collections import deque
import time
import random

# Function to generate food at a random position not occupied by the snake
def generate_food(snake, grid_width, grid_height):
    while True:
        x = random.randint(0, grid_width - 1)
        y = random.randint(0, grid_height - 1)
        if (x, y) not in snake:
            return (x, y)

# Initialize the OLED display
serial = i2c(port=8, address=0x3C)  # Adjust port if necessary
device = ssd1306(serial, width=128, height=32)

# Initialize curses for terminal input
stdscr = curses.initscr()
curses.cbreak()          # Disable line buffering
stdscr.keypad(True)      # Enable keypad mode for arrow keys
stdscr.nodelay(True)     # Non-blocking input

# Set the size of each snake segment in pixels
segment_size = 6

# Playable area is 126x30 pixels, leaving a 1-pixel border
grid_width = 126 // segment_size
grid_height = 30 // segment_size

# Initialize snake near the left-center of the grid
snake = deque([(2, grid_height//2), (3, grid_height//2), (4, grid_height//2)])
direction = (1, 0)  # Initial direction: right (dx, dy)
food = generate_food(snake, grid_width, grid_height)
game_over = False
update_interval = 0.2  # Snake moves every 0.2 seconds
last_update = time.time()

try:
    while not game_over:
        # Capture arrow key input
        key = stdscr.getch()
        if key == curses.KEY_UP and direction != (0, 1):       # Prevent reversing
            direction = (0, -1)  # Up
        elif key == curses.KEY_DOWN and direction != (0, -1):
            direction = (0, 1)   # Down
        elif key == curses.KEY_LEFT and direction != (1, 0):
            direction = (-1, 0)  # Left
        elif key == curses.KEY_RIGHT and direction != (-1, 0):
            direction = (1, 0)   # Right

        # Update game state at fixed intervals
        current_time = time.time()
        if current_time - last_update >= update_interval:
            # Calculate new head position
            head = snake[-1]
            new_head = (head[0] + direction[0], head[1] + direction[1])

            # Check for collisions with walls or body
            if (new_head[0] < 0 or new_head[0] >= grid_width or
                new_head[1] < 0 or new_head[1] >= grid_height or
                (new_head in snake and new_head != snake[0])):
                game_over = True
            else:
                snake.append(new_head)  # Add new head
                if new_head == food:
                    food = generate_food(snake, grid_width, grid_height)  # New food
                else:
                    snake.popleft()  # Move by removing tail

            last_update = current_time

        # Render the game on the OLED with a visible white border
        with canvas(device) as draw:
            # Draw the white border around the entire display
            draw.rectangle((0, 0, 127, 31), outline="white", fill="black")

            # Draw snake segments within the playable area
            for segment in snake:
                x, y = segment
                pixel_x = 1 + x * segment_size
                pixel_y = 1 + y * segment_size
                draw.rectangle((pixel_x, pixel_y, pixel_x + segment_size - 1, 
                               pixel_y + segment_size - 1), fill="white")

            # Draw food within the playable area
            x, y = food
            pixel_x = 1 + x * segment_size
            pixel_y = 1 + y * segment_size
            draw.rectangle((pixel_x, pixel_y, pixel_x + segment_size - 1, 
                           pixel_y + segment_size - 1), fill="white")

        # Small delay to prevent CPU overload
        time.sleep(0.01)

finally:
    # Clean up on exit
    curses.endwin()  # Restore terminal settings
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, fill="black")  # Clear display
