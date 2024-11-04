# menu.py

import pyxel
from constants import CURRENT_VER

class MainMenu:
    def __init__(self, game):
        self.game = game
        self.pyuni = self.game.pyuni
        self.menu_items = ["Start Career", "Load Career", "About", "Exit"]
        self.selected_index = 0  # Index of the currently selected menu item

    def update(self):
        # Navigate the menu using up and down arrow keys
        if pyxel.btnp(pyxel.KEY_UP):
            self.selected_index = (self.selected_index - 1) % len(self.menu_items)
        elif pyxel.btnp(pyxel.KEY_DOWN):
            self.selected_index = (self.selected_index + 1) % len(self.menu_items)

        # Select the menu item when Enter is pressed
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.select_menu_item()

    def select_menu_item(self):
        selected_item = self.menu_items[self.selected_index]
        if selected_item == "Start Career":
            self.game.start_race()
        elif selected_item == "Load Career":
            # You can implement an OptionsMenu class similarly
            self.game.state = 'options_menu'
        elif selected_item == "About":
            pyxel.quit()
        elif selected_item == "Exit":
            pyxel.quit()

    def draw(self):
        pyxel.cls(0)
        # Draw the menu title
        menu_title = "Main Menu"
        title_x = pyxel.width // 2 - len(menu_title) * 8 // 2
        title_y = 50
        self.pyuni.text(title_x, title_y, menu_title, 7)

        # Draw the menu items
        for index, item in enumerate(self.menu_items):
            color = 7  # Default color
            if index == self.selected_index:
                color = 10  # Highlighted color
            item_x = pyxel.width // 2 - len(item) * 8 // 2
            item_y = 100 + index * 20
            self.pyuni.text(item_x, item_y, item, color)

        # Display the version
        self.pyuni.text(370, 480, CURRENT_VER, 7)
