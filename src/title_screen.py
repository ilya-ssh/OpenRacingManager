# title_screen.py

import pyxel
from constants import CURRENT_VER, GAME_TITLE
from pyxelunicode import PyxelUnicode
class TitleScreen:
    def __init__(self, game):
        self.game = game
        self.font_path = self.game.font_path
        self.font_size = 16
        self.pyunititle = PyxelUnicode(self.font_path, self.font_size)
        self.pyuni = self.game.pyuni
        self.title_text = GAME_TITLE
        self.subtitle_text = "Press any key to continue"

    def update(self):
        # Proceed to the main menu when any key is pressed
        if self.any_key_pressed():
            self.game.state = 'main_menu'

    def any_key_pressed(self):
        # Check if any key is pressed
        return any(pyxel.btnp(key) for key in range(pyxel.KEY_SPACE, pyxel.KEY_Z + 1))

    def draw(self):
        pyxel.cls(0)

        # Calculate a smoother color change using sine function for gradual transitions
        # Adjust the multiplier and offset for softer colors within the color palette range
        color = int((pyxel.sin(pyxel.frame_count * 0.50) + 1) * 8) % 16

        # Draw the title with the calculated smooth color
        title_x = pyxel.width // 2 - len(self.title_text) * self.font_size // 2
        title_y = pyxel.height // 2 - 20
        self.pyunititle.text(title_x, title_y, self.title_text, color)

        # Draw the subtitle with a static color
        subtitle_x = pyxel.width // 2 - len(self.subtitle_text) * self.font_size // 2
        subtitle_y = pyxel.height // 2
        self.pyunititle.text(subtitle_x, subtitle_y, self.subtitle_text, 7)

        # Display the version
        self.pyuni.text(370, 480, CURRENT_VER, 7)
