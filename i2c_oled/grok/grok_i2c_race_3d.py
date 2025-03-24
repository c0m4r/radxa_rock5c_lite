# 3D-effect racing game
# Author: Grok 3
# License: Public Domain

# Controls:
# A - turn left
# D - turn right

import time
import random
import curses
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306

# Initialize the OLED display
serial = i2c(port=8, address=0x3C)  # Matches /dev/i2c-8 and address 0x3C
device = ssd1306(serial)

# Initialize curses for non-blocking keyboard input
stdscr = curses.initscr()
curses.noecho()
curses.cbreak()
stdscr.keypad(True)
stdscr.nodelay(True)

# Game variables
player_lane = 1  # Start in middle lane (0, 1, or 2)
obstacles = []   # List of {'y': int, 'lane': int}
score = 0
running = True

# Player's car x-positions for each lane (centers at y=31)
player_x_positions = [21, 63, 105]

# Function to draw the game scene
def draw_scene(draw):
    # Draw road dividers for 3D effect
    for i in range(4):
        x_bottom = i * 127 // 3  # Dividers at 0, 42, 84, 127 at bottom
        draw.line((64, 0, x_bottom, 31), fill="white")
    
    # Draw player's car
    player_x = player_x_positions[player_lane]
    draw.rectangle((player_x - 2, 28, player_x + 2, 31), fill="white")
    
    # Draw obstacles
    for obs in obstacles:
        y = obs['y']
        lane = obs['lane']
        # Calculate x-center based on lane and perspective
        x_center_bottom = player_x_positions[lane]
        x_center = 64 + (x_center_bottom - 64) * (y / 31)
        w = 1 + int(4 * (y / 31))  # Width grows from 1 to 5 pixels
        draw.line((x_center - w//2, y, x_center + w//2, y), fill="white")

# Main game loop
try:
    while running:
        # Handle keyboard input
        key = stdscr.getch()
        if key == ord('a') and player_lane > 0:
            player_lane -= 1  # Move left
        elif key == ord('d') and player_lane < 2:
            player_lane += 1  # Move right
        elif key == ord('q'):
            running = False   # Quit game
        
        # Update obstacles
        for obs in obstacles[:]:  # Copy list to modify during iteration
            obs['y'] += 1
            if obs['y'] >= 31:
                if obs['lane'] == player_lane:
                    running = False  # Collision: game over
                else:
                    score += 1       # Obstacle avoided
                obstacles.remove(obs)
        
        # Spawn new obstacles (10% chance per frame)
        if random.random() < 0.1:
            new_lane = random.randint(0, 2)
            obstacles.append({'y': 0, 'lane': new_lane})
        
        # Draw the current frame
        with canvas(device) as draw:
            draw_scene(draw)
        
        # Maintain ~30 FPS
        time.sleep(0.033)

finally:
    # Clean up terminal
    curses.nocbreak()
    stdscr.keypad(False)
    curses.echo()
    curses.endwin()
    
    # Display game over screen with score
    with canvas(device) as draw:
        draw.text((10, 10), "Game Over", fill="white")
        draw.text((10, 20), f"Score: {score}", fill="white")
    time.sleep(2)  # Show score for 2 seconds before exiting
