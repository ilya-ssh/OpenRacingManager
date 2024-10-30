from constants import (
    TIRE_TYPES, DEBUG_MODE, MAX_LAPS, PIT_STOP_THRESHOLD,
    PITLANE_SPEED_LIMIT, PIT_STOP_DURATION
)
from track import (
    START_FINISH_INDEX_SMOOTHED,
    TRACK_POINTS,
    CUMULATIVE_DISTANCES,
    TOTAL_TRACK_LENGTH,
    get_position_along_track,
    get_desired_speed_at_distance,
    DESIRED_SPEEDS_LIST,
    PIT_LANE_POINTS,
    PIT_LANE_CUMULATIVE_DISTANCES,
    PIT_LANE_TOTAL_LENGTH,
    PITLANE_ENTRANCE_DISTANCE,
    PITLANE_EXIT_DISTANCE,
    PIT_STOP_POINT
)
import random
import pyxel

class Car:
    def __init__(self, color_index, car_number, grid_position, announcements):
        self.color = color_index
        self.car_number = car_number
        self.tire_type = random.choice(list(TIRE_TYPES.keys()))
        self.tire_percentage = 100.0  # Start with full tire percentage
        self.laps_completed = 0
        self.speed = 0.0
        start_distance = CUMULATIVE_DISTANCES[START_FINISH_INDEX_SMOOTHED]
        self.distance = start_distance - (0.5 + grid_position * 0.1)
        self.previous_distance = self.distance

        # Car stats
        self.engine_power = random.uniform(0.8, 1.2)        # Affects max speed on straights
        self.aero_efficiency = random.uniform(0.8, 1.2)     # Affects cornering speed
        self.gearbox_quality = random.uniform(0.8, 1.2)     # Affects acceleration
        self.suspension_quality = random.uniform(0.8, 1.2)  # Affects tire wear and handling
        self.brake_performance = random.uniform(0.8, 1.2)   # Affects braking intensity

        # Performance parameters
        self.base_max_speed = 1.0  # Base max speed without modifiers
        self.base_acceleration = 0.007  # Base acceleration without modifiers
        self.braking_intensity = 3.0 * self.brake_performance  # Adjusted braking intensity

        # Pitstop variables
        self.on_pitlane = False
        self.pitting = False
        self.pit_stop_done = False
        self.pitlane_distance = 0.0
        self.pit_stop_timer = 0

        # Additional variables for pit announcements
        self.just_entered_pit = False
        self.just_changed_tires = False

        # Variables for lap timing
        self.lap_times = []
        self.best_lap_time = None
        self.lap_start_frame = None

        # Flags to prevent multiple lap counts
        self.just_crossed_start = False
        self.just_crossed_pitstop_point = False

        # New variables
        self.target_speed = self.base_max_speed  # Desired speed at any point
        self.min_speed = 0.1  # Minimum speed to prevent stopping completely
        self.min_max_speed = 0.2  # Minimum max speed to prevent speed from becoming zero

        # Reference to the announcements instance
        self.announcements = announcements

    def update(self, race_started, current_frame):
        if not race_started:
            return

        if self.lap_start_frame is None:
            self.lap_start_frame = current_frame  # Start timing the lap

        self.previous_distance = self.distance

        # Tire wear logic
        wear_rate = TIRE_TYPES[self.tire_type]["wear_rate"] / self.suspension_quality
        if self.tire_percentage < TIRE_TYPES[self.tire_type]["threshold"]:
            wear_rate *= 2
        self.tire_percentage = max(1, self.tire_percentage - wear_rate)  # Ensure it doesn't drop below 1%

        # Cap tire percentage to prevent errors
        self.tire_percentage = max(self.tire_percentage, 1)

        # Decide to pit if tire percentage is low
        if not self.pitting and not self.on_pitlane and self.tire_percentage <= PIT_STOP_THRESHOLD:
            self.pitting = True

        # Pitstop logic
        if self.pitting and not self.on_pitlane:
            # Adjust desired speed to approach pitlane entrance
            current_lap_distance = self.distance % TOTAL_TRACK_LENGTH
            distance_to_entrance = (PITLANE_ENTRANCE_DISTANCE - current_lap_distance) % TOTAL_TRACK_LENGTH

            # Avoid division by zero
            if self.speed > 0:
                time_to_entrance = distance_to_entrance / self.speed
            else:
                time_to_entrance = distance_to_entrance / self.min_speed

            time_to_entrance = max(time_to_entrance, 1)
            self.target_speed = distance_to_entrance / time_to_entrance

            # Ensure the target speed is not too low
            self.target_speed = max(self.target_speed, self.min_speed)

            # If close enough, enter pitlane
            if distance_to_entrance < self.speed * 2 or distance_to_entrance < 1:
                # Enter pitlane
                self.on_pitlane = True
                self.just_entered_pit = True  # Set flag for announcement
                self.pitlane_distance = 0.0
                self.speed = min(self.speed, PITLANE_SPEED_LIMIT)
                self.distance = PITLANE_ENTRANCE_DISTANCE
        elif self.on_pitlane:
            # Update pitlane distance
            self.previous_pitlane_distance = self.pitlane_distance
            self.pitlane_distance += self.speed

            # Check if car crossed pitstop point (middle of pitlane)
            if not self.just_crossed_pitstop_point and self.previous_pitlane_distance <= PIT_STOP_POINT < self.pitlane_distance:
                self.laps_completed += 1
                # Record lap time
                if self.lap_start_frame is not None:
                    lap_time = (current_frame - self.lap_start_frame) / 60.0  # Assuming 60 FPS
                    self.lap_times.append(lap_time)
                    if self.best_lap_time is None or lap_time < self.best_lap_time:
                        self.best_lap_time = lap_time
                self.lap_start_frame = current_frame
                self.just_crossed_pitstop_point = True
                print(f"Car {self.car_number} completed lap {self.laps_completed} with lap time {lap_time:.2f}s")
            # Reset the flag after the car has moved sufficiently past the pitstop point
            if self.just_crossed_pitstop_point and self.pitlane_distance > PIT_STOP_POINT + 10:
                self.just_crossed_pitstop_point = False

            # Check if car is at pitstop point
            if not self.pit_stop_done and self.pitlane_distance >= PIT_STOP_POINT:
                # Car stops for pitstop
                self.speed = 0.0
                self.pit_stop_timer += 1
                if self.pit_stop_timer >= PIT_STOP_DURATION:
                    # Finish pitstop
                    self.pit_stop_done = True
                    self.pit_stop_timer = 0  # Reset pitstop timer
                    # Assign new random tire type and reset tire percentage
                    self.tire_type = random.choice(list(TIRE_TYPES.keys()))
                    self.tire_percentage = 100.0
                    self.just_changed_tires = True  # Set flag for announcement
            else:
                # Car is moving in pitlane
                # Limit speed in pitlane
                self.speed = min(self.speed, PITLANE_SPEED_LIMIT)

            # Check if car has completed pitlane
            if self.pitlane_distance >= PIT_LANE_TOTAL_LENGTH:
                # Exit pitlane
                self.on_pitlane = False
                self.pitting = False
                self.pit_stop_done = False
                self.pitlane_distance = 0.0
                self.speed = PITLANE_SPEED_LIMIT  # Speed upon exiting pitlane
                self.distance = PITLANE_EXIT_DISTANCE
        else:
            # Regular driving logic
            # Adjust target speed based on tire wear
            self.target_speed = get_desired_speed_at_distance(
                self.distance % TOTAL_TRACK_LENGTH,
                DESIRED_SPEEDS_LIST,
                TOTAL_TRACK_LENGTH,
                self
            )
            self.target_speed *= (self.tire_percentage / 100)

            # Ensure the target speed doesn't fall below min_speed
            self.target_speed = max(self.target_speed, self.min_speed)

        # Adjust acceleration based on gearbox quality
        effective_acceleration = self.base_acceleration * self.gearbox_quality

        # Acceleration and braking towards target speed
        if self.speed < self.target_speed:
            self.speed += effective_acceleration
            self.speed = min(self.speed, self.target_speed)
        elif self.speed > self.target_speed:
            speed_diff = self.speed - self.target_speed
            braking_force = (self.braking_intensity * speed_diff) * 0.1  # Adjusted braking force
            self.speed -= braking_force
            self.speed = max(self.speed, self.target_speed)

        # Cap max_speed based on tire percentage and min_max_speed
        # Adjust max_speed for straights and corners
        max_speed = self.base_max_speed * (self.tire_percentage / 100)
        # Determine if the car is in a corner or straight
        is_corner = self.is_in_corner()
        if is_corner:
            max_speed *= self.aero_efficiency
        else:
            max_speed *= self.engine_power
        max_speed = max(max_speed, self.min_max_speed)
        self.speed = min(self.speed, max_speed)

        # Ensure speed doesn't drop below min_speed
        self.speed = max(self.speed, self.min_speed)

        # Update distance
        if not self.on_pitlane:
            self.distance += self.speed

            current_lap_distance = self.distance % TOTAL_TRACK_LENGTH
            previous_lap_distance = self.previous_distance % TOTAL_TRACK_LENGTH

            start_finish_distance = CUMULATIVE_DISTANCES[START_FINISH_INDEX_SMOOTHED]

            # Check if car crossed start-finish line
            if not self.just_crossed_start and previous_lap_distance <= start_finish_distance < current_lap_distance:
                self.laps_completed += 1
                # Record lap time
                if self.lap_start_frame is not None:
                    lap_time = (current_frame - self.lap_start_frame) / 60.0  # Assuming 60 FPS
                    self.lap_times.append(lap_time)
                    if self.best_lap_time is None or lap_time < self.best_lap_time:
                        self.best_lap_time = lap_time
                    print(f"Car {self.car_number} completed lap {self.laps_completed} with lap time {lap_time:.2f}s")
                self.lap_start_frame = current_frame
                self.just_crossed_start = True
            # Reset the flag after the car has moved sufficiently past the start-finish line
            if self.just_crossed_start and current_lap_distance > start_finish_distance + 10:
                self.just_crossed_start = False

        # Send announcements for pit entry and tire change
        if self.just_entered_pit:
            self.announcements.add_message(f"Car {self.car_number} entered the pit lane.")
            self.just_entered_pit = False  # Reset flag

        if self.just_changed_tires:
            self.announcements.add_message(f"Car {self.car_number} changed to {self.tire_type.capitalize()} tires.")
            self.just_changed_tires = False  # Reset flag

        # Debug output
        if DEBUG_MODE:
            print(f"Car {self.car_number} - Lap: {self.laps_completed} | "
                  f"Tire: {self.tire_type.capitalize()} {self.tire_percentage:.1f}% | "
                  f"Speed: {self.speed:.2f} | Max Speed: {max_speed:.2f} | "
                  f"Engine: {self.engine_power:.2f} | Aero: {self.aero_efficiency:.2f} | "
                  f"Gearbox: {self.gearbox_quality:.2f} | "
                  f"Suspension: {self.suspension_quality:.2f} | Brakes: {self.brake_performance:.2f}")

    def is_in_corner(self):
        """Determine if the car is in a corner based on the desired speed profile."""
        # Get current desired speed without car-specific adjustments
        current_lap_distance = self.distance % TOTAL_TRACK_LENGTH
        for i in range(len(DESIRED_SPEEDS_LIST) - 1):
            dist1, base_speed1 = DESIRED_SPEEDS_LIST[i]
            dist2, base_speed2 = DESIRED_SPEEDS_LIST[i + 1]
            if dist1 <= current_lap_distance <= dist2:
                # If the desired speed is significantly lower than max, it's a corner
                avg_base_speed = (base_speed1 + base_speed2) / 2
                if avg_base_speed < self.base_max_speed * 0.9:
                    return True
                else:
                    return False
        return False

    def draw(self):
        if self.on_pitlane:
            x, y = get_position_along_track(self.pitlane_distance, PIT_LANE_POINTS, PIT_LANE_CUMULATIVE_DISTANCES)
        else:
            x, y = get_position_along_track(self.distance, TRACK_POINTS, CUMULATIVE_DISTANCES)
        pyxel.circ(x, y, 3, self.color)

    def get_current_time(self):
        if self.on_pitlane:
            # Adjust the distance to account for pitlane
            adjusted_distance = self.distance + self.pitlane_distance
        else:
            adjusted_distance = self.distance
        return self.laps_completed + (adjusted_distance % TOTAL_TRACK_LENGTH) / TOTAL_TRACK_LENGTH
