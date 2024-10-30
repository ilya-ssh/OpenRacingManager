DEBUG_MODE = True

MAX_LAPS = 50

# Tire types and their properties
TIRE_TYPES = {
    "hard": {"wear_rate": 0.025, "initial_grip": 0.9, "threshold": 25},
    "medium": {"wear_rate": 0.025, "initial_grip": 1.0, "threshold": 35},
    "soft": {"wear_rate": 0.025, "initial_grip": 1.1, "threshold": 50}
}

CURRENT_VER = "Pre-alpha 0.0.2"

# Pitstop constants
PIT_STOP_THRESHOLD = 20.0     # Tire percentage to trigger pitstop
PITLANE_SPEED_LIMIT = 0.3     # Speed limit in the pitlane
PIT_STOP_DURATION = 60        # Frames to wait during pitstop
