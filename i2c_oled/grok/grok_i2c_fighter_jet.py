# Fighter jet game
# Author: Grok 3
# License: Public Domain

# Up arrow - move up
# Down arrow - move down
# Space - shoot

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

# Game variables
jet_slot = 1  # Start in the middle slot (0, 1, 2)
rockets = []  # List of (x, slot) for rockets
bullets = []  # List of (x, slot) for bullets
game_over = False
frame_count = 0

try:
    while not game_over:
        # Handle user input
        key = stdscr.getch()
        if key == curses.KEY_UP and jet_slot > 0:
            jet_slot -= 1  # Move jet up
        elif key == curses.KEY_DOWN and jet_slot < 2:
            jet_slot += 1  # Move jet down
        elif key == ord(' '):
            # Shoot a bullet from the jet's position
            bullets.append((12, jet_slot))

        # Move rockets left by 2 pixels
        for i in range(len(rockets)):
            rockets[i] = (rockets[i][0] - 2, rockets[i][1])
        
        # Move bullets right by 4 pixels
        for i in range(len(bullets)):
            bullets[i] = (bullets[i][0] + 4, bullets[i][1])
        
        # Remove off-screen rockets and bullets
        rockets = [r for r in rockets if r[0] + 3 >= 0]
        bullets = [b for b in bullets if b[0] <= 127]
        
        # Spawn new rockets every 20 frames
        if frame_count % 20 == 0:
            slot = random.randint(0, 2)
            rockets.append((127, slot))
        
        # Check for bullet-rocket collisions
        for bullet in bullets[:]:
            for rocket in rockets[:]:
                if bullet[1] == rocket[1] and bullet[0] >= rocket[0] and bullet[0] <= rocket[0] + 3:
                    bullets.remove(bullet)
                    rockets.remove(rocket)
                    break  # One bullet hits one rocket
        
        # Check for rocket-jet collisions
        for rocket in rockets:
            if rocket[1] == jet_slot and rocket[0] <= 11:
                game_over = True
                break
        
        # Render the scene
        with canvas(device) as draw:
            # Draw the jet (12x4 rectangle)
            jet_y = jet_slot * 8
            draw.rectangle((0, jet_y + 2, 11, jet_y + 5), fill="white")
            
            # Draw bullets (2x1 rectangles)
            for x, slot in bullets:
                y = slot * 8 + 3
                draw.rectangle((x, y, x + 1, y), fill="white")
            
            # Draw rockets (4x8 rectangles)
            for x, slot in rockets:
                y = slot * 8
                draw.rectangle((x, y, x + 3, y + 7), fill="white")
        
        # Increment frame counter
        frame_count += 1
        
        # Control frame rate (20 FPS)
        time.sleep(0.05)

finally:
    # Clean up
    curses.endwin()  # Restore terminal
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, fill="black")  # Clear display
