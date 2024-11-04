# race.py

import pyxel
import random
from car import Car
from track import (
    TRACK_POINTS, START_FINISH_INDEX_SMOOTHED, PIT_LANE_POINTS, TOTAL_TRACK_LENGTH
)
from constants import *
from announcements import Announcements

class Race:
    def __init__(self, game):
        self.game = game
        self.pyuni = self.game.pyuni
        self.frame_count = 0
        self.countdown = 90  # 3 seconds at 30 FPS
        self.race_started = False
        self.race_finished = False
        self.leaderboard_scroll_index = 0
        self.announcements = Announcements(self.pyuni)
        self.cars = []
        self.init_race()

    def init_race(self):
        # Initialize race-related variables and cars
        pyxel.colors[0] = 0xFFFFFFFF  # White for track and text
        team_colors = [
            0xFF0000, 0x00FF00, 0x0000FF, 0xFFFF00,
            0xFF00FF, 0x00FFFF, 0x800000, 0x008000,
            0x000080, 0x808000, 0x000000
        ]
        for i, hex_color in enumerate(team_colors, start=1):
            pyxel.colors[i] = hex_color
        pyxel.colors[13] = 0x00FFFF  # Color for pitlane lines

        grid_positions = list(range(20))
        random.shuffle(grid_positions)

        for i in range(20):
            team_color_index = (i // 2) + 1
            car_number = i + 1
            grid_position = grid_positions[i]
            car = Car(
                color_index=team_color_index,
                car_number=car_number,
                grid_position=grid_position,
                announcements=self.announcements
            )
            self.cars.append(car)

        self.cars.sort(key=lambda car: car.distance, reverse=True)
        leader_distance = self.cars[0].distance
        average_speed = sum(car.base_max_speed for car in self.cars) / len(self.cars)

        for car in self.cars:
            distance_diff = (leader_distance - car.distance) % TOTAL_TRACK_LENGTH
            car.initial_time_offset = distance_diff / average_speed

    def update(self):
        self.frame_count += 1
        if self.countdown > 0:
            self.countdown -= 1
        else:
            self.race_started = True

        if self.race_started and not self.race_finished:
            for car in self.cars:
                car.update(self.race_started, self.frame_count)
            self.cars.sort(
                key=lambda car: (-car.laps_completed, -car.adjusted_distance)
            )
            max_scroll_index = max(0, len(self.cars) - 3)
            if pyxel.btnp(pyxel.KEY_UP):
                self.leaderboard_scroll_index = max(
                    self.leaderboard_scroll_index - 1, 0
                )
            elif pyxel.btnp(pyxel.KEY_DOWN):
                self.leaderboard_scroll_index = min(
                    self.leaderboard_scroll_index + 1, max_scroll_index
                )
            self.announcements.update()
            if any(car.laps_completed >= MAX_LAPS for car in self.cars):
                self.race_finished = True
        else:
            self.cars.sort(key=lambda car: car.distance, reverse=True)

    def draw(self):
        pyxel.cls(11)
        self.pyuni.text(370, 480, CURRENT_VER, 0)
        # Draw the track
        for i in range(len(TRACK_POINTS) - 1):
            x1, y1 = TRACK_POINTS[i]
            x2, y2 = TRACK_POINTS[i + 1]
            pyxel.line(x1, y1, x2, y2, 0)
        # Draw start-finish line
        sx, sy = TRACK_POINTS[START_FINISH_INDEX_SMOOTHED]
        sx_next, sy_next = TRACK_POINTS[(START_FINISH_INDEX_SMOOTHED + 1)]
        pyxel.line(sx, sy, sx_next, sy_next, 2)
        # Draw pitlane
        if PIT_LANE_POINTS:
            for i in range(len(PIT_LANE_POINTS) - 1):
                x1, y1 = PIT_LANE_POINTS[i]
                x2, y2 = PIT_LANE_POINTS[i + 1]
                pyxel.line(x1, y1, x2, y2, 13)
        # Draw cars
        for car in self.cars:
            car.draw()
        # Draw leaderboard and other race information
        self.draw_leaderboard()
        if self.race_finished:
            self.pyuni.text(200, 300, "Race Finished!", 0)
        # Draw announcements and countdown
        self.announcements.draw()
        if self.countdown > 0:
            countdown_text = str((self.countdown // 30) + 0)
            self.pyuni.text(250, 300, countdown_text, 0)

    def draw_leaderboard(self):
        x_offset = 20
        y_offset = 20
        self.pyuni.text(x_offset, y_offset, "Leaderboard:", 0)
        for idx, car in enumerate(
            self.cars[self.leaderboard_scroll_index : self.leaderboard_scroll_index + 3]
        ):
            global_idx = self.leaderboard_scroll_index + idx
            gap_text = "Leader" if global_idx == 0 else self.get_gap_text(global_idx)
            lap_text = f"Lap: {car.laps_completed + 1}/{MAX_LAPS}"
            best_lap_text = (
                f"Best Lap: {car.best_lap_time:.2f}s"
                if car.best_lap_time
                else "Best Lap: N/A"
            )
            stats_text = f"Speed: {car.speed:.2f}"
            car_stats = (
                f"E:{car.engine_power:.2f} A:{car.aero_efficiency:.2f} "
                f"G:{car.gearbox_quality:.2f}"
            )
            tire_text = f"T:{car.tire_type.capitalize()} {car.tire_percentage:.1f}%"
            self.pyuni.text(
                x_offset,
                y_offset + (idx * 50) + 10,
                f"{global_idx + 1}. Car {car.car_number} {gap_text}",
                car.color,
            )
            self.pyuni.text(
                x_offset,
                y_offset + (idx * 50) + 20,
                f"{lap_text} | {best_lap_text}",
                car.color,
            )
            self.pyuni.text(
                x_offset,
                y_offset + (idx * 50) + 30,
                f"{stats_text}",
                car.color,
            )
            self.pyuni.text(
                x_offset,
                y_offset + (idx * 50) + 40,
                f"{car_stats} | {tire_text}",
                car.color,
            )
            for n in range(16):
                pyxel.rect(6 * n, 20, 6, 6, n)
        leader_lap = self.cars[0].laps_completed + 1
        self.pyuni.text(20, 5, f"Lap: {leader_lap}/{MAX_LAPS}", 0)

    def get_gap_text(self, global_idx):
        car = self.cars[global_idx]
        car_ahead = self.cars[global_idx - 1]
        if self.race_started:
            distance_gap = (
                car_ahead.adjusted_total_distance - car.adjusted_total_distance
            )
            if distance_gap < 0:
                distance_gap += TOTAL_TRACK_LENGTH
            min_speed = 0.1
            effective_speed = max(car.speed, min_speed)
            gap = (distance_gap / effective_speed) / 20
            return f"+{gap:.2f}s"
        else:
            gap = (car.initial_time_offset - car_ahead.initial_time_offset) / 5
            return f"+{gap:.1f}s"
