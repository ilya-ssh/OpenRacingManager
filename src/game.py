import pyxel
from pyxelunicode import PyxelUnicode
from constants import CURRENT_VER
from title_screen import TitleScreen
from menu import MainMenu
from race import Race
from qualifying import Qualifying

class Game:
    def __init__(self):
        pyxel.init(500, 500, fps=30)
        self.state = 'title_screen'
        self.font_path = r"../fonts/PublicPixel.ttf"
        self.font_size = 8
        self.pyuni = PyxelUnicode(self.font_path, self.font_size)
        self.title_screen = TitleScreen(self)
        self.main_menu = MainMenu(self)
        self.qualifying = None
        self.race = None
        pyxel.mouse(visible=True)
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

    def draw(self):
        if self.state == 'title_screen':
            self.title_screen.draw()
        elif self.state == 'main_menu':
            self.main_menu.draw()
        elif self.state == 'qualifying':
            self.qualifying.draw()
        elif self.state == 'race':
            self.race.draw()

    def start_qualifying(self):
        self.qualifying = Qualifying(self)
        self.state = 'qualifying'

    def start_race(self, starting_grid=None):
        self.race = Race(self, starting_grid)
        self.state = 'race'
