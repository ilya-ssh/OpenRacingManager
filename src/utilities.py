# utilities.py

def braking_curve(current_speed, target_speed, deceleration_factor=0.95):
    """Applies a deceleration factor to reduce the car's speed smoothly."""
    return max(target_speed, current_speed * deceleration_factor)
