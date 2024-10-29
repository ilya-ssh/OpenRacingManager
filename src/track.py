# track.py
import json
import math
import numpy as np
from scipy.interpolate import splprep, splev

def load_track(file_path):
    with open(file_path, 'r') as file:
        track_data = json.load(file)
    points = track_data['points']
    start_finish_index = track_data.get('start_finish_index', 0)
    return points, start_finish_index

def compute_cumulative_distances(points):
    distances = [0]
    total_length = 0
    for i in range(len(points)):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % len(points)]  # Loop around
        dist = math.hypot(x2 - x1, y2 - y1)
        total_length += dist
        distances.append(total_length)
    return distances

def compute_angle_differences(points):
    angle_diffs = []
    for i in range(len(points)):
        # Get three consecutive points
        x0, y0 = points[i - 1]  # Previous point (handles wrap-around)
        x1, y1 = points[i]      # Current point
        x2, y2 = points[(i + 1) % len(points)]  # Next point (wrap-around)
        
        # Create vectors from the points
        v1 = (x1 - x0, y1 - y0)
        v2 = (x2 - x1, y2 - y1)
        
        # Calculate the angle between the vectors
        dot_prod = v1[0]*v2[0] + v1[1]*v2[1]
        mag_v1 = math.hypot(*v1)
        mag_v2 = math.hypot(*v2)
        
        if mag_v1 == 0 or mag_v2 == 0:
            angle_diff = 0
        else:
            cos_theta = dot_prod / (mag_v1 * mag_v2)
            # Ensure cos_theta is within [-1, 1]
            cos_theta = max(-1.0, min(1.0, cos_theta))
            angle_diff = math.acos(cos_theta)
        
        angle_diffs.append(angle_diff)
    return angle_diffs

def compute_desired_speeds(angle_diffs, max_speed, min_speed):
    desired_speeds = []
    for angle_diff in angle_diffs:
        # Larger angle_diff leads to lower desired speed
        speed = max_speed - (max_speed - min_speed) * (angle_diff / math.pi)
        desired_speeds.append(max(min_speed, speed))
    return desired_speeds

def get_position_along_track(distance, points, cumulative_distances):
    total_length = cumulative_distances[-1]
    distance = distance % total_length  # Wrap around
    for i in range(len(cumulative_distances) - 1):
        if cumulative_distances[i] <= distance <= cumulative_distances[i + 1]:
            t = (distance - cumulative_distances[i]) / (cumulative_distances[i + 1] - cumulative_distances[i])
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % len(points)]
            x = x1 + (x2 - x1) * t
            y = y1 + (y2 - y1) * t
            return x, y
    return points[-1]

def get_desired_speed_at_distance(distance, desired_speeds_list, total_length, car):
    distance = distance % total_length
    for i in range(len(desired_speeds_list) - 1):
        dist1, base_speed1 = desired_speeds_list[i]
        dist2, base_speed2 = desired_speeds_list[i + 1]
        if dist1 <= distance <= dist2:
            t = (distance - dist1) / (dist2 - dist1)
            # Base speed interpolation
            base_speed = base_speed1 + (base_speed2 - base_speed1) * t
            # Adjust base speed based on car's aero efficiency
            adjusted_speed = base_speed * car.aero_efficiency
            return adjusted_speed
    # If distance exceeds the last point, return the last speed adjusted for the car
    return desired_speeds_list[-1][1] * car.aero_efficiency

def smooth_track(points, num_points=200):
    import numpy as np
    from scipy.interpolate import splprep, splev

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
        tck, u = splprep([x, y], s=1.0, per=True)
        unew = np.linspace(0, 1.0, num_points)
        out = splev(unew, tck)
        smoothed_points = list(zip(out[0], out[1]))
        return smoothed_points
    except Exception as e:
        print(f"Error in splprep: {e}")
        # Fall back to original points if smoothing fails
        return points

# Load track and compute necessary data
track_path = r'../tracks/track.json'
TRACK_POINTS, START_FINISH_INDEX = load_track(track_path)
TRACK_POINTS = smooth_track(TRACK_POINTS)  # Apply smoothing
CUMULATIVE_DISTANCES = compute_cumulative_distances(TRACK_POINTS)
TOTAL_TRACK_LENGTH = CUMULATIVE_DISTANCES[-1]
ANGLE_DIFFS = compute_angle_differences(TRACK_POINTS)
MAX_SPEED = 0.7  # Adjust as needed
MIN_SPEED = 0.001  # Adjust as needed
DESIRED_SPEEDS = compute_desired_speeds(ANGLE_DIFFS, MAX_SPEED, MIN_SPEED)
DESIRED_SPEEDS_LIST = list(zip(CUMULATIVE_DISTANCES[:-1], DESIRED_SPEEDS))
