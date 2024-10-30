import pyxel
from car import Car
from track import TRACK_POINTS, START_FINISH_INDEX_SMOOTHED, PIT_LANE_POINTS
from constants import *
from pyxelunicode import PyxelUnicode
import random
from announcements import Announcements  # Import the announcements module

class Game:
    def __init__(self):
        pyxel.init(500, 500)
        # Initialize the game state to 'main_menu'
        self.state = 'main_menu'
        # Initialize PyxelUnicode for font rendering
        font_path = r"../fonts/PublicPixel.ttf"  # Replace with the path to your font file
        font_size = 8
        self.pyuni = PyxelUnicode(font_path, font_size)
        self.leaderboard_scroll_index = 0  # Initialize scroll index for the leaderboard
        self.frame_count = 0  # Frame counter for timing
        self.announcements = Announcements(self.pyuni)  # Initialize the announcements
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

        # Assign color for pitlane
        pyxel.colors[13] = 0x00FFFF  # Color for pitlane lines

        # Randomize grid positions for 20 cars
        grid_positions = list(range(20))
        random.shuffle(grid_positions)

        # Create 20 cars, with pairs of cars (two per team) sharing the same color index
        self.cars = []
        for i in range(20):
            # Calculate team color index (integer division by 2 to ensure pairs have the same color)
            team_color_index = (i // 2) + 1  # +1 because Pyxel color indexes start from 1
            car_number = i + 1
            grid_position = grid_positions[i]

            # Instantiate a car with the assigned team color index
            car = Car(color_index=team_color_index, car_number=car_number, grid_position=grid_position, announcements=self.announcements)
            self.cars.append(car)

        self.state = 'race'
        self.leaderboard_scroll_index = 0  # Reset scroll index
        self.frame_count = 0  # Reset frame count

    def update_race(self):
        # Countdown logic
        if self.countdown > 0:
            self.countdown -= 1
        else:
            self.race_started = True  # Start the race once countdown finishes

        if self.race_started and not self.race_finished:
            self.frame_count += 1  # Increment frame count

            for car in self.cars:
                car.update(self.race_started, self.frame_count)

            # Sort cars for the leaderboard using get_current_time()
            self.cars.sort(key=lambda car: -car.get_current_time())

            # Handle leaderboard scrolling
            max_scroll_index = max(0, len(self.cars) - 3)

            if pyxel.btnp(pyxel.KEY_UP):
                self.leaderboard_scroll_index = max(self.leaderboard_scroll_index - 1, 0)
            elif pyxel.btnp(pyxel.KEY_DOWN):
                self.leaderboard_scroll_index = min(self.leaderboard_scroll_index + 1, max_scroll_index)

            # Update announcements
            self.announcements.update()

            # Check if the race is finished
            if any(car.laps_completed >= MAX_LAPS for car in self.cars):
                self.race_finished = True

    def draw_race(self):
        pyxel.cls(11)
        self.pyuni.text(370, 480, CURRENT_VER, 0)
        # Draw track segments in pure white
        for i in range(len(TRACK_POINTS)-1):
            x1, y1 = TRACK_POINTS[i]
            x2, y2 = TRACK_POINTS[i + 1]
            pyxel.line(x1, y1, x2, y2, 0)  # Using color index 0 for pure white

        # Draw start-finish line
        sx, sy = TRACK_POINTS[START_FINISH_INDEX_SMOOTHED]
        sx_next, sy_next = TRACK_POINTS[(START_FINISH_INDEX_SMOOTHED + 1)]
        pyxel.line(sx, sy, sx_next, sy_next, 2)

        # Draw pitlane segments
        if PIT_LANE_POINTS:
            for i in range(len(PIT_LANE_POINTS)-1):
                x1, y1 = PIT_LANE_POINTS[i]
                x2, y2 = PIT_LANE_POINTS[i + 1]
                pyxel.line(x1, y1, x2, y2, 13)  # Using color index 13 for pitlane

        # Draw cars
        for car in self.cars:
            car.draw()

        x_offset = 20
        y_offset = 20
        self.pyuni.text(x_offset, y_offset, "Leaderboard:", 0)  # Using color index 0 for pure white

        # Display the leaderboard with scrolling
        for idx, car in enumerate(self.cars[self.leaderboard_scroll_index:self.leaderboard_scroll_index + 3]):
            global_idx = self.leaderboard_scroll_index + idx
            gap = 0.0 if global_idx == 0 else \
                (self.cars[global_idx - 1].get_current_time() - car.get_current_time()) * 10
            gap_text = f"-{gap:.2f}s" if global_idx != 0 else "Leader"
            lap_text = f"Lap: {car.laps_completed + 1}/{MAX_LAPS}"
            best_lap_text = f"Best Lap: {car.best_lap_time:.2f}s" if car.best_lap_time else "Best Lap: N/A"
            stats_text = f"Speed: {car.speed:.2f}"
            car_stats = f"E:{car.engine_power:.2f} A:{car.aero_efficiency:.2f} G:{car.gearbox_quality:.2f}"
            tire_text = f"T:{car.tire_type.capitalize()} {car.tire_percentage:.1f}%"

            self.pyuni.text(x_offset, y_offset + (idx * 40) + 10, f"{global_idx + 1}. Car {car.car_number} {gap_text}", car.color)
            self.pyuni.text(x_offset, y_offset + (idx * 40) + 20, f"{lap_text} | {best_lap_text}", car.color)
            self.pyuni.text(x_offset, y_offset + (idx * 40) + 30, f"{stats_text}", car.color)
            self.pyuni.text(x_offset, y_offset + (idx * 40) + 40, f"{car_stats} | {tire_text}", car.color)

        if self.race_finished:
            self.pyuni.text(200, 300, "Race Finished!", 0)

        # Display laps to go
        leader_lap = self.cars[0].laps_completed + 1  # laps_completed starts from 0
        self.pyuni.text(20, 5, f"Lap: {leader_lap}/{MAX_LAPS}", 0)

        # Display announcements
        self.announcements.draw()

        # Countdown display
        if self.countdown > 0:
            countdown_text = str((self.countdown // 60) + 0)  # Display countdown in seconds
            self.pyuni.text(250, 300, countdown_text, 0)
