# constants.py
DEBUG_MODE = True
MAX_LAPS = 50
QUALIFYING_TIME = 10
ENABLE_WARMUP_LAP = True
SAFETY_CAR_DEPLOY_CHANCE = 0.0001
SAFETY_CAR_SPEED = 0.3
SAFETY_CAR_CATCH_DISTANCE = 10.0
SAFETY_CAR_GAP_DISTANCE = 2.0
SAFETY_CAR_DURATION_LAPS = 1
SAFETY_CAR_COLOR_INDEX = 15
SAFETY_CAR_CATCH_UP_SPEED = 0.5  # Faster than safety car speed
OVERTAKE_CHANCE = 0.01
CRASH_CHANCE = 0.00001
CRASH_RECOVERY_TIME = 0
TIRE_TYPES = {
    "hard": {"wear_rate": 0.04, "initial_grip": 0.9, "threshold": 25},
    "medium": {"wear_rate": 0.0025, "initial_grip": 1.3, "threshold": 35},
    "soft": {"wear_rate": 0.005, "initial_grip": 1.5, "threshold": 50}
}
GAME_TITLE = "OpenRacingManager"
CURRENT_VER = "Pre-alpha 0.0.7a"
PIT_STOP_THRESHOLD = 50.0
PITLANE_SPEED_LIMIT = 0.3
PIT_STOP_DURATION = 60
teamsfile = r"../database/teams/teams.json"

