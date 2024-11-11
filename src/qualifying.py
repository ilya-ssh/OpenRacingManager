import pyxel
import random
from car import Car
from track import PIT_LANE_TOTAL_LENGTH, PITLANE_ENTRANCE_DISTANCE, TOTAL_TRACK_LENGTH, TRACK_POINTS, START_FINISH_INDEX_SMOOTHED, PIT_LANE_POINTS, CUMULATIVE_DISTANCES, PIT_LANE_CUMULATIVE_DISTANCES, PIT_STOP_POINT
from constants import CURRENT_VER, QUALIFYING_TIME, TIRE_TYPES
from track import get_position_along_track
from load_teams import load_teams
class Qualifying:
    def __init__(self, game):
        self.game = game
        self.pyuni = self.game.pyuni
        self.session_time = QUALIFYING_TIME * 60 * 30
        self.elapsed_time = 0
        self.cars = []
        self.num_cars = 20
        self.create_cars()
        self.session_over = False
        self.starting_grid = []
        pyxel.colors[0] = 0xFFFFFFFF
        pyxel.colors[1] = 0x00000000

    def create_cars(self):
        teams_data = load_teams()

        # Set pyxel colors based on team data
        for i, team in enumerate(teams_data, start=2):
            pyxel.colors[i] = int(team["color"], 16)  # Convert hex to integer

        for i, team in enumerate(teams_data):
            for driver in team["drivers"]:
                car_number = driver["name"]
                color_index = i + 2
                grid_position = len(self.cars)
                car = Car(color_index, car_number, grid_position, announcements=None, game=self.game, mode='qualifying')
                car.qualifying_exit_delay = random.randint(0, 60 * 30 * 3)
                self.cars.append(car)

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
            pass

    def drawbox(self, x_box, y_box, width, height, radius, border_thickness):
        # Draw white border
        pyxel.rect(x_box + radius, y_box, width - 2 * radius, height, 0)
        pyxel.rect(x_box, y_box + radius, width, height - 2 * radius, 0)
        pyxel.rect(x_box + radius, y_box + height - radius, width - 2 * radius, radius, 0)

        # Draw white rounded corners
        pyxel.circ(x_box + radius, y_box + radius, radius, 0)
        pyxel.circ(x_box + width - radius - 1, y_box + radius, radius, 0)
        pyxel.circ(x_box + radius, y_box + height - radius - 1, radius, 0)
        pyxel.circ(x_box + width - radius - 1, y_box + height - radius - 1, radius, 0)

        # Draw inner black box
        inner_x, inner_y = x_box + border_thickness, y_box + border_thickness
        inner_width, inner_height = width - 2 * border_thickness, height - 2 * border_thickness
        inner_radius = radius - border_thickness

        pyxel.rect(inner_x + inner_radius, inner_y, inner_width - 2 * inner_radius, inner_height, 1)
        pyxel.rect(inner_x, inner_y + inner_radius, inner_width, inner_height - 2 * inner_radius, 1)
        pyxel.rect(inner_x + inner_radius, inner_y + inner_height - inner_radius, inner_width - 2 * inner_radius,
                   inner_radius, 1)

        # Draw black rounded corners
        pyxel.circ(inner_x + inner_radius, inner_y + inner_radius, inner_radius, 1)
        pyxel.circ(inner_x + inner_width - inner_radius - 1, inner_y + inner_radius, inner_radius, 1)
        pyxel.circ(inner_x + inner_radius, inner_y + inner_height - inner_radius - 1, inner_radius, 1)
        pyxel.circ(inner_x + inner_width - inner_radius - 1, inner_y + inner_height - inner_radius - 1,
                   inner_radius, 1)

    def draw(self):
        pyxel.cls(1)

        # Draw the track and pit lane
        for i in range(len(TRACK_POINTS) - 1):
            x1, y1 = TRACK_POINTS[i]
            x2, y2 = TRACK_POINTS[i + 1]
            pyxel.line(x1, y1, x2, y2, 0)

        # Draw start/finish line
        sx, sy = TRACK_POINTS[START_FINISH_INDEX_SMOOTHED]
        sx_next, sy_next = TRACK_POINTS[(START_FINISH_INDEX_SMOOTHED + 1) % len(TRACK_POINTS)]
        pyxel.line(sx, sy, sx_next, sy_next, 2)

        # Draw pit lane
        if PIT_LANE_POINTS:
            for i in range(len(PIT_LANE_POINTS) - 1):
                x1, y1 = PIT_LANE_POINTS[i]
                x2, y2 = PIT_LANE_POINTS[i + 1]
                pyxel.line(x1, y1, x2, y2, 13)
            pitstop_x, pitstop_y = get_position_along_track(PIT_STOP_POINT, PIT_LANE_POINTS,
                                                            PIT_LANE_CUMULATIVE_DISTANCES)
            pyxel.rect(pitstop_x - 2, pitstop_y - 2, 4, 4, 8)

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
                    'name' : car.car_number
                }

        # After all cars are drawn, proceed to draw the UI
        self.pyuni.text(10, 10, 'Qualifying', 0)
        # Draw session time and car list
        time_remaining_frames = max(0, self.session_time - self.elapsed_time)
        time_remaining_seconds = time_remaining_frames / 30
        minutes = int(time_remaining_seconds // 60)
        seconds = int(time_remaining_seconds % 60)
        time_text = f"Time Remaining: {minutes}:{seconds:02d}"
        self.pyuni.text(10, 20, time_text, 0)

        y_offset = 30
        sorted_cars = sorted(self.cars, key=lambda c: c.best_lap_time if c.best_lap_time else float('inf'))
        for i, car in enumerate(sorted_cars):
            lap_time = f"{car.best_lap_time:.2f}" if car.best_lap_time else "-"
            text = f"{i+1} {car.car_number}: {lap_time}"
            self.pyuni.text(10, y_offset + i * 10, text, 0)

        self.pyuni.text(370, 480, CURRENT_VER, 0)

        # Draw tooltip for the single hovered car last
        if hover_info:
            x_box = hover_info['x'] - 7
            y_box = hover_info['y'] - 92
            width, height = 80, 80
            radius = 5
            border_thickness = 1
            self.drawbox(x_box,y_box,width,height,radius,border_thickness)



            pyxel.text(hover_info['x'] - 5, hover_info['y'] - 85, hover_info['name'], 0)
            pyxel.text(hover_info['x'] - 5, hover_info['y'] - 78, hover_info['lap_status'], 0)
            pyxel.text(hover_info['x'] - 5, hover_info['y'] - 71,
                       f"Morale: Good", 0)
            pyxel.text(hover_info['x'] - 5, hover_info['y'] - 65,
                       f"{hover_info['tire_key'].capitalize()} {hover_info['tire_percentage']:.1f}%", 0)
            pyxel.text(hover_info['x'] - 5, hover_info['y'] - 58,
                       f"Tyre temps: ", 0)


    def calculate_starting_grid(self):
        self.cars.sort(key=lambda c: c.best_lap_time if c.best_lap_time is not None else float('inf'))
        self.starting_grid = [car.car_number for car in self.cars]
