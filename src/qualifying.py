import pyxel
import json
import random
from car import Car
from track import (
    PIT_LANE_TOTAL_LENGTH,
    PITLANE_ENTRANCE_DISTANCE,
    TOTAL_TRACK_LENGTH,
    TRACK_POINTS,
    START_FINISH_INDEX_SMOOTHED,
    PIT_LANE_POINTS,
    CUMULATIVE_DISTANCES,
    PIT_LANE_CUMULATIVE_DISTANCES,
    PIT_STOP_POINT,
    get_position_along_track
)
from constants import CURRENT_VER, QUALIFYING_TIME, TIRE_TYPES
from load_teams import load_teams  # Ensure this function is correctly imported

class Qualifying:
    def __init__(self, game):
        self.game = game
        self.pyuni = self.game.pyuni
        self.session_time = QUALIFYING_TIME * 60 * 30  # Assuming QUALIFYING_TIME is in minutes
        self.elapsed_time = 0
        self.cars = []
        self.num_cars = 20  # Adjust as needed based on number of drivers
        self.drivers_map = self.load_drivers()  # Load drivers data
        self.teams_data = load_teams()  # Corrected: Call load_teams() directly
        self.create_cars()
        self.session_over = False
        self.starting_grid = []
        pyxel.colors[0] = 0x000000  # Black
        pyxel.colors[1] = 0xFFFFFF  # White

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
                pyxel.colors[i] = int(team["color"], 16)  # Convert hex color to integer
            except ValueError:
                print(f"Invalid color format for team {team['team_name']}. Using default color 0xFFFFFF.")
                pyxel.colors[i] = 0xFFFFFF  # Default to white if color parsing fails

        for team_index, team in enumerate(self.teams_data):
            for driver in team["drivers"]:
                driver_id = driver["driver_id"]
                driver_data = self.drivers_map.get(driver_id, None)
                if driver_data:
                    driver_name = driver_data["name"]
                    driver_number = driver_data["number"]
                    color_index = team_index + 2  # Ensure unique color index per team
                    grid_position = len(self.cars)  # Position based on the current number of cars
                    car = Car(
                        color_index=color_index,
                        car_number=driver_number,
                        driver_name=driver_name,  # Ensure Car class can accept driver_name
                        grid_position=grid_position,
                        announcements=None,
                        game=self.game,
                        mode='qualifying'
                    )
                    car.qualifying_exit_delay = random.randint(0, 60 * 30 * 3)
                    self.cars.append(car)
                else:
                    print(f"Warning: Driver ID {driver_id} not found in drivers.json")

    def update(self):
        if not self.session_over:
            self.elapsed_time += 1
            if self.elapsed_time >= self.session_time:
                self.session_over = True
                self.calculate_starting_grid()
                self.game.start_race(self.starting_grid)
            else:
                for car in self.cars:
                    car.update_qualifying()
        else:
            pass  # Session is over; no further updates needed

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

    def draw(self):
        pyxel.cls(0)  # Clear screen with white background

        # Draw the track and pit lane
        for i in range(len(TRACK_POINTS) - 1):
            x1, y1 = TRACK_POINTS[i]
            x2, y2 = TRACK_POINTS[i + 1]
            pyxel.line(x1, y1, x2, y2, 1)  # Black color (0)

        # Draw start/finish line
        sx, sy = TRACK_POINTS[START_FINISH_INDEX_SMOOTHED]
        sx_next, sy_next = TRACK_POINTS[(START_FINISH_INDEX_SMOOTHED + 1) % len(TRACK_POINTS)]
        pyxel.line(sx, sy, sx_next, sy_next, 2)  # Red color (2)

        # Draw pit lane
        if PIT_LANE_POINTS:
            for i in range(len(PIT_LANE_POINTS) - 1):
                x1, y1 = PIT_LANE_POINTS[i]
                x2, y2 = PIT_LANE_POINTS[i + 1]
                pyxel.line(x1, y1, x2, y2, 13)  # Light blue color (13)
            pitstop_x, pitstop_y = get_position_along_track(
                PIT_STOP_POINT, PIT_LANE_POINTS, PIT_LANE_CUMULATIVE_DISTANCES
            )
            pyxel.rect(pitstop_x - 2, pitstop_y - 2, 4, 4, 8)  # Green color (8)

        # Draw all cars first
        hover_info = None  # Track only one hovered car
        for car in self.cars:
            if not car.is_active:
                continue

            # Get car position
            if car.on_pitlane:
                x, y = get_position_along_track(car.pitlane_distance, PIT_LANE_POINTS, PIT_LANE_CUMULATIVE_DISTANCES)
            else:
                x, y = get_position_along_track(car.distance, TRACK_POINTS, CUMULATIVE_DISTANCES)

            # Draw the car
            pyxel.circ(x, y, 3, car.color)

            # Check if this car is hovered and store info
            if not hover_info and abs(pyxel.mouse_x - x) <= 10 and abs(pyxel.mouse_y - y) <= 10:
                # Determine lap status
                lap_status = (
                    "In lap" if car.on_in_lap else
                    "Fast lap" if car.on_fast_lap else
                    "Out lap" if car.on_out_lap else
                    "In pit"
                )
                hover_info = {
                    'x': x,
                    'y': y,
                    'lap_status': lap_status,
                    'tire_key': car.tire_type,
                    'tire_percentage': car.tire_percentage,
                    'name': car.driver_name  # Changed from car.car_number to driver_name
                }

        # After all cars are drawn, proceed to draw the UI
        self.pyuni.text(10, 10, 'Qualifying', 1)  # Black color (0)
        # Draw session time and car list
        time_remaining_frames = max(0, self.session_time - self.elapsed_time)
        time_remaining_seconds = time_remaining_frames / 30
        minutes = int(time_remaining_seconds // 60)
        seconds = int(time_remaining_seconds % 60)
        time_text = f"Time Remaining: {minutes}:{seconds:02d}"
        self.pyuni.text(10, 20, time_text, 1)

        y_offset = 30
        # Sort cars based on best lap time; cars without lap time are placed at the end
        sorted_cars = sorted(
            self.cars,
            key=lambda c: c.best_lap_time if c.best_lap_time is not None else float('inf')
        )
        for i, car in enumerate(sorted_cars):
            lap_time = f"{car.best_lap_time:.2f}" if car.best_lap_time else "-"
            text = f"{i+1} {car.driver_name}: {lap_time}"
            self.pyuni.text(10, y_offset + i * 10, text, 1)  # Black color (0)

        self.pyuni.text(370, 480, CURRENT_VER, 1)  # Black color (0)

        # Draw tooltip for the single hovered car last
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

    def calculate_starting_grid(self):
        """Calculate and set the starting grid based on qualifying results."""
        # Sort cars based on best lap time; cars without lap time are placed at the end
        self.cars.sort(key=lambda c: c.best_lap_time if c.best_lap_time is not None else float('inf'))
        self.starting_grid = [car.car_number for car in self.cars]
