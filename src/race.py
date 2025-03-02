# race.py

import pyxel
import random
from car import Car
from track import (
    TRACK_POINTS, START_FINISH_INDEX_SMOOTHED, PIT_LANE_POINTS,
    TOTAL_TRACK_LENGTH, PIT_LANE_TOTAL_LENGTH, PITLANE_ENTRANCE_DISTANCE,
    PITLANE_EXIT_DISTANCE, get_position_along_track, PIT_STOP_POINT, PIT_LANE_CUMULATIVE_DISTANCES, CUMULATIVE_DISTANCES
)
from constants import *
from announcements import Announcements
from load_teams import load_teams
import json

class Race:
    def __init__(self, game, starting_grid):
        self.starting_grid = starting_grid
        self.game = game
        self.pyuni = self.game.pyuni
        self.frame_count = 0
        self.countdown = 90
        self.race_started = False
        self.race_finished = False
        self.safety_car_active = False
        self.safety_car_lap_counter = 0
        self.safety_car_triggered = False
        self.safety_car = None
        self.safety_car_laps_started = False
        self.safety_car_ending_announced = False
        self.leaderboard_scroll_index = 0
        self.announcements = Announcements(self.pyuni)
        self.cars = []
        self.state = 'warmup_lap' if ENABLE_WARMUP_LAP else 'countdown'
        self.drivers_map = self.load_drivers()  # Load drivers data
        self.teams_data = load_teams()  # Load teams data

        self.assign_team_pitboxes()

        self.create_cars()

    def load_drivers(self):
        """Load driver data from JSON file and create a mapping from driver_id to driver data."""
        try:
            with open("../database/drivers/drivers.json", "r") as f:
                drivers = json.load(f)
            drivers_map = {driver["id"]: driver for driver in drivers}
            return drivers_map
        except FileNotFoundError:
            print("Error: drivers.json file not found.")
            return {}
        except json.JSONDecodeError as e:
            print(f"Error decoding drivers.json: {e}")
            return {}

    def create_cars(self):
        """Create Car objects based on teams and their drivers."""
        # Assign unique color indexes starting from 2 to avoid overriding existing Pyxel colors
        for i, team in enumerate(self.teams_data, start=2):
            try:
                # Set Pyxel colors based on team data
                color_value = int(team["color"], 16)
            except ValueError:
                print(f"Invalid color format for team {team['team_name']}. Using default color 0xFFFFFF.")
                pyxel.colors[i] = 0xFFFFFF  # Default to white if color parsing fails

            pyxel.colors[i] = color_value
            # Also store the palette index for the team.
            team["color_index"] = i

        # Initialize cars using team data
        for team_index, team in enumerate(self.teams_data):
            for driver in team["drivers"]:
                driver_id = driver["driver_id"]
                driver_data = self.drivers_map.get(driver_id, None)
                if driver_data:
                    driver_name = driver_data["name"]
                    driver_number = driver_data["number"]
                    color_index = team_index + 2  # Ensure unique color index per team
                    grid_position = self.starting_grid.index(
                        driver_number) if driver_number in self.starting_grid else len(self.cars)
                    pit_dist = team["pitbox_distance"]

                    car = Car(
                        color_index=color_index,
                        car_number=driver_number,
                        driver_name=driver_name,  # Pass driver_name correctly
                        grid_position=grid_position,
                        announcements=self.announcements,
                        game=self.game,
                        mode='race',
                        pitbox_coords=team.get("pitbox_coords"),
                        pitbox_distance=pit_dist
                    )
                    car.qualifying_exit_delay = random.randint(0, 60 * 30 * 3)
                    self.cars.append(car)
                else:
                    print(f"Warning: Driver ID {driver_id} not found in drivers.json")

        # Sort cars by grid position for the race
        self.cars.sort(key=lambda car: car.grid_position)
        for idx, car in enumerate(self.cars):
            start_delay_frames = idx * 30
            car.start_delay_frames = start_delay_frames

        # Add initial announcements
        if ENABLE_WARMUP_LAP:
            self.announcements.add_message("Warm-up lap has started.", duration=90)
        else:
            self.announcements.add_message("Race starting soon.", duration=90)

        # Initialize safety car variables


    def assign_team_pitboxes(self):
        """
        Sort teams alphabetically by team name and assign each team a unique pitbox location
        along the pitlane. The pitbox coordinates are stored in the team data.
        """
        # Sort teams alphabetically
        sorted_teams = sorted(self.teams_data, key=lambda t: t["team_name"])
        self.teams_data = sorted_teams  # Overwrite teams_data so subsequent loops are in alphabetical order
        num_teams = len(self.teams_data)

        # For each team, evenly space its pitbox along the pitlane.
        for i, team in enumerate(self.teams_data):
            # Calculate a distance along the pitlane for the pitbox.
            pit_distance = PIT_LANE_TOTAL_LENGTH * (i + 1) / (num_teams + 1)
            # Convert that distance to (x, y) coordinates on the pitlane.
            pit_x, pit_y = get_position_along_track(
                pit_distance, PIT_LANE_POINTS, PIT_LANE_CUMULATIVE_DISTANCES
            )
            # Store the pitbox info with the team.
            team["pitbox_distance"] = pit_distance
            team["pitbox_coords"] = (pit_x, pit_y)

    def create_safety_car(self):
        """Create and initialize the safety car."""
        safety_car_color_index = SAFETY_CAR_COLOR_INDEX
        self.safety_car = Car(
            color_index=safety_car_color_index,
            car_number=0,  # Assuming 0 represents the safety car
            driver_name="Safety Car",
            grid_position=0,
            announcements=self.announcements,
            game=self.game,
            mode='race',
            pitbox_coords=PIT_STOP_POINT,
            pitbox_distance=PITLANE_EXIT_DISTANCE
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
        """Update logic for the warm-up lap."""
        all_cars_ready = True
        for car in self.cars:
            car.update_warmup(self.frame_count)
            if not car.warmup_completed:
                all_cars_ready = False
        if all_cars_ready:
            self.state = 'countdown'
            self.countdown = 90
            self.announcements.add_message("All cars are on the grid.", duration=60)
            self.announcements.add_message("Race starting soon.", duration=60)

    def update_countdown(self):
        """Update logic for the countdown before the race starts."""
        self.race_started = True
        self.state = 'race'
        print(self.cars[0])
        leader_distance = self.cars[0].distance
        average_speed = sum(car.base_max_speed for car in self.cars) / len(self.cars)
        for car in self.cars:
            distance_diff = (leader_distance - car.distance) % TOTAL_TRACK_LENGTH
            car.initial_time_offset = distance_diff / average_speed
        self.announcements.add_message("Go!", duration=60)

    def update_race_logic(self):
        """Update the main race logic."""
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
                    self.announcements.add_message("Safety Car Deployed!", duration=90)
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
                    car.update(self.race_started, self.frame_count, self.cars, self.safety_car_active)
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
                self.announcements.add_message("Race finished!", duration=180)

    def update_safety_car(self):
        """Update the safety car and the cars under its effect."""
        self.cars.sort(
            key=lambda c: (-c.laps_completed, -c.adjusted_distance)
        )
        if self.safety_car:
            self.safety_car.update(self.race_started, self.frame_count, self.cars, self.safety_car_active)
        for idx, car in enumerate(self.cars):
            if not car.is_active:
                continue
            if idx == 0:
                car_ahead = self.safety_car
            else:
                car_ahead = self.cars[idx - 1]
            car.update_under_safety_car(self.frame_count, self.safety_car, self.cars, car_ahead)
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

        all_cars_caught_up = all(car.speed == SAFETY_CAR_SPEED for car in self.cars if car.is_active)
        if all_cars_caught_up and not self.safety_car_laps_started:
            self.safety_car_laps_started = True
            self.safety_car_start_lap = self.cars[0].laps_completed
        if self.safety_car_laps_started:
            leader_car = self.cars[0]
            laps_under_safety_car = leader_car.laps_completed - self.safety_car_start_lap
            print(laps_under_safety_car)
            if laps_under_safety_car >= SAFETY_CAR_DURATION_LAPS:
                if not self.safety_car_ending_announced:
                    self.end_safety_car_period()
                    self.safety_car_ending_announced = True

    def end_safety_car_period(self):
        """Handle the end of the safety car period."""
        self.announcements.add_message("Safety Car Ending! Prepare for Restart.", duration=90)
        if self.safety_car:
            self.safety_car.is_exiting = True
        for car in self.cars:
            car.is_safety_car_ending = True

    def handle_crashed_cars(self):
        """Deactivate crashed cars."""
        for car in self.cars:
            if car.crashed:
                car.is_active = False

    def drawbox(self, x_box, y_box, width, height, radius, border_thickness):
        """Draws a rounded box with a white border and black inner box."""
        # Draw white border
        pyxel.rect(x_box + radius, y_box, width - 2 * radius, height, 1)  # White color (1)
        pyxel.rect(x_box, y_box + radius, width, height - 2 * radius, 1)  # White color (1)
        pyxel.rect(x_box + radius, y_box + height - radius, width - 2 * radius, radius, 1)  # White color (1)

        # Draw white rounded corners
        pyxel.circ(x_box + radius, y_box + radius, radius, 1)  # White color (1)
        pyxel.circ(x_box + width - radius - 1, y_box + radius, radius, 1)  # White color (1)
        pyxel.circ(x_box + radius, y_box + height - radius - 1, radius, 1)  # White color (1)
        pyxel.circ(x_box + width - radius - 1, y_box + height - radius - 1, radius, 1)  # White color (1)

        # Draw inner black box
        inner_x, inner_y = x_box + border_thickness, y_box + border_thickness
        inner_width, inner_height = width - 2 * border_thickness, height - 2 * border_thickness
        inner_radius = radius - border_thickness

        pyxel.rect(inner_x + inner_radius, inner_y, inner_width - 2 * inner_radius, inner_height, 0)  # Black color (0)
        pyxel.rect(inner_x, inner_y + inner_radius, inner_width, inner_height - 2 * inner_radius, 0)  # Black color (0)
        pyxel.rect(inner_x + inner_radius, inner_y + inner_height - inner_radius, inner_width - 2 * inner_radius,
                   inner_radius, 0)  # Black color (0)

        # Draw black rounded corners
        pyxel.circ(inner_x + inner_radius, inner_y + inner_radius, inner_radius, 0)  # Black color (0)
        pyxel.circ(inner_x + inner_width - inner_radius - 1, inner_y + inner_radius, inner_radius, 0)  # Black color (0)
        pyxel.circ(inner_x + inner_radius, inner_y + inner_height - inner_radius - 1, inner_radius, 0)  # Black color (0)
        pyxel.circ(inner_x + inner_width - inner_radius - 1, inner_y + inner_height - inner_radius - 1,
                   inner_radius, 0)  # Black color (0)

    def draw_pitboxes(self):
        """
        Draws a custom pitbox for each team at its assigned location.
        The pitbox is drawn as a filled square using the team's palette index
        (which refers to the proper color in Pyxel's palette) with the team name below.
        """
        pitbox_size = 10  # Adjust the size as needed
        for team in self.teams_data:
            pit_x, pit_y = team["pitbox_coords"]
            # Center the pitbox on the (x, y) coordinate.
            top_left_x = pit_x - pitbox_size // 2
            top_left_y = pit_y - pitbox_size // 2

            # Use the team's palette index for drawing.
            team_color = team.get("color_index", 1)
            pyxel.rect(top_left_x, top_left_y, pitbox_size//2, pitbox_size//2, team_color)
            pyxel.rectb(top_left_x, top_left_y, pitbox_size//2, pitbox_size//2, 1)

    def draw(self):
        """Render the race scene."""
        pyxel.cls(0)
        self.pyuni.text(370, 480, CURRENT_VER, 1)  # Display version

        # Draw the track
        for i in range(len(TRACK_POINTS) - 1):
            x1, y1 = TRACK_POINTS[i]
            x2, y2 = TRACK_POINTS[i + 1]
            pyxel.line(x1, y1, x2, y2, 1)  # Black color

        # Draw start/finish line
        sx, sy = TRACK_POINTS[START_FINISH_INDEX_SMOOTHED]
        sx_next, sy_next = TRACK_POINTS[(START_FINISH_INDEX_SMOOTHED + 1)]
        pyxel.line(sx, sy, sx_next, sy_next, 2)

        # Draw pit lane
        if PIT_LANE_POINTS:
            for i in range(len(PIT_LANE_POINTS) - 1):
                x1, y1 = PIT_LANE_POINTS[i]
                x2, y2 = PIT_LANE_POINTS[i + 1]
                pyxel.line(x1, y1, x2, y2, 13)
            pitstop_x, pitstop_y = get_position_along_track(
                PIT_STOP_POINT, PIT_LANE_POINTS, PIT_LANE_CUMULATIVE_DISTANCES
            )


        self.draw_pitboxes()

        # Draw all cars
        for car in self.cars:
            car.draw()
        if self.safety_car and self.safety_car.is_active:
            self.safety_car.draw()

        # Draw race-specific UI elements
        if self.state == 'race':
            self.draw_leaderboard()
            if self.race_finished:
                self.pyuni.text(200, 300, "Race Finished!", 0)
            leader_lap = self.cars[0].laps_completed + 1
            self.pyuni.text(20, 5, f"Lap: {leader_lap}/{MAX_LAPS}", 0)
        elif self.state == 'warmup_lap':
            self.pyuni.text(20, 5, "Warm-up Lap", 0)
        else:
            self.pyuni.text(20, 5, f"Lap: 1/{MAX_LAPS}", 0)
        if self.safety_car_active:
            self.pyuni.text(20, 20, "Safety Car Deployed", 8)

        hover_info = None  # Track only one hovered car
        for car in self.cars:
            if not car.is_active:
                continue

            # Get car position
            if car.on_pitlane:
                x, y = get_position_along_track(car.pitlane_distance, PIT_LANE_POINTS, PIT_LANE_CUMULATIVE_DISTANCES)
            else:
                x, y = get_position_along_track(car.distance, TRACK_POINTS, CUMULATIVE_DISTANCES)
            if not hover_info and abs(pyxel.mouse_x - x) <= 10 and abs(pyxel.mouse_y - y) <= 10:
                # Determine lap status
                lap_status = (
                    "Planning to pit" if car.pitting else
                    "Racing"
                )
                hover_info = {
                    'x': x,
                    'y': y,
                    'lap_status': lap_status,
                    'tire_key': car.tire_type,
                    'tire_percentage': car.tire_percentage,
                    'name': car.driver_name  # Changed from car.car_number to driver_name
                }
        if hover_info:
            x_box = hover_info['x'] - 7
            y_box = hover_info['y'] - 92
            width, height = 80, 80
            radius = 5
            border_thickness = 1
            self.drawbox(x_box, y_box, width, height, radius, border_thickness)

            pyxel.text(x_box + 5, y_box + 5, hover_info['name'], 1)  # Black color (0)
            pyxel.text(x_box + 5, y_box + 15, hover_info['lap_status'], 1)  # Black color (0)
            pyxel.text(x_box + 5, y_box + 25, f"Morale: Good", 1)  # Placeholder for morale
            pyxel.text(x_box + 5, y_box + 35, f"{hover_info['tire_key'].capitalize()} {hover_info['tire_percentage']:.1f}%", 1)  # Black color (0)
            pyxel.text(x_box + 5, y_box + 45, f"Tyre temps: ", 1)  # Placeholder for tyre temperature
        self.announcements.draw()

    def draw_leaderboard(self):
        """Render the leaderboard on the screen in a compact two-line format per racer."""
        x_offset = 20
        y_offset = 20
        self.pyuni.text(x_offset, y_offset, "Leaderboard:", 1)
        racing_cars = [car for car in self.cars if not car.is_safety_car and car.is_active]
        # Starting Y position for the first racer (just below the header)
        racer_start_y = y_offset + 20
        safety_car_active = self.safety_car_active

        for idx, car in enumerate(
                racing_cars[self.leaderboard_scroll_index:self.leaderboard_scroll_index + 8]
        ):
            global_idx = self.leaderboard_scroll_index + idx
            gap_text = "Leader" if global_idx == 0 else self.get_gap_text(global_idx, racing_cars)
            lap_text = f"Lap: {car.laps_completed}/{MAX_LAPS}"
            best_lap_text = f"Best Lap: {car.best_lap_time:.2f}s" if car.best_lap_time else "Best Lap: N/A"
            stats_text = f"Speed: {car.speed:.2f}"
            car_stats = f"E:{car.engine_power:.2f} A:{car.aero_efficiency:.2f} G:{car.gearbox_quality:.2f}"
            tire_text = f"T:{car.tire_type.capitalize()} {car.tire_percentage:.1f}% PD: {car.calculate_pit_desire(safety_car_active)}"

            # Combine all info into two compact lines with no extra spacing between racers.
            line1 = f"{global_idx + 1}. Car {car.car_number} {gap_text} | {lap_text} | {best_lap_text}"
            line2 = f"{stats_text} | {car_stats} | {tire_text}"

            # Each racer block is 20 pixels high (two lines of 10 pixels each)
            current_y = racer_start_y + idx * 20
            self.pyuni.text(x_offset, current_y, line1, car.color)
            self.pyuni.text(x_offset, current_y + 10, line2, car.color)

    def get_gap_text(self, global_idx, racing_cars):
        """Calculate and return the gap text for the leaderboard."""
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
            gap = (car.initial_time_offset - car_ahead.initial_time_offset) / 5
            return f"+{gap:.1f}s"

