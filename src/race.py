# race.py

import pyxel
import random
from car import Car
from track import (
    TRACK_POINTS, START_FINISH_INDEX_SMOOTHED, PIT_LANE_POINTS,
    TOTAL_TRACK_LENGTH, PIT_LANE_TOTAL_LENGTH, PITLANE_ENTRANCE_DISTANCE,
    PITLANE_EXIT_DISTANCE
)
from constants import *
from announcements import Announcements
from load_teams import load_teams
class Race:
    def __init__(self, game, starting_grid):
        self.starting_grid = starting_grid
        self.game = game
        self.pyuni = self.game.pyuni
        self.frame_count = 0
        self.countdown = 90
        self.race_started = False
        self.race_finished = False
        self.leaderboard_scroll_index = 0
        self.announcements = Announcements(self.pyuni)
        self.cars = []
        self.state = 'warmup_lap' if ENABLE_WARMUP_LAP else 'countdown'
        self.init_race()


    def init_race(self):
        pyxel.colors[0] = 0xFFFFFFFF
        teams_data = load_teams()

        # Set pyxel colors based on team data
        for i, team in enumerate(teams_data, start=2):
            pyxel.colors[i] = int(team["color"], 16)  # Convert hex to integer


        grid_positions = list(range(20))
        random.shuffle(grid_positions)

        # Initialize cars using team data
        for i, team in enumerate(teams_data):
            for driver in team["drivers"]:
                car_number = driver["name"]
                color_index = i + 2
                grid_position = self.starting_grid.index(car_number) if car_number in self.starting_grid else len(
                    self.cars)
                car = Car(color_index, car_number, grid_position, self.announcements, mode='race')
                car.game = self.game
                self.cars.append(car)

        # Sort cars by grid position for the race
        self.cars.sort(key=lambda car: car.grid_position)
        for idx, car in enumerate(self.cars):
            start_delay_frames = idx * 30
            car.start_delay_frames = start_delay_frames
        if ENABLE_WARMUP_LAP:
            self.announcements.add_message("Warm-up lap has started.",
                                           duration=90)
        else:
            self.announcements.add_message("Race starting soon...",
                                           duration=90)
        self.safety_car_active = False
        self.safety_car_lap_counter = 0
        self.safety_car_triggered = False
        self.safety_car = None
        self.safety_car_laps_started = False
        self.safety_car_ending_announced = False

    def create_safety_car(self):
        safety_car_color_index = SAFETY_CAR_COLOR_INDEX
        self.safety_car = Car(
            color_index=safety_car_color_index,
            car_number=0,
            grid_position=0,
            announcements=self.announcements
        )
        self.safety_car.is_safety_car = True
        self.safety_car.speed = SAFETY_CAR_SPEED
        self.safety_car.distance = PITLANE_EXIT_DISTANCE

    def update(self):
        self.frame_count += 1
        if self.state == 'warmup_lap':
            self.update_warmup_lap()
        elif self.state == 'countdown':
            self.update_countdown()
        elif self.state == 'race':
            self.update_race_logic()
        self.announcements.update()

    def update_warmup_lap(self):
        all_cars_ready = True
        for car in self.cars:
            car.update_warmup(self.frame_count)
            if not car.warmup_completed:
                all_cars_ready = False
        if all_cars_ready:
            self.state = 'countdown'
            self.countdown = 90
            self.announcements.add_message("All cars are on the grid.",
                                           duration=60)
            self.announcements.add_message("Race starting soon...",
                                           duration=60)

    def update_countdown(self):
        self.race_started = True
        self.state = 'race'
        print(self.cars[0])
        leader_distance = self.cars[0].distance
        average_speed = sum(car.base_max_speed for car in self.cars) / \
                        len(self.cars)
        for car in self.cars:
            distance_diff = (leader_distance - car.distance) % \
                            TOTAL_TRACK_LENGTH
            car.initial_time_offset = distance_diff / average_speed
        self.announcements.add_message("Go!", duration=60)

    def update_race_logic(self):
        if self.race_started and not self.race_finished:
            if not self.safety_car_active and not self.safety_car_triggered:
                for car in self.cars:
                    if car.crashed:
                        if random.random() < SAFETY_CAR_DEPLOY_CHANCE:
                            # Sort cars before safety car deployment
                            self.cars.sort(
                                key=lambda car: (-car.laps_completed, -car.adjusted_distance)
                            )
                            self.safety_car_active = True
                            self.safety_car_triggered = True
                            self.announcements.add_message(
                                "Safety Car Deployed!", duration=90)
                            self.create_safety_car()
                            break
                if pyxel.btnp(pyxel.KEY_P):
                    # Sort cars before safety car deployment
                    self.cars.sort(
                        key=lambda car: (-car.laps_completed, -car.adjusted_distance)
                    )
                    self.safety_car_active = True
                    self.safety_car_triggered = True
                    self.announcements.add_message("Safety Car Deployed!",
                                                   duration=90)
                    self.create_safety_car()
            if self.safety_car_active:
                self.update_safety_car()
                # Do not sort cars during safety car period to maintain positions
            else:

                # Regular sorting during race
                self.cars.sort(
                    key=lambda car: (-car.laps_completed, -car.adjusted_distance)
                )
                for car in self.cars:
                    car.update(self.race_started, self.frame_count,
                               self.cars, self.safety_car_active)
                max_scroll_index = max(0, len(self.cars) - 3)
                if pyxel.btnp(pyxel.KEY_UP):
                    self.leaderboard_scroll_index = max(
                        self.leaderboard_scroll_index - 1, 0
                    )
                elif pyxel.btnp(pyxel.KEY_DOWN):
                    self.leaderboard_scroll_index = min(
                        self.leaderboard_scroll_index + 1, max_scroll_index
                    )
            if self.safety_car and not self.safety_car.is_active:
                self.safety_car = None
                self.safety_car_active = False
                self.safety_car_laps_started = False
                self.safety_car_triggered = False
                self.safety_car_ending_announced = False
                self.handle_crashed_cars()
                for car in self.cars:
                    car.reset_after_safety_car()
            if any(car.laps_completed >= MAX_LAPS for car in self.cars):
                self.race_finished = True
                self.announcements.add_message("Race finished!",
                                               duration=180)

    def update_safety_car(self):
        if self.safety_car:
            self.safety_car.update(self.race_started, self.frame_count,
                                   self.cars, self.safety_car_active)
        for idx, car in enumerate(self.cars):
            if not car.is_active:
                continue
            if idx == 0:
                car_ahead = self.safety_car
            else:
                car_ahead = self.cars[idx - 1]
            car.update_under_safety_car(self.frame_count, self.safety_car,
                                        car_ahead)
        # Do not sort cars during safety car period to maintain positions
        max_scroll_index = max(0, len(self.cars) - 3)
        if pyxel.btnp(pyxel.KEY_UP):
            self.leaderboard_scroll_index = max(
                self.leaderboard_scroll_index - 1, 0
            )
        elif pyxel.btnp(pyxel.KEY_DOWN):
            self.leaderboard_scroll_index = min(
                self.leaderboard_scroll_index + 1, max_scroll_index
            )
      #  all_cars_caught_up = all(car.has_caught_safety_car or not car.is_active
                               #  for car in self.cars)
        all_cars_caught_up = all(car.speed == SAFETY_CAR_SPEED for car in self.cars)
        if all_cars_caught_up and not self.safety_car_laps_started:
            self.safety_car_laps_started = True
            self.safety_car_start_lap = self.cars[0].laps_completed
        if self.safety_car_laps_started:
            leader_car = self.cars[0]
            laps_under_safety_car = leader_car.laps_completed - \
                                    self.safety_car_start_lap
            print(laps_under_safety_car)
            if laps_under_safety_car >= SAFETY_CAR_DURATION_LAPS:
                if not self.safety_car_ending_announced:
                    self.end_safety_car_period()
                    self.safety_car_ending_announced = True

    def end_safety_car_period(self):
        self.announcements.add_message("Safety Car Ending! Prepare for "
                                       "Restart.", duration=90)
        if self.safety_car:
            self.safety_car.is_exiting = True
        for car in self.cars:
            car.is_safety_car_ending = True

    def handle_crashed_cars(self):
        for car in self.cars:
            if car.crashed:
                car.is_active = False

    def draw(self):
        pyxel.cls(1)
        self.pyuni.text(370, 480, CURRENT_VER, 0)
        for i in range(len(TRACK_POINTS) - 1):
            x1, y1 = TRACK_POINTS[i]
            x2, y2 = TRACK_POINTS[i + 1]
            pyxel.line(x1, y1, x2, y2, 0)
        sx, sy = TRACK_POINTS[START_FINISH_INDEX_SMOOTHED]
        sx_next, sy_next = TRACK_POINTS[(START_FINISH_INDEX_SMOOTHED + 1)]
        pyxel.line(sx, sy, sx_next, sy_next, 2)
        if PIT_LANE_POINTS:
            for i in range(len(PIT_LANE_POINTS) - 1):
                x1, y1 = PIT_LANE_POINTS[i]
                x2, y2 = PIT_LANE_POINTS[i + 1]
                pyxel.line(x1, y1, x2, y2, 13)
        for car in self.cars:
            car.draw()
        if self.safety_car and self.safety_car.is_active:
            self.safety_car.draw()
        if self.state == 'race':
            self.draw_leaderboard()
            if self.race_finished:
                self.pyuni.text(200, 300, "Race Finished!", 0)
            leader_lap = self.cars[0].laps_completed + 1
            self.pyuni.text(20, 5, f"Lap: {leader_lap}/{MAX_LAPS}", 0)
        elif self.state == 'warmup_lap':
            self.pyuni.text(20, 5, "Warm-up Lap", 0)
        else:
            self.pyuni.text(20, 5, "Lap: 1/{}".format(MAX_LAPS), 0)
        if self.safety_car_active:
            self.pyuni.text(20, 20, "Safety Car Deployed", 8)
        self.announcements.draw()

    def draw_leaderboard(self):
        x_offset = 20
        y_offset = 20
        self.pyuni.text(x_offset, y_offset, "Leaderboard:", 0)
        racing_cars = [car for car in self.cars if not car.is_safety_car
                       and car.is_active]
        for idx, car in enumerate(
            racing_cars[self.leaderboard_scroll_index:
                        self.leaderboard_scroll_index + 3]
        ):
            global_idx = self.leaderboard_scroll_index + idx
            gap_text = "Leader" if global_idx == 0 else \
                       self.get_gap_text(global_idx, racing_cars)
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
            tire_text = f"T:{car.tire_type.capitalize()} "\
                        f"{car.tire_percentage:.1f}%"
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

    def get_gap_text(self, global_idx, racing_cars):
        car = racing_cars[global_idx]
        car_ahead = racing_cars[global_idx - 1]
        if self.race_started:
            distance_gap = (
                car_ahead.adjusted_total_distance -
                car.adjusted_total_distance
            )
            if distance_gap < 0:
                distance_gap += TOTAL_TRACK_LENGTH * MAX_LAPS
            min_speed = 0.1
            effective_speed = max(car.speed, min_speed)
            gap = (distance_gap / effective_speed) / 20
            return f"+{gap:.2f}s"
        else:
            gap = (car.initial_time_offset -
                   car_ahead.initial_time_offset) / 5
            return f"+{gap:.1f}s"
