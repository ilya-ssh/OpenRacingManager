# announcements.py

import pyxel

class Announcements:
    def __init__(self, pyuni):
        self.pyuni = pyuni
        self.messages = []
        self.default_display_duration = 90  # Reduced to 90 frames (3 seconds at 30 FPS)
        self.current_message = None
        self.message_timer = 0

    def add_message(self, message, duration=None):
        if duration is None:
            duration = self.default_display_duration
        self.messages.append((message, duration))

    def update(self):
        if self.current_message is None and self.messages:
            self.current_message, self.message_timer = self.messages.pop(0)
        elif self.current_message is not None:
            self.message_timer -= 1
            if self.message_timer <= 0:
                self.current_message = None

    def draw(self):
        if self.current_message:
            x = 100
            y = pyxel.height - 30
            pyxel.rect(x - 5, y - 5, 300, 20, 0)  # Background rectangle
            self.pyuni.text(x, y, self.current_message, 7)
