# car.py
from constants import TIRE_TYPES, DEBUG_MODE, MAX_LAPS
from track import (
    START_FINISH_INDEX,
    TRACK_POINTS,
    CUMULATIVE_DISTANCES,
    TOTAL_TRACK_LENGTH,
    get_position_along_track,
    get_desired_speed_at_distance,
    DESIRED_SPEEDS_LIST
)
import random
import pyxel

class Car:
    def __init__(self, color_index, car_number, grid_position):
        self.color = color_index
        self.car_number = car_number
        self.tire_type = random.choice(list(TIRE_TYPES.keys()))
        self.tire_percentage = 100.0  # Start with full tire percentage
        self.laps_completed = 0  # Start laps at -1
        self.speed = 0.0
        self.just_crossed_start = False  
        start_distance = CUMULATIVE_DISTANCES[START_FINISH_INDEX]
        self.distance = start_distance - (0.5 + grid_position * 0.1)
        self.previous_distance = self.distance

        # Car stats
        self.engine_power = random.uniform(0.8, 1.2)        # Affects max speed and acceleration
        self.aero_efficiency = random.uniform(0.8, 1.2)     # Affects cornering speed
        self.suspension_quality = random.uniform(0.8, 1.2)  # Affects tire wear and handling
        self.brake_performance = random.uniform(0.8, 1.2)   # Affects braking intensity

        # Performance parameters
        self.base_max_speed = 1.0 * self.engine_power
        self.base_acceleration = 0.007 * self.engine_power  # Base acceleration
        self.braking_intensity = 3.0 * self.brake_performance  # Adjusted braking intensity

    def update(self, race_started):
        if not race_started:
            return

        self.previous_distance = self.distance

        # Tire wear logic
        wear_rate = TIRE_TYPES[self.tire_type]["wear_rate"] / self.suspension_quality
        if self.tire_percentage < TIRE_TYPES[self.tire_type]["threshold"]:
            wear_rate *= 2
        self.tire_percentage = max(0, self.tire_percentage - wear_rate)

        # Tire blowout simulation
        if self.tire_percentage < 5:
            self.base_max_speed = 0.5

        # Get desired speed
        current_lap_distance = self.distance % TOTAL_TRACK_LENGTH
        desired_speed = get_desired_speed_at_distance(
            current_lap_distance,
            DESIRED_SPEEDS_LIST,
            TOTAL_TRACK_LENGTH,
            self
        )
        desired_speed *= (self.tire_percentage / 100)

        # Acceleration and braking towards desired speed
        if self.speed < desired_speed:
            acceleration = self.base_acceleration
            self.speed += acceleration
            self.speed = min(self.speed, desired_speed)
        elif self.speed > desired_speed:
            speed_diff = self.speed - desired_speed
            braking_force = (self.braking_intensity * speed_diff) * 30
            self.speed -= braking_force
            self.speed = max(self.speed, desired_speed)

        if self.speed < 0:
            self.speed = 0.1

        # Cap speed
        max_speed = self.base_max_speed * (self.tire_percentage / 100)
        self.speed = min(self.speed, max_speed)

        # Update distance
        self.distance += self.speed

        # Lap completion check using the start/finish crossing flag
        if not self.just_crossed_start and \
           self.previous_distance > CUMULATIVE_DISTANCES[START_FINISH_INDEX] and \
           self.distance % TOTAL_TRACK_LENGTH < CUMULATIVE_DISTANCES[START_FINISH_INDEX]:
            self.laps_completed += 1
            self.just_crossed_start = True  # Set flag after crossing the line

        # Reset the flag once the car is well past the start/finish line
        if self.distance % TOTAL_TRACK_LENGTH > CUMULATIVE_DISTANCES[START_FINISH_INDEX] + 10:
            self.just_crossed_start = False

        # Debug output
        if DEBUG_MODE:
            print(f"Car {self.car_number} - Lap: {self.laps_completed} | "
                  f"Tire: {self.tire_type.capitalize()} {self.tire_percentage:.1f}% | "
                  f"Speed: {self.speed:.2f} | Max Speed: {max_speed:.2f} | "
                  f"Engine: {self.engine_power:.2f} | Aero: {self.aero_efficiency:.2f} | "
                  f"Suspension: {self.suspension_quality:.2f} | Brakes: {self.brake_performance:.2f}")

    def draw(self):
        x, y = get_position_along_track(self.distance, TRACK_POINTS, CUMULATIVE_DISTANCES)
        pyxel.circ(x, y, 3, self.color)

    def get_current_time(self):
        return self.laps_completed + (self.distance % TOTAL_TRACK_LENGTH) / TOTAL_TRACK_LENGTH
