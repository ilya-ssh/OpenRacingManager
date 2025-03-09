# constants.py
DEBUG_MODE = True
MAX_LAPS = 50
QUALIFYING_TIME = 0.05
ENABLE_WARMUP_LAP = False
SAFETY_CAR_DEPLOY_CHANCE = 0.0001
SAFETY_CAR_SPEED = 0.2
SAFETY_CAR_CATCH_DISTANCE = 10.0
SAFETY_CAR_GAP_DISTANCE = 2.0
SAFETY_CAR_DURATION_LAPS = 1
SAFETY_CAR_COLOR_INDEX = 15
SAFETY_CAR_CATCH_UP_SPEED = 0.6
OVERTAKE_CHANCE = 0.001
CRASH_CHANCE = 0.00001
MISTAKE_CHANCE = 0.0001
CRASH_RECOVERY_TIME = 0
TIRE_TYPES = {
    "hard":   {"wear_rate": 0.0007, "grip": 1.00, "threshold": 15, "temp_gain": 1.28, "optimal_temp": 90},
    "medium": {"wear_rate": 0.0022, "grip": 1.04, "threshold": 20, "temp_gain": 1.30,  "optimal_temp": 90},
    "soft":   {"wear_rate": 0.009,  "grip": 1.10, "threshold": 30, "temp_gain": 1.5,  "optimal_temp": 90}
}
GAME_TITLE = "OpenRacingManager"
CURRENT_VER = "Pre-alpha 0.0.10"
PIT_STOP_THRESHOLD = 50.0
PITLANE_SPEED_LIMIT = 0.25
PIT_STOP_DURATION = 60
teamsfile = r"../database/teams/teams.json"
SLIPSTREAM_DISTANCE = 5.0
SLIPSTREAM_BASE_FRAMES = 20
SLIPSTREAM_OVERTAKE_FRAMES = 30
SLIPSTREAM_SPEED_BOOST = 1.10

