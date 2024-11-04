# game.py

import pyxel
from pyxelunicode import PyxelUnicode
from constants import CURRENT_VER
from title_screen import TitleScreen
from menu import MainMenu
from race import Race

class Game:
    def __init__(self):
        pyxel.init(500, 500, fps=30)
        self.state = 'title_screen'
        # Initialize PyxelUnicode for font rendering
        self.font_path = r"../fonts/PublicPixel.ttf"  # Replace with the correct path
        self.font_size = 8
        self.pyuni = PyxelUnicode(self.font_path, self.font_size)

        # Initialize state classes
        self.title_screen = TitleScreen(self)
        self.main_menu = MainMenu(self)
        self.race = None  # Will be initialized when the race starts
        # self.options_menu = OptionsMenu(self)  # Create if you implement options

        pyxel.run(self.update, self.draw)

    def update(self):
        if self.state == 'title_screen':
            self.title_screen.update()
        elif self.state == 'main_menu':
            self.main_menu.update()
        elif self.state == 'race':
            self.race.update()
        # elif self.state == 'options_menu':
        #     self.options_menu.update()

    def draw(self):
        if self.state == 'title_screen':
            self.title_screen.draw()
        elif self.state == 'main_menu':
            self.main_menu.draw()
        elif self.state == 'race':
            self.race.draw()
        # elif self.state == 'options_menu':
        #     self.options_menu.draw()

    def start_race(self):
        self.race = Race(self)
        self.state = 'race'
