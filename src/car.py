import random
import pyxel
from constants import (
    TIRE_TYPES, PITLANE_SPEED_LIMIT,  OVERTAKE_CHANCE, CRASH_CHANCE,
    SAFETY_CAR_SPEED, SAFETY_CAR_GAP_DISTANCE, SAFETY_CAR_CATCH_UP_SPEED,
    PIT_STOP_THRESHOLD, PIT_STOP_DURATION, MAX_LAPS, DEBUG_MODE, SLIPSTREAM_DISTANCE, SLIPSTREAM_OVERTAKE_FRAMES, SLIPSTREAM_BASE_FRAMES,SLIPSTREAM_SPEED_BOOST
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
                 announcements, pitbox_coords=PITLANE_ENTRANCE_DISTANCE, pitbox_distance=PITLANE_EXIT_DISTANCE, game=None, mode='race', start_delay_frames=0):
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
        self.engine_power = random.uniform(1.0, 1.2)
        self.aero_efficiency = random.uniform(1.0, 1.2)
        self.gearbox_quality = random.uniform(1.0, 1.2)
        self.suspension_quality = random.uniform(0.8, 1.2)
        self.brake_performance = random.uniform(1.0, 1.2)
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

        # Fuel system
        self.base_weight = 800.0
        self.fuel_capacity = 100.0
        self.fuel_density = 0.75
        self.fuel_consumption_coefficient = 0.01
        self.fuel_consumption_multiplier = 1.0

        # Slipstream
        self.slipstream_timer = 0
        self.slipstream_target = None

        # Mode-based init
        if self.mode == 'qualifying':
            self.initialize_qualifying_mode()
            # Use only the minimum fuel needed for a flying lap
            self.fuel_level = 40.0  # liters – tweak this value as needed
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

    def update(self, race_started, current_frame, cars, safety_car_active):
        if not self.is_active:
            return
        if self.mode == 'qualifying':
            self.update_qualifying(cars)
        elif self.mode == 'race':
            self.update_race(race_started, current_frame, cars, safety_car_active)

    # -------------------- Race Functions --------------------

    def initialize_race_mode(self):
        # -------------------------
        # Basic setup (unchanged)
        # -------------------------
        strategies = ["aggressive", "normal", "cautious"]
        self.strategy_type = random.choice(strategies)
        self.just_crossed_pitstop_point = False
        self.lap_start_frame = None
        self.just_crossed_start = False
        self.laps_completed = 0
        self.is_at_grid_position = True
        self.warmup_completed = False
        self.announced_on_grid = False
        self.crash_timer = 0

        self.start_delay_frames = 0
        self.warmup_started = False
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

        # Plan the entire race so it always includes at least 1 pit stop & 2 compounds
        laps_remaining = MAX_LAPS
        best_time, strategy_plan = self.plan_optimal_strategy(
            laps_left=laps_remaining,
            start_tire_pct=100.0,
            strategy=self.strategy_type,
            used_compounds=set(),  # none used at the start
            pitstops=0
        )

        # If for some reason no plan found => fallback
        if best_time == float('inf') or not strategy_plan:
            # fallback: 2-stint forced
            strategy_plan = [
                {"tire": "soft", "laps": laps_remaining // 2},
                {"tire": "medium", "laps": laps_remaining - laps_remaining // 2},
            ]

        # The first stint's tire determines initial tire
        first_tire = strategy_plan[0]["tire"]
        self.tire_type = first_tire
        self.tire_percentage = 100.0

        self.first_lap_completed = False

    def apply_slipstream(self, cars):
        """
        Checks if we're close behind another car and applies a slipstream boost if so.
        If we overtake that car, we keep the boost for additional frames.
        """
        # If we already have some slipstream time, count it down
        if self.slipstream_timer > 0:
            self.slipstream_timer -= 1
        else:
            self.slipstream_target = None  # no active slipstream once timer hits 0

        # If we are under safety car or not active, no slipstream
        if self.is_under_safety_car or not self.is_active:
            return

        # 1) Identify the nearest active car in front (distance_diff in (0, SLIPSTREAM_DISTANCE))
        #    We'll keep track of the smallest positive distance
        best_distance = float('inf')
        best_car = None

        for other_car in cars:
            if (
                    other_car is not self
                    and other_car.is_active
                    and not other_car.is_under_safety_car
                    and not other_car.crashed
            ):
                distance_diff = (other_car.distance - self.distance) % TOTAL_TRACK_LENGTH

                # This means other_car is ahead if distance_diff > 0
                if 0 < distance_diff < best_distance:
                    best_distance = distance_diff
                    best_car = other_car

        # 2) Check if we are within slipstream distance to that "best_car"
        if best_car and best_distance < SLIPSTREAM_DISTANCE:
            # We are in the slipstream zone!
            # Refresh the timer to at least SLIPSTREAM_BASE_FRAMES
            if self.slipstream_timer < SLIPSTREAM_BASE_FRAMES:
                self.slipstream_timer = SLIPSTREAM_BASE_FRAMES
                self.slipstream_target = best_car
        else:
            # No slipstream if we haven't already got some leftover slipstream timer
            # (But we won't forcibly kill slipstream_timer if we previously had it)
            pass

        # 3) If we do have an active slipstream target, check for overtake:
        if self.slipstream_target:
            distance_to_target = (self.slipstream_target.distance - self.distance) % TOTAL_TRACK_LENGTH
            # If we pass them (distance_to_target becomes negative or 0), keep slipstream for extra frames
            if distance_to_target <= 0:
                # e.g. set slipstream_timer to a guaranteed minimum
                if self.slipstream_timer < SLIPSTREAM_OVERTAKE_FRAMES:
                    self.slipstream_timer = SLIPSTREAM_OVERTAKE_FRAMES

        # 4) Finally, if slipstream_timer > 0, apply the speed boost
        #    One easy way is simply to multiply your speed by SLIPSTREAM_SPEED_BOOST
        if self.slipstream_timer > 0:
            # You could either multiply your final speed or multiply target_speed or acceleration
            # For example, multiply acceleration:
            self.speed *= SLIPSTREAM_SPEED_BOOST

    def plan_optimal_strategy(
            self,
            laps_left,
            start_tire_pct=100.0,
            strategy="normal",
            used_compounds=None,
            pitstops=0,
            memo=None
    ):
        """
        Returns (best_time, plan) for running `laps_left` starting from
        `start_tire_pct` tire condition, must have >=1 pitstop & >=2 compounds.

        Constraints:
          - At least 1 pit stop total
          - At least 2 different tire compounds used
        """
        if used_compounds is None:
            used_compounds = set()
        if memo is None:
            memo = {}

        # If we’ve completed all laps, check constraints
        if laps_left <= 0:
            # Must have >=1 pitstop & >=2 compounds
            if pitstops >= 1 and len(used_compounds) >= 2:
                return (0.0, [])
            else:
                return (float('inf'), [])

        # Memo key
        memo_key = (laps_left, round(start_tire_pct, 1), strategy, frozenset(used_compounds), pitstops)
        if memo_key in memo:
            return memo[memo_key]

        best_time = float('inf')
        best_plan = []

        # Pit-lane travel + stationary
        pit_lane_travel_time = (PIT_LANE_TOTAL_LENGTH / PITLANE_SPEED_LIMIT)
        stationary_pit_time = PIT_STOP_DURATION / 30.0
        total_pit_time_penalty = pit_lane_travel_time + stationary_pit_time

        # Try each tire compound
        for tire_key in TIRE_TYPES:
            # This stint starts on tire_key; add it to used_compounds
            new_used_compounds = used_compounds | {tire_key}

            # How many laps can we safely run on this tire before dropping under threshold
            safe_laps = self.laps_until_threshold(tire_key, start_tire_pct, strategy=strategy)
            if safe_laps <= 0:
                continue

            # If we can finish the race on this tire (safe_laps >= laps_left)
            # then we see if that solution meets constraints
            if safe_laps >= laps_left:
                # We do these laps *without another pit stop*
                stint_time = self.estimate_stint_time(laps_left, tire_key, start_tire_pct, strategy)

                # After finishing, see if we meet constraints:
                # pitstops remains the same, used_compounds is new_used_compounds
                # Only if pitstops >=1 and len(...) >=2 do we consider it valid.
                # But we must actually check at the base case, so let’s call a sub-check:
                # We'll effectively do laps_left => 0, so we check the base condition:
                # We'll do a small "fake" recursion with laps_left-laps_left=0
                # BUT we can short-circuit: if we don't meet constraints, it’s infinite.
                final_pitstops = pitstops
                final_used = new_used_compounds
                if final_pitstops >= 1 and len(final_used) >= 2:
                    if stint_time < best_time:
                        best_time = stint_time
                        best_plan = [{"tire": tire_key, "laps": laps_left}]
            else:
                # We can't finish the race on this stint alone; we must pit afterwards
                # 1) Time to do 'safe_laps' on this tire
                stint_time = self.estimate_stint_time(safe_laps, tire_key, start_tire_pct, strategy)

                # 2) Then pit => next stint starts at 100% tire
                next_time, next_plan = self.plan_optimal_strategy(
                    laps_left - safe_laps,
                    100.0,
                    strategy,
                    new_used_compounds,
                    pitstops + 1,  # we made a pit stop
                    memo
                )

                total_time_here = stint_time + total_pit_time_penalty + next_time
                if total_time_here < best_time:
                    best_time = total_time_here
                    best_plan = [{"tire": tire_key, "laps": safe_laps}] + next_plan

        memo[memo_key] = (best_time, best_plan)
        return memo[memo_key]

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
            self.apply_slipstream(cars)
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

            # ----- Weight-Adjusted Acceleration -----
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

            max_speed = self.base_max_speed * (self.tire_percentage / 100) * weight_factor
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
                print(
                    f"Car {self.car_number} - Lap: {self.laps_completed} |"
                    f" Tire: {self.tire_type.capitalize()} Fuel: {self.fuel_level:.1f}L"
                    f" {self.tire_percentage:.1f}% | Speed: {self.speed:.2f}"
                )

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
                    # Recompute strategy for remaining laps, with our strategy type
                    laps_remaining = MAX_LAPS - self.laps_completed
                    best_time, strategy_plan = self.plan_optimal_strategy(
                        laps_left=laps_remaining,
                        start_tire_pct=100.0,
                        strategy=self.strategy_type,
                        used_compounds=set(),  # new strategy from here on
                        pitstops=1  # we've definitely made at least one pit now
                    )
                    if strategy_plan:
                        next_tire = strategy_plan[0]["tire"]
                        self.tire_type = next_tire
                        self.tire_percentage = 100.0
                        self.just_changed_tires = True
                    else:
                        # fallback
                        self.tire_type = random.choice(list(TIRE_TYPES.keys()))
                        self.tire_percentage = 100.0

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
        self.target_speed = get_desired_speed_at_distance(
            self.distance % TOTAL_TRACK_LENGTH,
            DESIRED_SPEEDS_LIST,
            TOTAL_TRACK_LENGTH,
            self
        )
        self.target_speed *= (self.tire_percentage / 100)
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
        max_speed = self.base_max_speed * (self.tire_percentage / 100) * weight_factor
        is_corner = self.is_in_corner()
        if is_corner:
            max_speed *= self.aero_efficiency
        else:
            max_speed *= self.engine_power
        max_speed = max(max_speed, self.min_max_speed)
        self.speed = min(self.speed, max_speed)
        self.speed = max(self.speed, self.min_speed)
        self.distance += self.speed

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
        if DEBUG_MODE:
            print(
                f"DEBUG: Car {self.car_number} - Laps: {self.laps_completed}, raw distance: {self.distance:.2f}, adjusted distance: {self.adjusted_distance:.2f}, total adjusted: {self.adjusted_total_distance:.2f}")

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
