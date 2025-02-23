import pyxel
from pyxelunicode import PyxelUnicode
from constants import CURRENT_VER
from title_screen import TitleScreen
from menu import MainMenu
from race import Race
from qualifying import Qualifying
from choose_team import ChooseTeam
from pathlib import Path

class Game:
    def __init__(self):
        pyxel.init(500, 500, fps=30)
        self.state = 'title_screen'
        self.font_path = Path(__file__).resolve().parent.parent / "fonts" / "PublicPixel.ttf"
        self.font_size = 8
        self.pyuni = PyxelUnicode(str(self.font_path), self.font_size)
        self.title_screen = TitleScreen(self)
        self.main_menu = MainMenu(self)
        self.qualifying = None
        self.race = None
        self.choose_team_screen = ChooseTeam(self)  # This is now a ChooseTeam instance
        pyxel.mouse(visible=True)
        pyxel.images[0].load(0, 0, r"../assets/car.png")
        pyxel.run(self.update, self.draw)

    def update(self):
        if self.state == 'title_screen':
            self.title_screen.update()
        elif self.state == 'main_menu':
            self.main_menu.update()
        elif self.state == 'qualifying':
            self.qualifying.update()
        elif self.state == 'race':
            self.race.update()
        elif self.state == 'choose_team':
            self.choose_team_screen.update()

    def draw(self):

        if self.state == 'title_screen':
            self.title_screen.draw()
        elif self.state == 'main_menu':
            self.main_menu.draw()
        elif self.state == 'qualifying':
            self.qualifying.draw()
        elif self.state == 'race':
            self.race.draw()
        elif self.state == 'choose_team':
            self.choose_team_screen.draw()
        self.pyuni.text(370, 480, CURRENT_VER, 0)
        for n in range(16):
            pyxel.rect(6 * n, pyxel.height - 10, 6, 6, n)

    def start_qualifying(self):
        self.qualifying = Qualifying(self)
        self.state = 'qualifying'

    def start_race(self, starting_grid=None):
        self.race = Race(self, starting_grid)
        self.state = 'race'

    def start_choose_team(self):  # This is the method to call for choosing a team
        self.state = "choose_team"
