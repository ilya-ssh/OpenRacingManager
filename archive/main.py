import pyxel
import json
import random
from pyxelunicode import PyxelUnicode

# Debug mode toggle
DEBUG_MODE = True

# Load track data from a JSON file
def load_track(file_path):
    with open(file_path, 'r') as file:
        track_data = json.load(file)
    points = track_data['points']
    start_finish_index = track_data.get('start_finish_index', 0)
    return points, start_finish_index

# Load track points and start/finish index
TRACK_POINTS, START_FINISH_INDEX = load_track('track.json')

# Set maximum laps for the race
MAX_LAPS = 2

# Tire types and their properties
TIRE_TYPES = {
    "hard": {"wear_rate": 0.005, "initial_grip": 0.9, "threshold": 25},
    "medium": {"wear_rate": 0.01, "initial_grip": 1.0, "threshold": 35},
    "soft": {"wear_rate": 0.015, "initial_grip": 1.1, "threshold": 50}
}

# Car class
class Car:
    def __init__(self, color_index, car_number, grid_position):
        self.color = color_index
        self.car_number = car_number
        # Position each car slightly behind the start/finish line with a minimal stagger for grid positions
        self.position = START_FINISH_INDEX - (0.5 + grid_position * 0.01)  # Offset to start behind the line
        self.tire_type = random.choice(list(TIRE_TYPES.keys()))
        self.tire_percentage = 100.0  # Start with full tire percentage
        self.max_speed = 0.02 * TIRE_TYPES[self.tire_type]["initial_grip"]
        self.base_max_speed = self.max_speed  # Save base max speed for tire blowout effect
        self.speed = 0
        self.base_acceleration = 0.0003  # Base acceleration
        self.braking_intensity = 0.95  # Smoother braking intensity
        self.laps_completed = -1  # Start laps at -1, so crossing the line sets it to 0
        self.previous_index = int(self.position)  # Track previous point index for lap counting

    def update(self, race_started):
        if not race_started:
            return  # Don't update the car if race hasn't started

        index = int(self.position) % len(TRACK_POINTS)
        
        # Calculate dynamic acceleration adjusted by tire wear
        tire_grip = TIRE_TYPES[self.tire_type]["initial_grip"] * (self.tire_percentage / 100)
        dynamic_acceleration = self.base_acceleration * (1 - (self.speed / self.max_speed)) * tire_grip
        adjusted_braking = self.braking_intensity * (self.tire_percentage / 100)

        # Apply dynamic acceleration
        if self.speed < self.max_speed:
            self.speed += dynamic_acceleration
        else:
            self.speed = self.max_speed

        # Apply braking if needed
        self.speed = braking_curve(self.speed, self.max_speed * 0.8, adjusted_braking)

        # Move the car forward along the track based on its speed
        self.position += self.speed

        # Adjust wear rate based on tire percentage thresholds
        wear_rate = TIRE_TYPES[self.tire_type]["wear_rate"]
        if self.tire_percentage < TIRE_TYPES[self.tire_type]["threshold"]:
            wear_rate *= 2  # Increase wear rate if below the threshold

        # Apply constant tire wear
        self.tire_percentage = max(0, self.tire_percentage - wear_rate)

        # Additional tire wear in turns
        if index % 10 == 0:  # Assuming every 10th point represents a turn
            self.tire_percentage = max(0, self.tire_percentage - wear_rate * 2)

        # Simulate tire blowout if tire percentage is below 5%
        if self.tire_percentage < 5:
            self.max_speed = 0.005  # Drastically reduce max speed for blown tire

        # Check if the car crossed the start/finish line
        if self.previous_index < START_FINISH_INDEX <= index:
            # Increment lap count once the car has crossed the line
            self.laps_completed += 1

        # Debug info output
        if DEBUG_MODE:
            print(f"Car {self.car_number} - Lap: {self.laps_completed} | Tire: {self.tire_type.capitalize()} "
                  f"{self.tire_percentage:.1f}% | Speed: {self.speed:.4f} | Accel: {dynamic_acceleration:.5f} | "
                  f"Brake: {adjusted_braking:.5f} | Max Speed: {self.max_speed:.4f}")

        # Update previous index for lap counting
        self.previous_index = index

    def draw(self):
        # Determine the current position for smooth movement
        index = int(self.position) % len(TRACK_POINTS)
        next_index = (index + 1) % len(TRACK_POINTS)
        t = self.position - int(self.position)

        x1, y1 = TRACK_POINTS[index]
        x2, y2 = TRACK_POINTS[next_index]

        # Interpolate position between points for smooth movement
        x = x1 + (x2 - x1) * t
        y = y1 + (y2 - y1) * t

        pyxel.circ(x, y, 3, self.color)

    def get_current_time(self):
        return self.laps_completed + (self.position / len(TRACK_POINTS))

# Define the custom braking function for smoother deceleration
def braking_curve(current_speed, target_speed, deceleration_factor=0.95):
    """Applies a deceleration factor to reduce the car's speed smoothly."""
    return max(target_speed, current_speed * deceleration_factor)

# Game class
class Game:
    def __init__(self):
        pyxel.init(400, 400)  # Higher resolution screen for larger font size
        
        # Define colors in the palette
        pyxel.colors[0] = 0xFFFFFFFF  # Pure white for track and text

        # Define a list of hex colors for the cars
        car_hex_colors = [
            0xFF0000, 0x00FF00, 0x0000FF, 0xFFFF00,
            0xFF00FF, 0x00FFFF, 0x800000, 0x008000, 0x000080, 0x808000, 0x000000
        ]
        
        # Randomize car grid positions
        grid_positions = list(range(10))
        random.shuffle(grid_positions)

        for i, hex_color in enumerate(car_hex_colors, start=1):
            pyxel.colors[i] = hex_color
        
        # Create cars with minimal staggered positions on the grid
        self.cars = [Car((i % len(car_hex_colors)) + 1, i + 1, grid_positions[i]) for i in range(10)]
        
        # Countdown timer for race start
        self.countdown = 180  # 180 frames = 3 seconds at 60 FPS
        self.race_started = False
        self.race_finished = False

        # Initialize PyxelUnicode for larger font display
        font_path = "PublicPixel.ttf"  # Replace with the path to your font file
        font_size = 8
        self.pyuni = PyxelUnicode(font_path, font_size)

        pyxel.run(self.update, self.draw)
    
    def update(self):
        # Countdown logic
        if self.countdown > 0:
            self.countdown -= 1
        else:
            self.race_started = True  # Start the race once countdown finishes

        if self.race_started and not self.race_finished:
            for car in self.cars:
                car.update(self.race_started)

            # Sort cars for the leaderboard
            self.cars.sort(key=lambda car: (-car.laps_completed, -car.position))

            # Check if the race is finished
            if any(car.laps_completed >= MAX_LAPS for car in self.cars):
                self.race_finished = True

    def draw(self):
        pyxel.cls(11)
    
        # Draw track segments in pure white
        for i in range(len(TRACK_POINTS)):
            x1, y1 = TRACK_POINTS[i]
            x2, y2 = TRACK_POINTS[(i + 1) % len(TRACK_POINTS)]
            pyxel.line(x1, y1, x2, y2, 0)  # Using color index 0 for pure white

        # Draw start/finish line as a red line between start/finish point and the next point
        sx, sy = TRACK_POINTS[START_FINISH_INDEX]
        sx_next, sy_next = TRACK_POINTS[(START_FINISH_INDEX + 1) % len(TRACK_POINTS)]
        pyxel.line(sx, sy, sx_next, sy_next, pyxel.COLOR_RED)

        # Draw cars
        for car in self.cars:
            car.draw()
        
        # Draw leaderboard with tire information
        x_offset = 20
        y_offset = 20
        self.pyuni.text(x_offset, y_offset, "Leaderboard:", 0)  # Using color index 0 for pure white
        
        for idx, car in enumerate(self.cars[:10]):
            gap = 0.0 if idx == 0 else (self.cars[idx - 1].get_current_time() - car.get_current_time()) * 10
            tire_text = f"{idx+1}. Car {car.car_number} - {car.tire_type.capitalize()} {car.tire_percentage:.1f}% - Gap: {gap:.2f}s"
            self.pyuni.text(x_offset, y_offset + (self.pyuni.font_height + 5) * (idx + 1), tire_text, car.color)

        # Display "Race Finished!" message in pure white if race is finished
        if self.race_finished:
            self.pyuni.text(200, 300, "Race Finished!", 0)

        # Countdown display
        if self.countdown > 0:
            countdown_text = str((self.countdown // 60) + 1)  # Display countdown in seconds
            self.pyuni.text(250, 300, countdown_text, pyxel.COLOR_YELLOW)

# Run the game
Game()
