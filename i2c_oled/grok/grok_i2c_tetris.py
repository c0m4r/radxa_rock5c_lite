# Tetris clone
# Author: Deepseek R1
# License: Public Domain

import sys
import time
import random
import curses
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas

# OLED Configuration
serial = i2c(port=8, address=0x3C)
device = ssd1306(serial, rotate=1, width=128, height=32)  # Rotated 90 degrees

# Game Constants
COLUMNS = 8
ROWS = 24  # 24 rows * 4px = 96px (leaves 32px for score)
BLOCK_SIZE = 4

# Tetromino Shapes
SHAPES = [
    # I
    [[(0,0), (1,0), (2,0), (3,0)],
     [(0,0), (0,1), (0,2), (0,3)]],
    # O
    [[(0,0), (1,0), (0,1), (1,1)]],
    # T
    [[(1,0), (0,1), (1,1), (2,1)],
     [(1,0), (1,1), (2,1), (1,2)],
     [(0,1), (1,1), (2,1), (1,2)],
     [(1,0), (0,1), (1,1), (1,2)]],
    # L
    [[(0,0), (0,1), (0,2), (1,2)],
     [(0,1), (1,1), (2,1), (0,2)],
     [(0,0), (1,0), (1,1), (1,2)],
     [(2,0), (0,1), (1,1), (2,1)]],
    # J
    [[(1,0), (1,1), (1,2), (0,2)],
     [(0,0), (0,1), (1,1), (2,1)],
     [(0,0), (0,1), (0,2), (1,0)],
     [(0,0), (1,0), (2,0), (2,1)]],
    # S
    [[(1,0), (2,0), (0,1), (1,1)],
     [(0,0), (0,1), (1,1), (1,2)]],
    # Z
    [[(0,0), (1,0), (1,1), (2,1)],
     [(1,0), (0,1), (1,1), (0,2)]]
]

class Tetris:
    def __init__(self):
        self.grid = [[0] * COLUMNS for _ in range(ROWS)]
        self.current_shape = None
        self.current_x = 0
        self.current_y = 0
        self.current_rot = 0
        self.score = 0
        self.game_over = False
        self.new_shape()

    def new_shape(self):
        self.current_shape = random.choice(SHAPES)
        self.current_rot = 0
        self.current_x = COLUMNS // 2 - 2
        self.current_y = 0
        
        if self.check_collision():
            self.game_over = True

    def check_collision(self, dx=0, dy=0, rot=None):
        rot = self.current_rot if rot is None else rot
        shape = self.current_shape[rot % len(self.current_shape)]
        for (x, y) in shape:
            new_x = self.current_x + x + dx
            new_y = self.current_y + y + dy
            if new_x < 0 or new_x >= COLUMNS or new_y >= ROWS:
                return True
            if new_y >= 0 and self.grid[new_y][new_x]:
                return True
        return False

    def rotate(self):
        new_rot = (self.current_rot + 1) % len(self.current_shape)
        if not self.check_collision(rot=new_rot):
            self.current_rot = new_rot

    def move(self, dx):
        if not self.check_collision(dx=dx):
            self.current_x += dx

    def drop(self):
        if not self.check_collision(dy=1):
            self.current_y += 1
            return True
        self.merge_shape()
        self.clear_lines()
        self.new_shape()
        return False

    def merge_shape(self):
        shape = self.current_shape[self.current_rot]
        for (x, y) in shape:
            if 0 <= self.current_y + y < ROWS and 0 <= self.current_x + x < COLUMNS:
                self.grid[self.current_y + y][self.current_x + x] = 1

    def clear_lines(self):
        lines = 0
        for y in range(ROWS-1, -1, -1):
            if all(self.grid[y]):
                del self.grid[y]
                self.grid.insert(0, [0]*COLUMNS)
                lines += 1
        self.score += lines * 100

    def draw(self, canvas):
        # Draw grid
        for y in range(ROWS):
            for x in range(COLUMNS):
                if self.grid[y][x]:
                    canvas.rectangle(
                        (x*BLOCK_SIZE, y*BLOCK_SIZE,
                         x*BLOCK_SIZE + BLOCK_SIZE-1, y*BLOCK_SIZE + BLOCK_SIZE-1),
                        fill="white")
        
        # Draw current shape
        if not self.game_over:
            shape = self.current_shape[self.current_rot]
            for (x, y) in shape:
                draw_x = self.current_x + x
                draw_y = self.current_y + y
                if 0 <= draw_y < ROWS and 0 <= draw_x < COLUMNS:
                    canvas.rectangle(
                        (draw_x*BLOCK_SIZE, draw_y*BLOCK_SIZE,
                         draw_x*BLOCK_SIZE + BLOCK_SIZE-1, draw_y*BLOCK_SIZE + BLOCK_SIZE-1),
                        fill="white")
        
        # Draw score
        canvas.text((0, ROWS*BLOCK_SIZE + 2), f"Score: {self.score}", fill="white")
        if self.game_over:
            canvas.text((0, ROWS*BLOCK_SIZE + 12), "GAME OVER!", fill="white")

def main(stdscr):
    # Set up curses
    stdscr.nodelay(True)
    curses.curs_set(0)
    stdscr.timeout(100)
    
    tetris = Tetris()
    last_drop = time.time()
    auto_drop = 0.5

    while not tetris.game_over:
        # Handle input
        key = stdscr.getch()
        if key == curses.KEY_LEFT:
            tetris.move(-1)
        elif key == curses.KEY_RIGHT:
            tetris.move(1)
        elif key == curses.KEY_DOWN:
            tetris.drop()
        elif key == curses.KEY_UP:
            tetris.rotate()
        elif key == ord(' '):
            while tetris.drop():
                pass
        elif key == ord('q'):
            break

        # Auto-drop and drawing (keep previous implementation)
        if time.time() - last_drop > auto_drop:
            tetris.drop()
            last_drop = time.time()

        with canvas(device) as draw:
            tetris.draw(draw)

        time.sleep(0.01)

    # Game over handling (keep previous implementation)

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
