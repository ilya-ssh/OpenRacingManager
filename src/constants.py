DEBUG_MODE = True

MAX_LAPS = 50

# Tire types and their properties
TIRE_TYPES = {
    "hard": {"wear_rate": 0.0015, "initial_grip": 0.9, "threshold": 25},
    "medium": {"wear_rate": 0.0025, "initial_grip": 1.3, "threshold": 35},
    "soft": {"wear_rate": 0.005, "initial_grip": 1.5, "threshold": 50}
}
GAME_TITLE = "OpenRacingManager"
CURRENT_VER = "Pre-alpha 0.0.3b"

# Pitstop constants
PIT_STOP_THRESHOLD = 20.0     # Tire percentage to trigger pitstop
PITLANE_SPEED_LIMIT = 0.3     # Speed limit in the pitlane
PIT_STOP_DURATION = 60        # Frames to wait during pitstop
