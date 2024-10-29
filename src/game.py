# game.py
import pyxel
from car import Car
from track import TRACK_POINTS, START_FINISH_INDEX
from constants import *
from utilities import braking_curve
from pyxelunicode import PyxelUnicode
import random

class Game:
    def __init__(self):
        pyxel.init(500, 500)
        # Initialize the game state to 'main_menu'
        self.state = 'main_menu'
        # Initialize PyxelUnicode for font rendering
        font_path = r"../fonts/PublicPixel.ttf"  # Replace with the path to your font file
        font_size = 8
        self.pyuni = PyxelUnicode(font_path, font_size)
        pyxel.run(self.update, self.draw)

    def update(self):
        if self.state == 'main_menu':
            self.update_main_menu()
        elif self.state == 'race':
            self.update_race()

    def draw(self):
        if self.state == 'main_menu':
            self.draw_main_menu()
        elif self.state == 'race':
            self.draw_race()

    def update_main_menu(self):
        # Handle input, check if 'W' is pressed to start race
        if pyxel.btnp(pyxel.KEY_W):
            self.start_race()

    def draw_main_menu(self):
        # Clear the screen
        pyxel.cls(0)
        self.pyuni.text(370, 480, CURRENT_VER, 7)

        menu_text = "Press W to start the race"
        text_x = pyxel.width // 2 - len(menu_text) * (8) // 2
        text_y = pyxel.height // 2 - 8 // 2
        self.pyuni.text(text_x, text_y, menu_text, 7)  # Using color index 7 for white

    def start_race(self):
        # Initialize race-related variables
        self.countdown = 180  # 180 frames = 3 seconds at 60 FPS
        self.race_started = False
        self.race_finished = False

        # Define colors in the palette
        pyxel.colors[0] = 0xFFFFFFFF  # Pure white for track and text

        # Define a list of hex colors for the cars
        team_colors = [
            0xFF0000, 0x00FF00, 0x0000FF, 0xFFFF00,
            0xFF00FF, 0x00FFFF, 0x800000, 0x008000, 0x000080, 0x808000, 0x000000
        ]

        # Randomize car grid positions
        for i, hex_color in enumerate(team_colors, start=1):
            pyxel.colors[i] = hex_color

        # Randomize grid positions for 20 cars
        grid_positions = list(range(100))
        random.shuffle(grid_positions)

        # Create 20 cars, with pairs of cars (two per team) sharing the same color index
        self.cars = []
        for i in range(100):
            # Calculate team color index (integer division by 2 to ensure pairs have the same color)
            team_color_index = (i // 10) + 1  # +1 because Pyxel color indexes start from 1
            car_number = i + 1
            grid_position = grid_positions[i]
            
            # Instantiate a car with the assigned team color index
            car = Car(color_index=team_color_index, car_number=car_number, grid_position=grid_position)
            self.cars.append(car)

        self.state = 'race'

    def update_race(self):
        # Countdown logic
        if self.countdown > 0:
            self.countdown -= 1
        else:
            self.race_started = True  # Start the race once countdown finishes

        if self.race_started and not self.race_finished:
            for car in self.cars:
                car.update(self.race_started)

            # Sort cars for the leaderboard using get_current_time()
            self.cars.sort(key=lambda car: -car.get_current_time())

            # Check if the race is finished
            if any(car.laps_completed >= MAX_LAPS for car in self.cars):
                self.race_finished = True

    def draw_race(self):
        pyxel.cls(11)
        self.pyuni.text(370, 480, CURRENT_VER, 0)
        # Draw track segments in pure white
        for i in range(len(TRACK_POINTS)):
            x1, y1 = TRACK_POINTS[i]
            x2, y2 = TRACK_POINTS[(i + 1) % len(TRACK_POINTS)]
            pyxel.line(x1, y1, x2, y2, 0)  # Using color index 0 for pure white

        sx, sy = TRACK_POINTS[START_FINISH_INDEX]
        sx_next, sy_next = TRACK_POINTS[(START_FINISH_INDEX + 1) % len(TRACK_POINTS)]
        pyxel.line(sx, sy, sx_next, sy_next, 2)

        # Draw cars
        for car in self.cars:
            car.draw()

        x_offset = 20
        y_offset = 20
        self.pyuni.text(x_offset, y_offset, "Leaderboard:", 0)  # Using color index 0 for pure white

        for idx, car in enumerate(self.cars[:3]):
            gap = 0.0 if idx == 0 else (self.cars[idx - 1].get_current_time() - car.get_current_time()) * 10
            tire_text = f"{idx+1}.{car.car_number} -{gap:.2f}s"
            stats_text = f"T: {car.tire_type.capitalize()} {car.tire_percentage:.1f}% | "
            stats_text += f"E: {car.engine_power:.2f} | A: {car.aero_efficiency:.2f} | "
            stats_text += f"S: {car.suspension_quality:.2f} | B: {car.brake_performance:.2f}"
            self.pyuni.text(x_offset, y_offset + (self.pyuni.font_height + 5) * (2 * idx + 1), tire_text, car.color)
            self.pyuni.text(x_offset, y_offset + (self.pyuni.font_height + 5) * (2 * idx + 2), stats_text, car.color)

        if self.race_finished:
            self.pyuni.text(200, 300, "Race Finished!", 0)

        # Countdown display
        if self.countdown > 0:
            countdown_text = str((self.countdown // 60) + 0)  # Display countdown in seconds
            self.pyuni.text(250, 300, countdown_text, 0)
