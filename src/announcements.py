import pyxel
class Announcements:
    def __init__(self, pyuni):
        self.pyuni = pyuni
        self.messages = []
        self.display_duration = 180  # Frames to display each message (e.g., 3 seconds at 60 FPS)
        self.current_message = None
        self.message_timer = 0

    def add_message(self, message):
        self.messages.append(message)

    def update(self):
        if self.current_message is None and self.messages:
            self.current_message = self.messages.pop(0)
            self.message_timer = self.display_duration
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
