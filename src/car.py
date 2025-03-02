import random
import pyxel
import math
from constants import (
    TIRE_TYPES, PITLANE_SPEED_LIMIT,  OVERTAKE_CHANCE, CRASH_CHANCE,
    SAFETY_CAR_SPEED, SAFETY_CAR_GAP_DISTANCE, SAFETY_CAR_CATCH_UP_SPEED,
    PIT_STOP_THRESHOLD, PIT_STOP_DURATION, MAX_LAPS, DEBUG_MODE, SLIPSTREAM_DISTANCE, SLIPSTREAM_OVERTAKE_FRAMES, SLIPSTREAM_BASE_FRAMES,SLIPSTREAM_SPEED_BOOST,
    MISTAKE_CHANCE
)
from track import (
    get_desired_speed_at_distance, get_position_along_track,
    PIT_LANE_POINTS, PIT_LANE_CUMULATIVE_DISTANCES, TRACK_POINTS, PITLANE_ENTRANCE_DISTANCE,
    PITLANE_EXIT_DISTANCE, TOTAL_TRACK_LENGTH, DESIRED_SPEEDS_LIST,
    PIT_STOP_POINT, PIT_LANE_TOTAL_LENGTH, CUMULATIVE_DISTANCES,
    START_FINISH_INDEX_SMOOTHED,
)
from announcements import Announcements

class Car:
    def __init__(self, color_index, car_number, driver_name, grid_position,
                 announcements, pitbox_coords=PITLANE_ENTRANCE_DISTANCE,
                 pitbox_distance=PITLANE_EXIT_DISTANCE, game=None, mode='race', start_delay_frames=0):
        # Starting tire is set initially (will not be overwritten by a strategy plan)
        if grid_position < 10:
            self.tire_type = "soft"
        elif 10 <= grid_position < 15:
            self.tire_type = random.choice(["soft", "medium"])
        else:
            self.tire_type = "hard"  # or "medium-hard" if defined in TIRE_TYPES
        self.tire_percentage = 100.0
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
        self.engine_power = random.uniform(1.0, 1.0)
        # Store the base engine power separately so it can be reset each update.
        self.base_engine_power = self.engine_power
        self.aero_efficiency = random.uniform(1.2, 1.2)
        self.gearbox_quality = random.uniform(0.800, 0.800)
        self.suspension_quality = random.uniform(1.2, 1.2)
        self.brake_performance = random.uniform(210, 210)
        self.base_max_speed = 1.0
        self.base_acceleration = 0.007
        self.braking_intensity = 3.0 * self.brake_performance
        self.min_speed = 0.1
        self.min_max_speed = 0.2
        self.is_under_safety_car = False
        self.is_safety_car = False
        self.is_exiting = False
        self.has_caught_safety_car = False
        self.is_safety_car_ending = False
        self.slipstream_cooldown = 0

        # Fuel system
        self.base_weight = 800.0
        self.fuel_capacity = 100.0
        self.fuel_density = 0.75
        self.fuel_consumption_coefficient = 0.01
        self.fuel_consumption_multiplier = 1.0

        # Slipstream
        self.slipstream_timer = 0
        self.slipstream_target = None

        # Dynamic strategy: pitting flag and desire will be used later.
        self.pitting = False
        self.on_pitlane = False
        self.just_entered_pit = False
        self.just_changed_tires = False

        # Mode-based initialization
        if self.mode == 'qualifying':
            self.initialize_qualifying_mode()
            self.fuel_level = 40.0  # Use only minimal fuel in qualifying
        elif self.mode == 'race':
            self.initialize_race_mode()
            # Start with a full tank in race mode
            self.fuel_level = self.fuel_capacity

    def get_weight_factor(self):
        """
        Compute a multiplier based on the current total weight.
        A full tank gives a “nominal” weight; as fuel is burned, the car becomes lighter,
        so effective acceleration and top speed are slightly higher.
        """
        nominal_weight = self.base_weight + self.fuel_capacity * self.fuel_density
        current_weight = self.base_weight + self.fuel_level * self.fuel_density
        return nominal_weight / current_weight

    def calculate_pit_desire(self, safety_car_active):
        """
        Modified pit desire: start increasing pit desire once tire health falls below 90%.
        Ramps from 0.0 to 0.5 between 90% and 80%, then from 0.5 to 1.0 as health falls further.
        A bonus of 0.3 is added under safety car if the car hasn't caught up.
        """
        T = TIRE_TYPES[self.tire_type]["threshold"]

        if self.tire_percentage >= 90:
            base_desire = 0.0
        elif self.tire_percentage <= (T - 2):
            base_desire = 1.0
        else:
            # Linear interpolation: at tire_percentage==90 => 0; at tire_percentage==(T-2) => 1.
            base_desire = (90 - self.tire_percentage) / (90 - (T - 2))
        print(safety_car_active)
        if safety_car_active and self.speed != SAFETY_CAR_SPEED:
            base_desire = base_desire + 0.9
        return base_desire

    def update(self, race_started, current_frame, cars, safety_car_active):
        if not self.is_active:
            return
        if self.mode == 'qualifying':
            self.update_qualifying(cars)
        elif self.mode == 'race':
            self.update_race(race_started, current_frame, cars, safety_car_active)

    # --- NEW: Random Event Method ---
    def check_random_events(self):
        # Define the chance of events (adjust these values as desired)
        flatspot_chance = 0.0000005   # 0.5% chance per update
        mistake_chance = 0.00001     # 1% chance per update
        # Flatspot event: reduce tire health by a random percentage (5% to 15%)
        if random.random() < flatspot_chance:
            reduction = random.uniform(5, 15)
            self.tire_percentage = max(1, self.tire_percentage - reduction)
            self.announcements.add_message(
                f"Car {self.car_number} flatspotted its tires (-{reduction:.0f}%)!", duration=30
            )
        # Mistake event: reduce speed for this update (simulate lost time)
        if self.get_corner_type() != 'none':
            if random.random() < mistake_chance:
                slowdown_factor = random.uniform(0.2, 0.5)
                self.speed *= slowdown_factor
                self.announcements.add_message(
                    f"Car {self.car_number} made a mistake and lost speed!", duration=30
                )

    def initialize_race_mode(self):
        # Basic setup; grid-based tire choice is already set in __init__
        self.lap_start_frame = None
        self.just_crossed_start = False
        self.laps_completed = 0
        self.is_at_grid_position = True
        self.warmup_completed = False
        self.announced_on_grid = False
        self.crash_timer = 0

        self.start_delay_frames = 0
        self.warmup_started = False
        spacing_factor = 2.0
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

        # Plan the entire race so it always includes at least 1 pit stop & 2 compounds
        self.first_lap_completed = False

    def apply_slipstream(self, cars):
        # If the car is under cooldown, skip applying slipstream.
        if self.slipstream_cooldown > 0:
            return

        # Reset the flag at the beginning of the update cycle.
        self.slipstream_applied = False

        # Decrease slipstream timer if active.
        if self.slipstream_timer > 0:
            self.slipstream_timer -= 1
        else:
            self.slipstream_target = None

        if self.is_under_safety_car or not self.is_active:
            return

        best_distance = float('inf')
        best_car = None

        # Identify the nearest car ahead.
        for other_car in cars:
            if (other_car is not self and other_car.is_active and
                    not other_car.is_under_safety_car and not other_car.crashed):
                distance_diff = (other_car.distance - self.distance) % TOTAL_TRACK_LENGTH
                if 0 < distance_diff < best_distance:
                    best_distance = distance_diff
                    best_car = other_car

        effective_aero_efficiency = self.aero_efficiency

        if best_car and best_distance < SLIPSTREAM_DISTANCE:
            if self.slipstream_timer < SLIPSTREAM_BASE_FRAMES:
                self.slipstream_timer = SLIPSTREAM_BASE_FRAMES
                self.slipstream_target = best_car

            # Apply dirty air penalty if in a corner with a medium gap.
            DIRTY_AIR_LOWER_THRESHOLD = 2.0
            DIRTY_AIR_UPPER_THRESHOLD = 4.0
            DIRTY_AIR_PENALTY = 0.9

            corner_type = self.get_corner_type(offset=10.0)
            if corner_type in ("medium", "slow") and (
                    DIRTY_AIR_LOWER_THRESHOLD < best_distance < DIRTY_AIR_UPPER_THRESHOLD):
                effective_aero_efficiency *= DIRTY_AIR_PENALTY

        # Apply slipstream boost only once.
        if self.slipstream_timer > 0 and not self.slipstream_applied:
            min_speed = 0.3
            full_boost_speed = 0.8
            if self.speed < min_speed:
                boost_multiplier = 1.0
            else:
                t = (self.speed - min_speed) / (full_boost_speed - min_speed)
                t = max(0, min(1, t))
                boost_multiplier = 1.0 + t * (SLIPSTREAM_SPEED_BOOST - 1.0)
            self.engine_power *= boost_multiplier
            self.slipstream_applied = True


    # -------------------- HELPER METHODS --------------------
    def estimate_stint_time(self, laps_to_run, tire_key, start_tire_pct=100.0, strategy="normal"):
        base_lap_time = 50.0 / self.engine_power
        base_lap_time *= (1.0 / self.aero_efficiency)

        base_wear_rate = TIRE_TYPES[tire_key]["wear_rate"] / self.suspension_quality
        base_grip = TIRE_TYPES[tire_key]["initial_grip"]
        threshold = TIRE_TYPES[tire_key]["threshold"]

        if strategy == "aggressive":
            grip_factor = 1.15
            wear_factor = 1.2
        elif strategy == "cautious":
            grip_factor = 0.95
            wear_factor = 0.8
        else:
            grip_factor = 1.0
            wear_factor = 1.0

        wear_rate = base_wear_rate * wear_factor
        initial_grip = base_grip * grip_factor

        total_time = 0.0
        temp_tire_pct = start_tire_pct
        for _ in range(laps_to_run):
            degrade_factor = 1.0 + ((100.0 - temp_tire_pct) / 100.0) * 0.4
            if temp_tire_pct < threshold:
                degrade_factor *= 1.2
            lap_time = (base_lap_time / initial_grip) * degrade_factor
            total_time += lap_time
            temp_tire_pct -= wear_rate
            if temp_tire_pct < 1.0:
                temp_tire_pct = 1.0

        return total_time

    def laps_until_threshold(self, tire_key, start_tire_pct=100.0, strategy="normal"):
        base_wear_rate = TIRE_TYPES[tire_key]["wear_rate"] / self.suspension_quality
        if strategy == "aggressive":
            wear_factor = 1.2
        elif strategy == "cautious":
            wear_factor = 0.8
        else:
            wear_factor = 1.0

        wear_rate = base_wear_rate * wear_factor
        temp_pct = start_tire_pct
        laps = 0
        while temp_pct > PIT_STOP_THRESHOLD and laps < 999:
            temp_pct -= wear_rate
            laps += 1
            if temp_pct < 1.0:
                break
        return laps

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

        # ----- Fuel Consumption Update -----
        fuel_consumed = self.fuel_consumption_coefficient * self.speed * self.fuel_consumption_multiplier
        self.fuel_level = max(0, self.fuel_level - fuel_consumed)
        if self.fuel_level <= 0:
            self.fuel_level = 0
            self.announcements.add_message(f"Car {self.car_number} ran out of fuel!")
            self.crashed = True
            self.is_active = False
            return


        # Safety car special handling
        if self.is_safety_car:
            self.update_safety_car_behavior()
            return
        if not race_started or self.crashed:
            return

        self.previous_distance = self.distance
        self.previous_pitlane_distance = self.pitlane_distance
        if self.slipstream_cooldown > 0:
            self.slipstream_cooldown -= 1

        # ----- Tire Wear Update -----
        wear_rate = TIRE_TYPES[self.tire_type]["wear_rate"] / self.suspension_quality
        if self.tire_percentage < TIRE_TYPES[self.tire_type]["threshold"]:
            wear_rate *= 2
        self.tire_percentage = max(1, self.tire_percentage - wear_rate)
        self.tire_percentage = max(self.tire_percentage, 1)

        # Determine pit desire based solely on tire health (and safety car bonus)
        pit_desire = self.calculate_pit_desire(safety_car_active)
        if pit_desire >= 1.0:
            self.pitting = True
        self.engine_power = self.base_engine_power  # Reset engine power
        self.apply_slipstream(cars)
        self.attempt_overtake(cars, safety_car_active)

        if self.pitting and not self.on_pitlane:
            self.to_pitlane(current_frame)
        elif self.on_pitlane:
            self.in_pitlane(current_frame)
        else:
            # Get the ideal target speed based on track position.
            base_target_speed = get_desired_speed_at_distance(
                self.distance % TOTAL_TRACK_LENGTH,
                DESIRED_SPEEDS_LIST,
                TOTAL_TRACK_LENGTH,
                self
            )
            # --- New Tire Effect Logic ---
            # Instead of directly scaling by self.tire_percentage/100,
            # we compute a tire factor that is only mildly penalizing when the tire health is above the threshold.
            tire_threshold = TIRE_TYPES[self.tire_type]["threshold"]
            if self.tire_percentage >= tire_threshold:
                tire_factor = 0.98 + 0.02 * ((self.tire_percentage - tire_threshold) / (100 - tire_threshold))
            elif self.tire_percentage >= tire_threshold - 5:
                tire_factor = 0.95 + ((self.tire_percentage - (tire_threshold - 5)) / 5) * (0.98 - 0.95)
            else:
                tire_factor = 0.50 + (self.tire_percentage / (tire_threshold - 5)) * (0.95 - 0.50)
            self.target_speed = base_target_speed * tire_factor
            self.target_speed = max(self.target_speed, self.min_speed)

        # ----- Weight-Adjusted Acceleration and Speed Adjustments -----
        weight_factor = self.get_weight_factor()
        effective_acceleration = self.base_acceleration * self.gearbox_quality * weight_factor

        corner_type = self.get_corner_type(offset=10.0)
        if corner_type == "slow":
            multiplier = (self.brake_performance / 210.0) * self.suspension_quality
        elif corner_type == "medium":
            multiplier = (self.aero_efficiency + (self.brake_performance / 210.0)) / 2.0
        elif corner_type == "fast":
            multiplier = self.aero_efficiency + self.engine_power
        else:
            multiplier = self.engine_power * 1.5

        max_speed = self.base_max_speed * (self.tire_percentage / 100) * weight_factor
        max_speed *= multiplier
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

        max_speed = self.base_max_speed * (self.tire_percentage / 100) * weight_factor
        max_speed *= multiplier
        max_speed = max(max_speed, self.min_max_speed)
        self.speed = min(self.speed, max_speed)
        self.speed = max(self.speed, self.min_speed)
        if not self.on_pitlane and not safety_car_active:
            self.check_random_events()

        # ----- Update Position and Lap Count -----
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

            #if DEBUG_MODE:
              #  print(
              #      f"Car {self.car_number} - Lap: {self.laps_completed} |"
              #      f" Tire: {self.tire_type.capitalize()} Fuel: {self.fuel_level:.1f}L"
              #      f" {self.tire_percentage:.1f}% | Speed: {self.speed:.2f}"
              #  )

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
        if not self.pit_stop_done:
            # Accelerate along pitlane until pitbox
            self.previous_pitlane_distance = self.pitlane_distance
            self.speed = min(self.speed + self.base_acceleration, PITLANE_SPEED_LIMIT)
            self.pitlane_distance += self.speed

            if self.previous_pitlane_distance <= self.pitbox_distance < self.pitlane_distance:
                self.speed = 0.0
                self.pitlane_distance = self.pitbox_distance
                self.pit_stop_timer += 1

                if self.pit_stop_timer >= PIT_STOP_DURATION:
                    self.pit_stop_done = True
                    self.pit_stop_timer = 0
                    # ----- Refuel During Pit Stop -----
                    self.fuel_level = self.fuel_capacity
                    self.announcements.add_message(f"Car {self.car_number} refueled!")
                    # After pitting, choose a random tire compound and reset tire health.
                    self.tire_type = random.choice(list(TIRE_TYPES.keys()))
                    self.tire_percentage = 100.0
                    self.just_changed_tires = True
        else:
            # After pit stop, accelerate to exit
            self.previous_pitlane_distance = self.pitlane_distance
            self.speed = min(self.speed + self.base_acceleration, PITLANE_SPEED_LIMIT)
            self.pitlane_distance += self.speed
            if self.pitlane_distance >= PIT_LANE_TOTAL_LENGTH:
                self.on_pitlane = False
                self.pitting = False
                self.pit_stop_done = False
                self.pitlane_distance = 0.0
                self.speed = PITLANE_SPEED_LIMIT
                self.distance = PITLANE_EXIT_DISTANCE

    def update_safety_car_behavior(self):
        self.previous_distance = self.distance
        if self.is_exiting and self.is_safety_car:
            #print(self.car_number)
            self.speed += self.base_acceleration * 0.5
            self.speed = min(self.speed, SAFETY_CAR_SPEED * 2)
            self.distance += self.speed
            self.distance %= TOTAL_TRACK_LENGTH
            if (self.distance >= PITLANE_ENTRANCE_DISTANCE and self.previous_distance < PITLANE_ENTRANCE_DISTANCE):
                self.is_active = False
        else:
            self.distance += self.speed
            self.distance %= TOTAL_TRACK_LENGTH

    def update_under_safety_car(self, current_frame, safety_car, cars, car_ahead=None):
        if self.crashed or not self.is_active:
            return
        pit_desire = self.calculate_pit_desire(True)
        if pit_desire >= 1.0:
            self.pitting = True
        if self.pitting and not self.on_pitlane:
            self.to_pitlane(current_frame)
        if self.on_pitlane:
            self.in_pitlane(current_frame)
            print(f"in pitlane", self.car_number, self.speed)
            return
        self.attempt_overtake(cars, True)
        self.previous_distance = self.distance
        desired_gap = SAFETY_CAR_GAP_DISTANCE
        if self.is_safety_car_ending and not self.is_safety_car:
            self.speed = SAFETY_CAR_SPEED * 1.2
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
        for other_car in cars:
            if other_car.car_number == self.car_number or other_car.crashed or not other_car.is_active:
                continue

            # If a safety car is active and the candidate car is not in the pitlane, skip overtaking.
            if safety_car_active and not other_car.on_pitlane:
                continue

            distance_diff = (other_car.distance - self.distance) % TOTAL_TRACK_LENGTH
            if 0 < distance_diff < 5:
                # If the car ahead is in the pitlane, increase the chance to overtake.
                if other_car.on_pitlane and self.calculate_pit_desire(safety_car_active) < 1:
                    self.distance = self.distance + 0.1
                else:
                    if random.random() < OVERTAKE_CHANCE:
                        self.distance = (other_car.distance + 1) % TOTAL_TRACK_LENGTH
                        other_car.slipstream_cooldown = 60
                    else:
                        if random.random() < CRASH_CHANCE:
                            self.crashed = True
                            self.speed = 0.0
                            self.is_active = False
                            self.announcements.add_message(f"Car {self.car_number} has crashed!")
                            break
                        if random.random() < MISTAKE_CHANCE:
                            self.speed *= 0.9
                            self.announcements.add_message(
                                f"Car {self.car_number} made a mistake and lost speed!"
                            )

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

    def update_qualifying(self, cars):
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
                self.update_movement(cars)
                if self.crossed_start_finish_line():
                    self.on_out_lap = False
                    self.on_fast_lap = True
                    self.current_lap_start_frame = self.game.qualifying.elapsed_time
        elif self.on_fast_lap:
            self.previous_distance = self.distance
            self.update_movement(cars)
            if self.crossed_start_finish_line():
                lap_time = (self.game.qualifying.elapsed_time - self.current_lap_start_frame) / 30.0
                self.lap_times.append(lap_time)
                if self.best_lap_time is None or lap_time < self.best_lap_time:
                    self.best_lap_time = lap_time
                self.on_fast_lap = False
                self.on_in_lap = True
        elif self.on_in_lap:
            self.previous_distance = self.distance
            self.update_movement(cars)
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

    def update_movement(self, cars):
        # ----- Fuel Consumption for Qualifying -----
        if self.slipstream_cooldown > 0:
            self.slipstream_cooldown -= 1
        fuel_consumed = self.fuel_consumption_coefficient * self.speed * self.fuel_consumption_multiplier
        self.fuel_level = max(0, self.fuel_level - fuel_consumed)
        if self.fuel_level <= 0:
            self.fuel_level = 0
            self.crashed = True
            return
        wear_rate = TIRE_TYPES[self.tire_type]["wear_rate"] / self.suspension_quality
        if self.tire_percentage < TIRE_TYPES[self.tire_type]["threshold"]:
            wear_rate *= 2
        self.tire_percentage = max(1, self.tire_percentage - wear_rate)
        self.tire_percentage = max(self.tire_percentage, 1)

        base_target_speed = get_desired_speed_at_distance(
            self.distance % TOTAL_TRACK_LENGTH,
            DESIRED_SPEEDS_LIST,
            TOTAL_TRACK_LENGTH,
            self
        )
        # --- New Tire Effect Logic for Qualifying ---
        tire_threshold = TIRE_TYPES[self.tire_type]["threshold"]
        if self.tire_percentage >= tire_threshold:
            tire_factor = 0.98 + 0.02 * ((self.tire_percentage - tire_threshold) / (100 - tire_threshold))
        elif self.tire_percentage >= tire_threshold - 5:
            tire_factor = 0.95 + ((self.tire_percentage - (tire_threshold - 5)) / 5) * (0.98 - 0.95)
        else:
            tire_factor = 0.50 + (self.tire_percentage / (tire_threshold - 5)) * (0.95 - 0.50)
        self.target_speed = base_target_speed * tire_factor
        self.target_speed = max(self.target_speed, self.min_speed)

        weight_factor = self.get_weight_factor()
        effective_acceleration = self.base_acceleration * self.gearbox_quality * weight_factor
        if self.speed < self.target_speed:
            self.speed += effective_acceleration
            self.speed = min(self.speed, self.target_speed)
        elif self.speed > self.target_speed:
            speed_diff = self.speed - self.target_speed
            braking_force = (self.braking_intensity * speed_diff) * 0.1
            self.speed -= braking_force
            self.speed = max(self.speed, self.target_speed)

        # --- New corner-based adjustment (unchanged) ---
        corner_type = self.get_corner_type(offset=10.0, threshold_degrees=15)
        if corner_type == "slow":
            multiplier = (self.brake_performance / 210.0) * self.suspension_quality
        elif corner_type == "medium":
            multiplier = (self.aero_efficiency + (self.brake_performance / 210.0)) / 2.0
        elif corner_type == "fast":
            multiplier = self.aero_efficiency
        else:
            multiplier = self.engine_power

        max_speed = self.base_max_speed * (self.tire_percentage / 100) * weight_factor
        max_speed *= multiplier
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

        max_speed = self.base_max_speed * (self.tire_percentage / 100) * weight_factor
        max_speed *= multiplier
        max_speed = max(max_speed, self.min_max_speed)
        self.speed = min(self.speed, max_speed)
        self.speed = max(self.speed, self.min_speed)
        self.distance += self.speed

        self.check_random_events()

        self.apply_slipstream(cars)
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
            position = (
                               PITLANE_ENTRANCE_DISTANCE
                               + pitlane_fraction * (PITLANE_EXIT_DISTANCE - PITLANE_ENTRANCE_DISTANCE)
                       ) % TOTAL_TRACK_LENGTH
        else:
            position = self.distance % TOTAL_TRACK_LENGTH

        self.adjusted_distance = (
                                         position - start_finish_distance + TOTAL_TRACK_LENGTH
                                 ) % TOTAL_TRACK_LENGTH
        self.adjusted_total_distance = self.laps_completed * TOTAL_TRACK_LENGTH + self.adjusted_distance
        #if DEBUG_MODE:
            #print(
            #    f"DEBUG: Car {self.car_number} - Laps: {self.laps_completed}, raw distance: {self.distance:.2f}, adjusted distance: {self.adjusted_distance:.2f}, total adjusted: {self.adjusted_total_distance:.2f}")

    def get_corner_type(self, offset=5.0, threshold_degrees=15):
        """
        Determines the type of corner based on the local turning angle.
        Returns:
          - "none" if nearly straight,
          - "fast" for slight curves (primarily aero-driven),
          - "medium" for moderate curves (mix of braking and aero),
          - "slow" for sharp turns (heavily influenced by braking and suspension).
        """
        current_pos = get_position_along_track(self.distance, TRACK_POINTS, CUMULATIVE_DISTANCES)
        prev_pos = get_position_along_track(self.distance - offset, TRACK_POINTS, CUMULATIVE_DISTANCES)
        next_pos = get_position_along_track(self.distance + offset, TRACK_POINTS, CUMULATIVE_DISTANCES)

        # Compute vectors from the previous to current, and current to next.
        vec1 = (current_pos[0] - prev_pos[0], current_pos[1] - prev_pos[1])
        vec2 = (next_pos[0] - current_pos[0], next_pos[1] - current_pos[1])

        # Calculate the magnitudes
        mag1 = math.hypot(*vec1)
        mag2 = math.hypot(*vec2)

        # Protect against division by zero
        if mag1 == 0 or mag2 == 0:
            return "none"
        dot = vec1[0] * vec2[0] + vec1[1] * vec2[1]
        cos_theta = dot / (mag1 * mag2)
        # Clamp cos_theta to valid range for acos.
        cos_theta = max(-1.0, min(1.0, cos_theta))
        angle = math.acos(cos_theta)
        angle_deg = math.degrees(angle)
        if angle_deg < 1:
            if self.driver_name == "Marco Bellini":
                print('none')
            return "none"
        elif angle_deg < 4:
            if self.driver_name == "Marco Bellini":
                print('fast')
            return "fast"
        elif angle_deg < 13:
            if self.driver_name == "Marco Bellini":
                print('medium')
            return "medium"
        else:
            if self.driver_name == "Marco Bellini":
                print('slow')
                print(angle_deg)
            return "slow"

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