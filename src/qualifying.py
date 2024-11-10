import pyxel
import random
from car import Car
from track import PIT_LANE_TOTAL_LENGTH, PITLANE_ENTRANCE_DISTANCE, TOTAL_TRACK_LENGTH, TRACK_POINTS, START_FINISH_INDEX_SMOOTHED, PIT_LANE_POINTS, CUMULATIVE_DISTANCES, PIT_LANE_CUMULATIVE_DISTANCES, PIT_STOP_POINT
from constants import CURRENT_VER, QUALIFYING_TIME
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

    def draw(self):
        pyxel.cls(1)
        for i in range(len(TRACK_POINTS) - 1):
            x1, y1 = TRACK_POINTS[i]
            x2, y2 = TRACK_POINTS[i + 1]
            pyxel.line(x1, y1, x2, y2, 0)
        sx, sy = TRACK_POINTS[START_FINISH_INDEX_SMOOTHED]
        sx_next, sy_next = TRACK_POINTS[(START_FINISH_INDEX_SMOOTHED + 1) % len(TRACK_POINTS)]
        pyxel.line(sx, sy, sx_next, sy_next, 2)
        if PIT_LANE_POINTS:
            for i in range(len(PIT_LANE_POINTS) - 1):
                x1, y1 = PIT_LANE_POINTS[i]
                x2, y2 = PIT_LANE_POINTS[i + 1]
                pyxel.line(x1, y1, x2, y2, 13)
            pitstop_x, pitstop_y = get_position_along_track(PIT_STOP_POINT, PIT_LANE_POINTS, PIT_LANE_CUMULATIVE_DISTANCES)
            pyxel.rect(pitstop_x - 2, pitstop_y - 2, 4, 4, 8)
        for car in self.cars:
            car.draw()
        time_remaining_frames = max(0, self.session_time - self.elapsed_time)
        time_remaining_seconds = time_remaining_frames / 30
        minutes = int(time_remaining_seconds // 60)
        seconds = int(time_remaining_seconds % 60)
        time_text = f"Time Remaining: {minutes}:{seconds:02d}"
        self.pyuni.text(10, 10, time_text, 0)
        y_offset = 30
        sorted_cars = sorted(self.cars, key=lambda c: c.best_lap_time if c.best_lap_time else float('inf'))
        for i, car in enumerate(sorted_cars):
            lap_time = f"{car.best_lap_time:.2f}" if car.best_lap_time else "-"
            text = f"Car {car.car_number}: {lap_time}"
            self.pyuni.text(10, y_offset + i * 10, text, 0)
        self.pyuni.text(370, 480, CURRENT_VER, 0)

    def calculate_starting_grid(self):
        self.cars.sort(key=lambda c: c.best_lap_time if c.best_lap_time is not None else float('inf'))
        self.starting_grid = [car.car_number for car in self.cars]
