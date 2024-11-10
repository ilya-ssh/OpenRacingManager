import json
from constants import teamsfile
def load_teams(filename=teamsfile):
    with open(filename, 'r') as file:
        teams_data = json.load(file)
    return teams_data