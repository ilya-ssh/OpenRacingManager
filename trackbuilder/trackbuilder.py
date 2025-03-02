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
        self.pit_lane_points = []
        self.drawing_pit_lane = False
        pyxel.mouse(True)
        pyxel.run(self.update, self.draw)

    def save_track(self):
        # Remove the last point if it’s the same as the first to avoid duplication
        if self.points and self.points[-1] == self.points[0]:
            points_to_save = self.points[:-1]
        else:
            points_to_save = self.points

        # Prepare data to save, including the start/finish index, max laps, and pit lane
        track_data = {
            "points": points_to_save,
            "start_finish_index": self.start_finish_index,
            "max_laps": self.max_laps,
            "pit_lane_points": self.pit_lane_points
        }
        with open("../tracks/track.json", "w") as file:
            json.dump(track_data, file, indent=4)
        print("Track saved to track.json")

    def update(self):
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            x, y = pyxel.mouse_x, pyxel.mouse_y

            if not self.looped:
                # Adding points to the main track
                self.points.append((x, y))
                self.action_history.append(('add_point', (x, y)))
                print(f"Added point {x}, {y}")
            elif self.drawing_pit_lane:
                if not self.pit_lane_points:
                    # First pit lane point snaps to closest point on track
                    closest_point = self.get_closest_point_on_track(x, y)
                    self.pit_lane_points.append(closest_point)
                    print(f"Added pit lane start point {closest_point} (snapped to track)")
                else:
                    # Add pit lane points as clicked
                    self.pit_lane_points.append((x, y))
                    print(f"Added pit lane point {x}, {y}")
                self.action_history.append(('add_pit_lane_point', (x, y)))
        elif pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT) and self.drawing_pit_lane:
            # Finish pit lane drawing
            x, y = pyxel.mouse_x, pyxel.mouse_y
            # Last pit lane point snaps to closest point on track
            closest_point = self.get_closest_point_on_track(x, y)
            self.pit_lane_points.append(closest_point)
            self.action_history.append(('add_pit_lane_point', (x, y)))
            self.drawing_pit_lane = False
            print("Finished drawing pit lane.")

        if pyxel.btnp(pyxel.KEY_L) and len(self.points) > 1 and not self.looped:
            self.points.append(self.points[0])  # Connect to the starting point
            self.looped = True
            self.action_history.append(('loop_track', None))
            print("Track looped back to the start.")

        if pyxel.btnp(pyxel.KEY_F) and self.looped and self.start_finish_index is None:
            # Set start/finish point based on the closest point to the mouse cursor
            closest_index = self.get_closest_point_index(pyxel.mouse_x, pyxel.mouse_y)
            if closest_index is not None:
                self.start_finish_index = closest_index
                self.action_history.append(('set_start_finish', None))
                print(f"Set start/finish point at index {self.start_finish_index}")

        if pyxel.btnp(pyxel.KEY_P) and self.looped and self.start_finish_index is not None:
            if not self.drawing_pit_lane and not self.pit_lane_points:
                self.drawing_pit_lane = True
                print("Started drawing pit lane. Left-click to add points, right-click to finish.")
            else:
                print("Pit lane already drawn or drawing in progress.")

        if pyxel.btnp(pyxel.KEY_UP):
            previous_laps = self.max_laps
            self.max_laps += 1
            self.action_history.append(('change_max_laps', previous_laps))
            print(f"Max laps increased to {self.max_laps}")
        elif pyxel.btnp(pyxel.KEY_DOWN) and self.max_laps > 1:
            previous_laps = self.max_laps
            self.max_laps -= 1
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
            self.start_finish_index = None
            print("Undo set_start_finish: Start/finish index unset.")
        elif action == 'change_max_laps':
            self.max_laps = data
            print(f"Undo change_max_laps: Max laps restored to {self.max_laps}")
        elif action == 'add_pit_lane_point':
            if self.pit_lane_points:
                removed_point = self.pit_lane_points.pop()
                print(f"Undo add_pit_lane_point: Removed pit lane point {removed_point}")
            if not self.pit_lane_points:
                self.drawing_pit_lane = False
                print("Pit lane drawing cancelled.")
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

    def get_closest_point_on_track(self, x, y):
        min_dist = float("inf")
        closest_point = None
        for (px, py) in self.points:
            dist = (px - x) ** 2 + (py - y) ** 2
            if dist < min_dist:
                min_dist = dist
                closest_point = (px, py)
        return closest_point

    def smooth_track(self, points, num_points=200):
        """Returns smoothed points for visual effect without modifying the original points."""
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
            tck, u = splprep([x, y], s=1.0, per=False)
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

        # Draw original track points and segments
        for i, (x, y) in enumerate(self.points):
            color = 7  # Default color
            if self.start_finish_index is not None and i == self.start_finish_index:
                color = 10  # Start/finish point
            pyxel.circ(x, y, 2, color)
            if i > 0:
                prev_x, prev_y = self.points[i - 1]
                pyxel.line(prev_x, prev_y, x, y, 7)  # Draw track in white color
        # Connect last point to first if looped
        if self.looped and len(self.points) > 1:
            first_x, first_y = self.points[0]
            last_x, last_y = self.points[-1]
            pyxel.line(last_x, last_y, first_x, first_y, 7)

        # Draw smoothed track if enabled
        if self.looped and self.show_smoothed:
            smoothed_points = self.smooth_track(self.points)
            for i in range(len(smoothed_points) - 1):
                x1, y1 = smoothed_points[i]
                x2, y2 = smoothed_points[i + 1]
                pyxel.line(x1, y1, x2, y2, 11)  # Draw smoothed track in color index 11

        # Draw pit lane original points and segments
        if self.pit_lane_points:
            for i, (x, y) in enumerate(self.pit_lane_points):
                color = 8  # Default pit lane color
                if i == 0 or i == len(self.pit_lane_points) - 1:
                    color = 9  # Start and end points
                pyxel.circ(x, y, 2, color)
                if i > 0:
                    prev_x, prev_y = self.pit_lane_points[i - 1]
                    pyxel.line(prev_x, prev_y, x, y, 8)  # Draw pit lane in color index 8

            # Draw smoothed pit lane if enabled
            if self.show_smoothed:
                smoothed_pit_lane = self.smooth_track(self.pit_lane_points)
                for i in range(len(smoothed_pit_lane) - 1):
                    x1, y1 = smoothed_pit_lane[i]
                    x2, y2 = smoothed_pit_lane[i + 1]
                    pyxel.line(x1, y1, x2, y2, 12)  # Draw smoothed pit lane in color index 12

        # Instructions
        pyxel.text(430, 470, f"X: {pyxel.mouse_x} Y: {pyxel.mouse_y}", 7)
        instructions = "L: Loop Track | F: Set Start/Finish | P: Draw Pit Lane | A: Save | Z: Undo | S: Toggle Smooth"
        pyxel.text(5, 480, instructions, 7)

        # Display the current settings
        pyxel.text(5, 460, f"Max Laps: {self.max_laps}", 7)
        pyxel.text(5, 470, f"Show Smoothed: {self.show_smoothed}", 7)

        if self.drawing_pit_lane:
            pyxel.text(5, 450, "Drawing pit lane... Left-click to add points, right-click to finish.", 7)

# Run the Track Builder
TrackBuilder()
