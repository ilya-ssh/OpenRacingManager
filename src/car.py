import random
import pyxel
from constants import (
    TIRE_TYPES, PITLANE_SPEED_LIMIT,  OVERTAKE_CHANCE, CRASH_CHANCE,
    SAFETY_CAR_SPEED, SAFETY_CAR_GAP_DISTANCE, SAFETY_CAR_CATCH_UP_SPEED,
    PIT_STOP_THRESHOLD, PIT_STOP_DURATION, MAX_LAPS, DEBUG_MODE
)
from track import (
    get_desired_speed_at_distance, get_position_along_track,
    PIT_LANE_POINTS, PIT_LANE_CUMULATIVE_DISTANCES, TRACK_POINTS, PITLANE_ENTRANCE_DISTANCE,
    PITLANE_EXIT_DISTANCE, TOTAL_TRACK_LENGTH, DESIRED_SPEEDS_LIST,
    PIT_STOP_POINT, PIT_LANE_TOTAL_LENGTH, CUMULATIVE_DISTANCES,
    START_FINISH_INDEX_SMOOTHED,
)

class Car:
    def __init__(self, color_index, car_number, driver_name, grid_position,
                 announcements, pitbox_coords, pitbox_distance, game=None, mode='race', start_delay_frames=0):
        self.color = color_index
        self.car_number = car_number
        self.grid_position = grid_position
        self.announcements = announcements
        self.game = game
        self.driver_name = driver_name
        self.mode = mode
        self.crashed = False
        self.speed = 0.0
        self.previous_distance = 0.0
        self.pitbox_coords = pitbox_coords
        self.pitlane_distance = pitbox_distance
        self.pitbox_distance = pitbox_distance
        self.lap_times = []
        self.best_lap_time = None
        self.current_lap_start_frame = None
        self.is_active = True
        self.engine_power = random.uniform(0.8, 1.2)
        self.aero_efficiency = random.uniform(0.8, 1.2)
        self.gearbox_quality = random.uniform(0.8, 1.2)
        self.suspension_quality = random.uniform(0.8, 1.2)
        self.brake_performance = random.uniform(0.8, 1.2)
        self.base_max_speed = 1.0
        self.base_acceleration = 0.007
        self.braking_intensity = 3.0 * self.brake_performance
        self.min_speed = 0.1
        self.min_max_speed = 0.2
        if self.mode == 'qualifying':
            self.initialize_qualifying_mode()
        elif self.mode == 'race':
            self.initialize_race_mode()

    def update(self, race_started, current_frame, cars, safety_car_active):
        if not self.is_active:
            return
        if self.mode == 'qualifying':
            self.update_qualifying()
        elif self.mode == 'race':
            self.update_race(race_started, current_frame, cars, safety_car_active)

    # -------------------- Race Functions --------------------

    def initialize_race_mode(self):
        self.just_crossed_pitstop_point = False
        self.lap_start_frame = None
        self.just_crossed_start = False
        self.laps_completed = 0
        self.is_at_grid_position = True
        self.warmup_completed = False
        self.announced_on_grid = False
        self.crash_timer = 0
        self.is_under_safety_car = False
        self.is_safety_car = False
        self.is_exiting = False
        self.has_caught_safety_car = False
        self.is_safety_car_ending = False
        self.start_delay_frames = 0
        self.warmup_started = False
        self.tire_type = random.choice(list(TIRE_TYPES.keys()))
        self.tire_percentage = 100.0
        spacing_factor = 1.0
        start_distance = CUMULATIVE_DISTANCES[START_FINISH_INDEX_SMOOTHED]
        self.grid_distance = (start_distance - (0.5 + self.grid_position * spacing_factor)) % TOTAL_TRACK_LENGTH
        self.distance = self.grid_distance
        self.previous_distance = self.distance
        self.on_pitlane = False
        self.pitting = False
        self.pit_stop_done = False
        self.pit_stop_timer = 0
        self.just_entered_pit = False
        self.just_changed_tires = False
        self.target_speed = self.base_max_speed
        self.initial_time_offset = 0.0
        self.adjusted_distance = 0.0
        self.adjusted_total_distance = 0.0
        self.pitlane_distance = 0.0
        self.previous_pitlane_distance = self.pitlane_distance

    def update_warmup(self, current_frame):
        if not self.warmup_started:
            if current_frame >= self.start_delay_frames:
                self.warmup_started = True
                self.speed = 0.3
            else:
                self.speed = 0.0
                return
        if not self.warmup_completed:
            self.distance += self.speed
            self.distance %= TOTAL_TRACK_LENGTH
            distance_to_grid = (self.grid_distance - self.distance) % TOTAL_TRACK_LENGTH
            if distance_to_grid <= self.speed:
                self.distance = self.grid_distance
                self.speed = 0.0
                self.warmup_completed = True
                self.is_at_grid_position = True
        else:
            self.speed = 0.0

    def update_race(self, race_started, current_frame, cars, safety_car_active):
        if not self.is_active:
            return
        if self.is_safety_car:
            self.update_safety_car_behavior()
            return
        if not race_started or self.crashed:
            return
        self.previous_distance = self.distance
        self.previous_pitlane_distance = self.pitlane_distance
        wear_rate = TIRE_TYPES[self.tire_type]["wear_rate"] / self.suspension_quality
        if self.tire_percentage < TIRE_TYPES[self.tire_type]["threshold"]:
            wear_rate *= 2
        self.tire_percentage = max(1, self.tire_percentage - wear_rate)
        self.tire_percentage = max(self.tire_percentage, 1)
        if not self.pitting and not self.on_pitlane and self.tire_percentage <= PIT_STOP_THRESHOLD:
            self.pitting = True
        if safety_car_active or self.is_under_safety_car:
            self.update_adjusted_distance()
            if self.crossed_start_finish_line():
                self.laps_completed += 1
            return
        else:
            self.attempt_overtake(cars, safety_car_active)
            if self.pitting and not self.on_pitlane:
                self.to_pitlane(current_frame)
            elif self.on_pitlane:
                self.in_pitlane(current_frame)
            else:
                self.target_speed = get_desired_speed_at_distance(
                    self.distance % TOTAL_TRACK_LENGTH,
                    DESIRED_SPEEDS_LIST,
                    TOTAL_TRACK_LENGTH,
                    self
                )
                self.target_speed *= (self.tire_percentage / 100)
                self.target_speed = max(self.target_speed, self.min_speed)
            effective_acceleration = self.base_acceleration * self.gearbox_quality
            if self.speed < self.target_speed:
                self.speed += effective_acceleration
                self.speed = min(self.speed, self.target_speed)
            elif self.speed > self.target_speed:
                speed_diff = self.speed - self.target_speed
                braking_force = (self.braking_intensity * speed_diff) * 0.1
                self.speed -= braking_force
                self.speed = max(self.speed, self.target_speed)
            max_speed = self.base_max_speed * (self.tire_percentage / 100)
            is_corner = self.is_in_corner()
            if is_corner:
                max_speed *= self.aero_efficiency
            else:
                max_speed *= self.engine_power
            max_speed = max(max_speed, self.min_max_speed)
            self.speed = min(self.speed, max_speed)
            self.speed = max(self.speed, self.min_speed)
            if not self.on_pitlane:
                self.distance += self.speed
                current_lap_distance = self.distance % TOTAL_TRACK_LENGTH
                previous_lap_distance = self.previous_distance % TOTAL_TRACK_LENGTH
                start_finish_distance = CUMULATIVE_DISTANCES[START_FINISH_INDEX_SMOOTHED]
                crossed_line = False
                if previous_lap_distance <= start_finish_distance < current_lap_distance:
                    crossed_line = True
                elif current_lap_distance < previous_lap_distance:
                    if previous_lap_distance <= start_finish_distance or start_finish_distance < current_lap_distance:
                        crossed_line = True
                if crossed_line and not self.just_crossed_start:
                    self.laps_completed += 1
                    if self.lap_start_frame is not None and self.first_lap_completed:
                        lap_time = (current_frame - self.lap_start_frame) / 30.0
                        self.lap_times.append(lap_time)
                        if self.best_lap_time is None or lap_time < self.best_lap_time:
                            self.best_lap_time = lap_time
                    else:
                        self.first_lap_completed = True
                    self.lap_start_frame = current_frame
                    self.just_crossed_start = True
                else:
                    if abs(current_lap_distance - start_finish_distance) > 1:
                        self.just_crossed_start = False
            self.update_adjusted_distance()
            if self.just_entered_pit:
                self.announcements.add_message(f"Car {self.car_number} entered the pit lane.")
                self.just_entered_pit = False
            if self.just_changed_tires:
                self.announcements.add_message(f"Car {self.car_number} changed to {self.tire_type.capitalize()} tires.")
                self.just_changed_tires = False
            if DEBUG_MODE:
                print(f"Car {self.car_number} - Lap: {self.laps_completed} | Tire: {self.tire_type.capitalize()} {self.tire_percentage:.1f}% | Speed: {self.speed:.2f} | Max Speed: {max_speed:.2f} | Engine: {self.engine_power:.2f} | Aero: {self.aero_efficiency:.2f} | Gearbox: {self.gearbox_quality:.2f} | Suspension: {self.suspension_quality:.2f} | Brakes: {self.brake_performance:.2f}")

    def to_pitlane(self, current_frame):
        current_lap_distance = self.distance % TOTAL_TRACK_LENGTH
        distance_to_entrance = (PITLANE_ENTRANCE_DISTANCE - current_lap_distance) % TOTAL_TRACK_LENGTH
        if self.speed > 0:
            time_to_entrance = distance_to_entrance / self.speed
        else:
            time_to_entrance = distance_to_entrance / self.min_speed
        time_to_entrance = max(time_to_entrance, 1)
        self.target_speed = distance_to_entrance / time_to_entrance
        self.target_speed = max(self.target_speed, self.min_speed)
        if distance_to_entrance < self.speed * 2 or distance_to_entrance < 1:
            self.on_pitlane = True
            self.just_entered_pit = True
            self.pitlane_distance = 0.0
            self.speed = min(self.speed, PITLANE_SPEED_LIMIT)
            self.distance = PITLANE_ENTRANCE_DISTANCE

    def in_pitlane(self, current_frame):
        # ---------------------
        # Modified Race Pitstop Logic:
        #
        # First, the car accelerates along the pitlane until it reaches its unique pitbox,
        # determined by self.pitbox_distance. Once the car’s previous pitlane distance is less
        # than or equal to its pitbox and the current pitlane distance exceeds it, the car stops.
        #
        # While stopped at its pitbox, a pit stop timer counts up. When the timer exceeds
        # PIT_STOP_DURATION, the pit stop is complete (tires are changed, etc.).
        #
        # After the pit stop, the car accelerates out of the pit lane.
        # ---------------------
        if not self.pit_stop_done:
            # Accelerate along the pitlane until the car reaches its pitbox.
            self.previous_pitlane_distance = self.pitlane_distance
            self.speed = min(self.speed + self.base_acceleration, PITLANE_SPEED_LIMIT)
            self.pitlane_distance += self.speed
            # Check if the car has just reached (or passed) its pitbox.
            if self.previous_pitlane_distance <= self.pitbox_distance < self.pitlane_distance:
                # Snap the car to its pitbox and stop.
                self.speed = 0.0
                self.pitlane_distance = self.pitbox_distance
                # Increment the pit stop timer while stopped.
                self.pit_stop_timer += 1
                if self.pit_stop_timer >= PIT_STOP_DURATION:
                    self.pit_stop_done = True
                    self.pit_stop_timer = 0
                    # Change tires (or perform any other pit stop actions).
                    self.tire_type = random.choice(list(TIRE_TYPES.keys()))
                    self.tire_percentage = 100.0
                    self.just_changed_tires = True
        else:
            # Once the pit stop is complete, accelerate to exit the pit lane.
            self.previous_pitlane_distance = self.pitlane_distance
            self.speed = min(self.speed + self.base_acceleration, PITLANE_SPEED_LIMIT)
            self.pitlane_distance += self.speed
            if self.pitlane_distance >= PIT_LANE_TOTAL_LENGTH:
                # Exit the pitlane and rejoin the track.
                self.on_pitlane = False
                self.pitting = False
                self.pit_stop_done = False
                self.pitlane_distance = 0.0
                self.speed = PITLANE_SPEED_LIMIT
                self.distance = PITLANE_EXIT_DISTANCE

    def update_safety_car_behavior(self):
        self.previous_distance = self.distance
        if self.is_exiting and self.is_safety_car:
            print(self.car_number)
            self.speed += self.base_acceleration * 0.5
            self.speed = min(self.speed, SAFETY_CAR_SPEED * 2)
            self.distance += self.speed
            self.distance %= TOTAL_TRACK_LENGTH
            if (self.distance >= PITLANE_ENTRANCE_DISTANCE and self.previous_distance < PITLANE_ENTRANCE_DISTANCE):
                self.is_active = False
        else:
            self.distance += self.speed
            self.distance %= TOTAL_TRACK_LENGTH

    def update_under_safety_car(self, current_frame, safety_car, car_ahead=None):
        if self.crashed or not self.is_active:
            return
        if self.pitting and not self.on_pitlane:
            self.to_pitlane(current_frame)
        if self.on_pitlane:
            self.in_pitlane(current_frame)
            print(f"in pitlane", self.car_number, self.speed)
            return
        self.previous_distance = self.distance
        desired_gap = SAFETY_CAR_GAP_DISTANCE
        if self.is_safety_car_ending and not self.is_safety_car:
            self.speed = SAFETY_CAR_SPEED
        if car_ahead and car_ahead.is_active and car_ahead != safety_car:
            distance_to_car_ahead = (car_ahead.distance - self.distance) % TOTAL_TRACK_LENGTH
            gap_error = distance_to_car_ahead - desired_gap
            if gap_error > 1.0:
                acceleration = min(self.base_acceleration * gap_error * 0.1, self.base_acceleration)
                self.speed = min(self.speed + acceleration, SAFETY_CAR_CATCH_UP_SPEED)
            elif gap_error < -1.0:
                braking = min(self.braking_intensity * abs(gap_error) * 0.1, self.braking_intensity)
                self.speed = max(self.speed - braking * 0.1, 0)
            else:
                self.speed = car_ahead.speed
        else:
            distance_to_safety_car = (safety_car.distance - self.distance) % TOTAL_TRACK_LENGTH
            print(distance_to_safety_car)
            if distance_to_safety_car > SAFETY_CAR_GAP_DISTANCE*10 and not safety_car.is_exiting:
                safety_car.speed = SAFETY_CAR_SPEED * 0.1
            elif distance_to_safety_car < SAFETY_CAR_GAP_DISTANCE*10 and not safety_car.is_exiting:
                safety_car.speed = SAFETY_CAR_SPEED
            print(distance_to_safety_car)
            gap_error = distance_to_safety_car - desired_gap
            if gap_error > 1.0:
                acceleration = min(self.base_acceleration * gap_error * 0.1, self.base_acceleration)
                self.speed = min(self.speed + acceleration, SAFETY_CAR_CATCH_UP_SPEED)
            elif gap_error < -1.0:
                braking = min(self.braking_intensity * abs(gap_error) * 0.1, self.braking_intensity)
                self.speed = max(self.speed - braking * 0.1, 0)
            else:
                self.speed = safety_car.speed
        self.distance = (self.distance + self.speed) % TOTAL_TRACK_LENGTH
        self.update_adjusted_distance()
        if self.crossed_start_finish_line():
            self.laps_completed += 1
        wear_rate = TIRE_TYPES[self.tire_type]["wear_rate"] / self.suspension_quality * 0.5
        self.tire_percentage = max(1, self.tire_percentage - wear_rate)

    def attempt_overtake(self, cars, safety_car_active):
        if safety_car_active or self.is_under_safety_car:
            return
        for other_car in cars:
            if other_car.car_number == self.car_number or other_car.crashed or not other_car.is_active:
                continue
            distance_diff = (other_car.distance - self.distance) % TOTAL_TRACK_LENGTH
            if 0 < distance_diff < 5:
                if random.random() < OVERTAKE_CHANCE:
                    pass
                else:
                    if random.random() < CRASH_CHANCE:
                        self.crashed = True
                        self.speed = 0.0
                        self.is_active = False
                        self.announcements.add_message(f"Car {self.car_number} has crashed!")
                        break

    def attempt_overtake(self, cars, safety_car_active):
        if safety_car_active or self.is_under_safety_car:
            return
        for other_car in cars:
            if other_car.car_number == self.car_number or other_car.crashed or not other_car.is_active:
                continue
            distance_diff = (other_car.distance - self.distance) % TOTAL_TRACK_LENGTH
            if 0 < distance_diff < 5:
                if random.random() < OVERTAKE_CHANCE:
                    pass
                else:
                    if random.random() < CRASH_CHANCE:
                        self.crashed = True
                        self.speed = 0.0
                        self.is_active = False
                        self.announcements.add_message(f"Car {self.car_number} has crashed!")
                        break

    # -------------------- Qualifying Functions --------------------

    def initialize_qualifying_mode(self):
        self.in_pit = True
        self.on_out_lap = False
        self.on_fast_lap = False
        self.on_in_lap = False
        self.has_time_for_another_run = True
        self.qualifying_exit_delay = random.randint(0, 60 * 30 * 3)
        self.last_exit_time = 0
        self.on_pitlane = True
        # self.pitlane_distance = PIT_STOP_POINT
        self.distance = PITLANE_ENTRANCE_DISTANCE
        self.previous_distance = self.distance
        self.laps_completed = 0
        self.tire_type = "soft"
        self.tire_percentage = 100.0

    def update_qualifying(self):
        if self.crashed:
            return
        if self.in_pit:
            if self.has_time_for_another_run:
                if self.game.qualifying.elapsed_time >= self.qualifying_exit_delay:
                    self.in_pit = False
                    self.on_pitlane = True
                    self.on_out_lap = True
                    self.speed = 0.0
                    self.pit_stop_done = True
        elif self.on_out_lap:
            self.previous_distance = self.distance
            if self.on_pitlane:
                self.update_pitlane_exit()
            else:
                self.update_movement()
                if self.crossed_start_finish_line():
                    self.on_out_lap = False
                    self.on_fast_lap = True
                    self.current_lap_start_frame = self.game.qualifying.elapsed_time
        elif self.on_fast_lap:
            self.previous_distance = self.distance
            self.update_movement()
            if self.crossed_start_finish_line():
                lap_time = (self.game.qualifying.elapsed_time - self.current_lap_start_frame) / 30.0
                self.lap_times.append(lap_time)
                if self.best_lap_time is None or lap_time < self.best_lap_time:
                    self.best_lap_time = lap_time
                self.on_fast_lap = False
                self.on_in_lap = True
        elif self.on_in_lap:
            self.previous_distance = self.distance
            self.update_movement()
            if (self.distance >= PITLANE_ENTRANCE_DISTANCE and self.previous_distance < PITLANE_ENTRANCE_DISTANCE):
                self.on_pitlane = True
            if self.on_pitlane:
                self.update_pitlane_entry()

    def update_pitlane_entry(self):
        self.previous_pitlane_distance = self.pitlane_distance
        self.speed = min(self.speed + self.base_acceleration, PITLANE_SPEED_LIMIT)
        self.pitlane_distance += self.speed
        print(f'self.previous_pitlane_distance {self.previous_pitlane_distance}')
        print(f'self.pitbox_distance {self.pitbox_distance}')
        print(f'self.pitlane_distance {self.pitlane_distance}')
        if (self.previous_pitlane_distance <= self.pitbox_distance < self.pitlane_distance):
            self.speed = 0.0
            self.in_pit = True
            self.on_in_lap = False
            remaining_time = self.game.qualifying.session_time - self.game.qualifying.elapsed_time
            estimated_time_for_run = (self.best_lap_time or 60 * 30) * 2
            if remaining_time > estimated_time_for_run:
                self.qualifying_exit_delay = self.game.qualifying.elapsed_time + random.randint(60 * 5, 60 * 15)
                self.has_time_for_another_run = True
            else:
                self.has_time_for_another_run = False

    def update_pitlane_exit(self):
        self.previous_pitlane_distance = self.pitlane_distance
        self.speed = min(self.speed + self.base_acceleration, PITLANE_SPEED_LIMIT)
        self.pitlane_distance += self.speed
        if self.pitlane_distance >= PIT_LANE_TOTAL_LENGTH:
            self.on_pitlane = False
            self.distance = PITLANE_EXIT_DISTANCE
            self.pitlane_distance = 0.0
            self.speed = self.min_speed

    def update_movement(self):
        wear_rate = TIRE_TYPES[self.tire_type]["wear_rate"] / self.suspension_quality
        if self.tire_percentage < TIRE_TYPES[self.tire_type]["threshold"]:
            wear_rate *= 2
        self.tire_percentage = max(1, self.tire_percentage - wear_rate)
        self.tire_percentage = max(self.tire_percentage, 1)
        self.target_speed = get_desired_speed_at_distance(
            self.distance % TOTAL_TRACK_LENGTH,
            DESIRED_SPEEDS_LIST,
            TOTAL_TRACK_LENGTH,
            self
        )
        self.target_speed *= (self.tire_percentage / 100)
        self.target_speed = max(self.target_speed, self.min_speed)
        effective_acceleration = self.base_acceleration * self.gearbox_quality
        if self.speed < self.target_speed:
            self.speed += effective_acceleration
            self.speed = min(self.speed, self.target_speed)
        elif self.speed > self.target_speed:
            speed_diff = self.speed - self.target_speed
            braking_force = (self.braking_intensity * speed_diff) * 0.1
            self.speed -= braking_force
            self.speed = max(self.speed, self.target_speed)
        max_speed = self.base_max_speed * (self.tire_percentage / 100)
        is_corner = self.is_in_corner()
        if is_corner:
            max_speed *= self.aero_efficiency
        else:
            max_speed *= self.engine_power
        max_speed = max(max_speed, self.min_max_speed)
        self.speed = min(self.speed, max_speed)
        self.speed = max(self.speed, self.min_speed)
        effective_acceleration = self.base_acceleration * self.gearbox_quality
        if self.speed < self.target_speed:
            self.speed += effective_acceleration
            self.speed = min(self.speed, self.target_speed)
        elif self.speed > self.target_speed:
            speed_diff = self.speed - self.target_speed
            braking_force = (self.braking_intensity * speed_diff) * 0.1
            self.speed -= braking_force
            self.speed = max(self.speed, self.target_speed)
        max_speed = self.base_max_speed * (self.tire_percentage / 100)
        is_corner = self.is_in_corner()
        if is_corner:
            max_speed *= self.aero_efficiency
        else:
            max_speed *= self.engine_power
        max_speed = max(max_speed, self.min_max_speed)
        self.speed = min(self.speed, max_speed)
        self.speed = max(self.speed, self.min_speed)
        self.distance += self.speed
        if self.on_out_lap or self.on_in_lap:
            self.speed = self.speed * 0.98
        self.distance %= TOTAL_TRACK_LENGTH
        self.update_adjusted_distance()

    # -------------------- Common Functions --------------------

    def crossed_start_finish_line(self):
        start_finish_distance = CUMULATIVE_DISTANCES[START_FINISH_INDEX_SMOOTHED]
        current_lap_distance = self.distance % TOTAL_TRACK_LENGTH
        previous_lap_distance = self.previous_distance % TOTAL_TRACK_LENGTH
        if previous_lap_distance <= start_finish_distance < current_lap_distance:
            return True
        elif current_lap_distance < previous_lap_distance:
            if previous_lap_distance <= start_finish_distance or start_finish_distance < current_lap_distance:
                return True
        return False

    def update_adjusted_distance(self):
        start_finish_distance = CUMULATIVE_DISTANCES[START_FINISH_INDEX_SMOOTHED]
        if self.on_pitlane:
            pitlane_fraction = self.pitlane_distance / PIT_LANE_TOTAL_LENGTH
            position = (PITLANE_ENTRANCE_DISTANCE + pitlane_fraction * (PITLANE_EXIT_DISTANCE - PITLANE_ENTRANCE_DISTANCE)) % TOTAL_TRACK_LENGTH
            current_distance = position
        else:
            current_distance = self.distance % TOTAL_TRACK_LENGTH
        self.adjusted_distance = (current_distance - start_finish_distance + TOTAL_TRACK_LENGTH) % TOTAL_TRACK_LENGTH
        self.adjusted_total_distance = self.laps_completed * TOTAL_TRACK_LENGTH + self.adjusted_distance

    def is_in_corner(self):
        current_lap_distance = self.distance % TOTAL_TRACK_LENGTH
        for i in range(len(DESIRED_SPEEDS_LIST) - 1):
            dist1, base_speed1 = DESIRED_SPEEDS_LIST[i]
            dist2, base_speed2 = DESIRED_SPEEDS_LIST[i + 1]
            if dist1 <= current_lap_distance <= dist2:
                avg_base_speed = (base_speed1 + base_speed2) / 2
                if avg_base_speed < self.base_max_speed * 0.9:
                    return True
                else:
                    return False
        return False

    def is_in_corner(self):
        current_lap_distance = self.distance % TOTAL_TRACK_LENGTH
        for i in range(len(DESIRED_SPEEDS_LIST) - 1):
            dist1, base_speed1 = DESIRED_SPEEDS_LIST[i]
            dist2, base_speed2 = DESIRED_SPEEDS_LIST[i + 1]
            if dist1 <= current_lap_distance <= dist2:
                avg_base_speed = (base_speed1 + base_speed2) / 2
                if avg_base_speed < self.base_max_speed * 0.9:
                    return True
                else:
                    return False
        return False

    def reset_after_safety_car(self):
        self.is_under_safety_car = False
        self.speed = SAFETY_CAR_SPEED
        self.has_caught_safety_car = False
        self.is_safety_car_ending = False

    def get_current_position(self):
        if self.on_pitlane:
            pitlane_fraction = self.pitlane_distance / PIT_LANE_TOTAL_LENGTH
            position = (PITLANE_ENTRANCE_DISTANCE + pitlane_fraction *
                        (PITLANE_EXIT_DISTANCE - PITLANE_ENTRANCE_DISTANCE)) % TOTAL_TRACK_LENGTH
        else:
            position = self.distance % TOTAL_TRACK_LENGTH
        return position

    def draw(self):
        if not self.is_active:
            return
        if self.on_pitlane:
            x, y = get_position_along_track(self.pitlane_distance, PIT_LANE_POINTS, PIT_LANE_CUMULATIVE_DISTANCES)
        else:
            x, y = get_position_along_track(self.distance, TRACK_POINTS, CUMULATIVE_DISTANCES)
        if self.mode == 'qualifying':
            pyxel.circ(x, y, 3, self.color)
        elif self.mode == 'race':
            if self.is_safety_car:
                pyxel.circ(x, y, 4, 0)
                pyxel.text(x - 3, y - 2, "SC", 1)
            else:
                pyxel.circ(x, y, 3, self.color)
