import pyxel
import json
import math
import numpy as np
from scipy.interpolate import splprep, splev

class TrackBuilder:
    def __init__(self):
        pyxel.init(500, 500)
        self.points = []
        self.looped = False  
        self.start_finish_index = None  
        self.max_laps = 10  
        self.action_history = []  
        self.show_smoothed = True 
        pyxel.mouse(True)
        pyxel.run(self.update, self.draw)

    def save_track(self):
        # Remove the last point if it’s the same as the first to avoid duplication
        if self.points and self.points[-1] == self.points[0]:
            points_to_save = self.points[:-1]
        else:
            points_to_save = self.points

        # Prepare data to save, including the start/finish index and max laps
        track_data = {
            "points": points_to_save,
            "start_finish_index": self.start_finish_index,
            "max_laps": self.max_laps
        }
        with open("track.json", "w") as file:
            json.dump(track_data, file, indent=4)
        print("Track saved to track.json")

    def update(self):

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and not self.looped:
            x, y = pyxel.mouse_x, pyxel.mouse_y
            self.points.append((x, y))
            # Record the action
            self.action_history.append(('add_point', (x, y)))
            print(f"Added point {x}, {y}")


        if pyxel.btnp(pyxel.KEY_L) and len(self.points) > 1 and not self.looped:
            self.points.append(self.points[0])  # Connect to the starting point
            self.looped = True
            # Record the action
            self.action_history.append(('loop_track', None))
            print("Track looped back to the start.")


        if pyxel.btnp(pyxel.KEY_F) and self.looped:
            # Store previous index
            previous_index = self.start_finish_index
            # Set start/finish point based on the closest point to the mouse cursor
            closest_index = self.get_closest_point_index(pyxel.mouse_x, pyxel.mouse_y)
            if closest_index is not None:
                self.start_finish_index = closest_index
                # Record the action
                self.action_history.append(('set_start_finish', previous_index))
                print(f"Set start/finish point at index {self.start_finish_index}")


        if pyxel.btnp(pyxel.KEY_UP):
            previous_laps = self.max_laps
            self.max_laps += 1
            # Record the action
            self.action_history.append(('change_max_laps', previous_laps))
            print(f"Max laps increased to {self.max_laps}")
        elif pyxel.btnp(pyxel.KEY_DOWN) and self.max_laps > 1:
            previous_laps = self.max_laps
            self.max_laps -= 1
            # Record the action
            self.action_history.append(('change_max_laps', previous_laps))
            print(f"Max laps decreased to {self.max_laps}")


        if pyxel.btnp(pyxel.KEY_A):
            self.save_track()


        if pyxel.btnp(pyxel.KEY_Z):
            self.undo_last_action()


        if pyxel.btnp(pyxel.KEY_S):
            self.show_smoothed = not self.show_smoothed
            print(f"Show smoothed track: {self.show_smoothed}")

    def undo_last_action(self):
        if not self.action_history:
            print("No actions to undo.")
            return
        action, data = self.action_history.pop()
        if action == 'add_point':

            if self.points:
                removed_point = self.points.pop()
                print(f"Undo add_point: Removed point {removed_point}")
        elif action == 'loop_track':

            if self.points and self.points[-1] == self.points[0]:
                self.points.pop()
                self.looped = False
                print("Undo loop_track: Track unlooped.")
        elif action == 'set_start_finish':

            self.start_finish_index = data
            print(f"Undo set_start_finish: Start/finish index restored to {self.start_finish_index}")
        elif action == 'change_max_laps':

            self.max_laps = data
            print(f"Undo change_max_laps: Max laps restored to {self.max_laps}")
        else:
            print(f"Unknown action '{action}' to undo.")

    def get_closest_point_index(self, x, y):

        min_dist = float("inf")
        closest_index = None
        for i, (px, py) in enumerate(self.points):
            dist = (px - x) ** 2 + (py - y) ** 2
            if dist < min_dist:
                min_dist = dist
                closest_index = i
        return closest_index

    def smooth_track(self, points, num_points=200):
        """Smooths the track points using spline interpolation."""
        if len(points) < 3:
            return points  # Need at least 3 points to interpolate

        # Remove duplicate points
        unique_points = []
        seen = set()
        for p in points:
            pt = tuple(p)
            if pt not in seen:
                seen.add(pt)
                unique_points.append(p)

        x = [p[0] for p in unique_points]
        y = [p[1] for p in unique_points]

        # Convert to numpy arrays
        x = np.array(x)
        y = np.array(y)

        # Parameterize the points
        t = np.linspace(0, 1, len(x))

        # Try to fit the spline; handle exceptions
        try:
            # Use a small positive smoothing factor 's' to allow for smoothing
            tck, u = splprep([x, y], s=1.0, per=self.looped)
            unew = np.linspace(0, 1.0, num_points)
            out = splev(unew, tck)
            smoothed_points = list(zip(out[0], out[1]))
            return smoothed_points
        except Exception as e:
            print(f"Error in splprep: {e}")
            # Fall back to original points if smoothing fails
            return points

    def draw(self):
        pyxel.cls(0)

        # Draw original points and segments
        for i, (x, y) in enumerate(self.points):
            color = 10 if i == self.start_finish_index else 7  # Highlight start/finish point
            pyxel.circ(x, y, 2, color)
            if i > 0:
                prev_x, prev_y = self.points[i - 1]
                pyxel.line(prev_x, prev_y, x, y, 7)  # Draw track in white color
            if i == len(self.points) - 1 and self.looped and self.points[0] != self.points[-1]:
                # Connect last point to first if looped
                first_x, first_y = self.points[0]
                pyxel.line(x, y, first_x, first_y, 7)

        # Draw smoothed track if enabled
        if self.looped and self.show_smoothed:
            smoothed_points = self.smooth_track(self.points)
            for i in range(len(smoothed_points)):
                x1, y1 = smoothed_points[i]
                x2, y2 = smoothed_points[(i + 1) % len(smoothed_points)]
                pyxel.line(x1, y1, x2, y2, 11)  # Draw smoothed track in color index 11

        # Instructions
        instructions = "L: Loop Track | F: Set Start/Finish | UP/DOWN: Adjust Laps | A: Save | Z: Undo | S: Toggle Smooth"
        pyxel.text(5, 480, instructions, 7)

        # Display the current settings
        pyxel.text(5, 460, f"Max Laps: {self.max_laps}", 7)
        pyxel.text(5, 470, f"Show Smoothed: {self.show_smoothed}", 7)

# Run the Track Builder
TrackBuilder()
