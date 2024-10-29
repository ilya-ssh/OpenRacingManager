# constants.py

DEBUG_MODE = False

MAX_LAPS = 2

# Tire types and their properties
TIRE_TYPES = {
    "hard": {"wear_rate": 0.005, "initial_grip": 0.9, "threshold": 25},
    "medium": {"wear_rate": 0.01, "initial_grip": 1.0, "threshold": 35},
    "soft": {"wear_rate": 0.015, "initial_grip": 1.1, "threshold": 50}
}

CURRENT_VER = "Pre-alpha 0.0.2"