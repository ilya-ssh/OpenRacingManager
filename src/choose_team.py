import pyxel
import json
import math
from pyxelunicode import PyxelUnicode

class ChooseTeam:
    def __init__(self, game):
        self.game = game
        self.font_path = r"../fonts/PublicPixel.ttf"
        self.font_size = 16
        self.pyuni = PyxelUnicode(self.font_path, self.font_size)
        self.sprite_x = 0
        self.sprite_y = 0
        self.sprite_width = 200
        self.sprite_height = 200
        self.current_team_index = 0
        self.teams = self.load_teams()
        self.base_color = int(self.teams[self.current_team_index]["color"], 16)
        self.initial_frame = True

        # Animation variables
        self.animation_phase = None  # Track the current phase of the animation
        self.anim_direction = 0  # -1 for left, 1 for right
        self.anim_offset = 0
        self.anim_speed = 10  # Adjust speed for smoothness on 500x500 screen

        # Triangle animation properties
        self.triangle_angle_left = 0  # Angle for circular motion on the left side
        self.triangle_angle_right = 0  # Angle for circular motion on the right side
        self.triangle_speed = 0.02  # Speed of rotation

        # Car circling effect
        self.car_angle = 0  # Angle for circular movement of the car
        self.car_radius = 5  # Radius of the car’s circular motion
        self.car_speed = 0.05  # Speed of the car's circular movement

        self.flash_counter = 10  # Counter for the flash effect
        self.flash_delay = 7  # Adjust flash speed
        self.flash_duration = 80  # Total time to flash

    def load_teams(self):
        """Load team data from JSON file."""
        with open("../database/teams/teams.json", "r") as f:
            return json.load(f)

    def toggle_colors(self):
        """Toggle the colors between white and base color for flashing effect."""
        if pyxel.colors[7] == self.base_color:
            # Flash to white
            pyxel.colors[7] = 0xFFFFFF
            pyxel.colors[8] = 0xFFFFFF
            pyxel.colors[13] = 0xFFFFFF
            pyxel.colors[3] = 0xFFFFFF
        else:
            # Reset to original colors (base color)
            self.set_shaded_colors(self.base_color)

    def update(self):
        # Update triangle angles for counter-clockwise and clockwise movement
        self.triangle_angle_left += self.triangle_speed  # Counter-clockwise for left
        self.triangle_angle_right -= self.triangle_speed  # Clockwise for right

        # Update car angle for slight circular movement
        self.car_angle += self.car_speed
        if self.car_angle >= 2 * math.pi:  # Reset after a full rotation
            self.car_angle -= 2 * math.pi

        if self.animation_phase == "flashing":
            self.flash_counter += 1
            if self.flash_counter > self.flash_duration:
                self.set_shaded_colors(self.base_color)  # Restore original colors
                self.game.start_qualifying()  # Move to next state after flashing
            elif self.flash_counter % self.flash_delay == 0:
                # Toggle colors between base and faded
                self.toggle_colors()

        # Start animation on left or right arrow key press
        if self.animation_phase is None:
            if pyxel.btnp(pyxel.KEY_RIGHT):
                self.anim_direction = 1
                self.start_animation("moving_out")
            elif pyxel.btnp(pyxel.KEY_LEFT):
                self.anim_direction = -1
                self.start_animation("moving_out")

        # Handle the animation phases
        if self.animation_phase == "moving_out":
            self.anim_offset += self.anim_speed * self.anim_direction
            if abs(self.anim_offset) >= pyxel.width:
                # Switch to palette update phase once old car is off-screen
                self.start_animation("palette_update")

        elif self.animation_phase == "palette_update":
            # Update team, color palette, and set up the new car position
            self.switch_to_new_team()

        elif self.animation_phase == "moving_in":
            self.anim_offset += self.anim_speed * self.anim_direction
            if self.anim_offset == 0:
                # Finish animation once the new car is centered
                self.animation_phase = None

        # Confirm selection with Enter key to transition back to the main menu
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.confirm_team_selection()

    def start_animation(self, phase):
        """Initiate the specified animation phase."""
        self.animation_phase = phase
        if phase == "moving_out":
            self.anim_offset = 0
        elif phase == "moving_in":
            self.anim_offset = -pyxel.width * self.anim_direction  # Position new sprite off-screen

    def switch_to_new_team(self):
        """Switch to the new team and start moving it on-screen."""
        # Update team index and palette
        self.current_team_index = (self.current_team_index + self.anim_direction) % len(self.teams)
        self.update_base_color()  # Update base color for the new team
        # Move to the "moving_in" phase to bring the new car on-screen
        self.start_animation("moving_in")

    def update_base_color(self):
        """Update the base color based on the selected team's color."""
        self.base_color = int(self.teams[self.current_team_index]["color"], 16)
        self.set_shaded_colors(self.base_color)

    def set_shaded_colors(self, base_color):
        """Set multiple Pyxel colors to progressively darker shades of the given base color."""
        red = (base_color >> 16) & 0xFF
        green = (base_color >> 8) & 0xFF
        blue = base_color & 0xFF

        pyxel.colors[7] = base_color
        pyxel.colors[8] = (max(0, int(red * 0.8)) << 16) | (max(0, int(green * 0.8)) << 8) | max(0, int(blue * 0.8))
        pyxel.colors[13] = (max(0, int(red * 0.6)) << 16) | (max(0, int(green * 0.6)) << 8) | max(0, int(blue * 0.6))
        pyxel.colors[3] = (max(0, int(red * 0.4)) << 16) | (max(0, int(green * 0.4)) << 8) | max(0, int(blue * 0.4))
        pyxel.colors[15] = (max(0, int(red * 0.6)) << 16) | (max(0, int(green * 0.6)) << 8) | max(0, int(blue * 0.6))

    def draw_triangles(self):
        """Draws moving outward-pointing triangles on the left and right sides."""
        center_y = (pyxel.height // 2) - 50
        radius = 20  # Distance from center for triangle base points
        base_x_left = 40  # Base x position for left side triangles
        base_x_right = pyxel.width - 40  # Base x position for right side triangles

        colors = [7, 8, 13]
        for i, color in enumerate(colors):
            # Calculate left triangle position (counter-clockwise movement)
            angle_left = self.triangle_angle_left + i * math.pi / 6
            left_x = base_x_left + math.cos(angle_left) * radius
            left_y = center_y + math.sin(angle_left) * radius
            pyxel.tri(left_x, left_y - 10, left_x - 20, left_y, left_x, left_y + 10, color)

            # Calculate right triangle position (clockwise movement)
            angle_right = self.triangle_angle_right + i * math.pi / 6
            right_x = base_x_right + math.cos(angle_right) * radius
            right_y = center_y + math.sin(angle_right) * radius
            pyxel.tri(right_x, right_y - 10, right_x + 20, right_y, right_x, right_y + 10, color)

    def drawbox(self, x_box, y_box, width, height, radius, border_thickness):
        """Draws a rounded box with a white border and black inner box."""
        # Draw white border
        pyxel.rect(x_box + radius, y_box, width - 2 * radius, height, 11)  # White color (11)
        pyxel.rect(x_box, y_box + radius, width, height - 2 * radius, 11)  # White color (11)
        pyxel.rect(x_box + radius, y_box + height - radius, width - 2 * radius, radius, 11)  # White color (11)

        # Draw white rounded corners
        pyxel.circ(x_box + radius, y_box + radius, radius, 11)  # White color (11)
        pyxel.circ(x_box + width - radius - 1, y_box + radius, radius, 11)  # White color (11)
        pyxel.circ(x_box + radius, y_box + height - radius - 1, radius, 11)  # White color (11)
        pyxel.circ(x_box + width - radius - 1, y_box + height - radius - 1, radius, 11)  # White color (11)

        # Draw inner black box
        inner_x, inner_y = x_box + border_thickness, y_box + border_thickness
        inner_width, inner_height = width - 2 * border_thickness, height - 2 * border_thickness
        inner_radius = radius - border_thickness

        pyxel.rect(inner_x + inner_radius, inner_y, inner_width - 2 * inner_radius, inner_height, 0)  # Black color (0)
        pyxel.rect(inner_x, inner_y + inner_radius, inner_width, inner_height - 2 * inner_radius, 0)  # Black color (0)
        pyxel.rect(inner_x + inner_radius, inner_y + inner_height - inner_radius, inner_width - 2 * inner_radius,
                   inner_radius, 0)  # Black color (0)

        # Draw black rounded corners
        pyxel.circ(inner_x + inner_radius, inner_y + inner_radius, inner_radius, 0)  # Black color (0)
        pyxel.circ(inner_x + inner_width - inner_radius - 1, inner_y + inner_radius, inner_radius, 0)  # Black color (0)
        pyxel.circ(inner_x + inner_radius, inner_y + inner_height - inner_radius - 1, inner_radius,
                   0)  # Black color (0)
        pyxel.circ(inner_x + inner_width - inner_radius - 1, inner_y + inner_height - inner_radius - 1, inner_radius,
                   0)  # Black color (0)

    def draw(self):
        # Clear the screen
        pyxel.cls(0)
        if self.initial_frame:
            self.update_base_color()
            self.initial_frame = False

        # Display team information
        team_name = self.teams[self.current_team_index]["team_name"]


        # Calculate circular offset for the car's slight circular movement
        car_offset_x = math.cos(self.car_angle) * self.car_radius
        car_offset_y = math.sin(self.car_angle) * self.car_radius



        # Draw the car sprite at a fixed position when in the flashing phase
        if self.animation_phase == "flashing":
            center_x = (pyxel.width - self.sprite_width) // 2
            center_y = ((pyxel.height - self.sprite_height) // 2) - 50
            pyxel.blt(center_x + car_offset_x, center_y + car_offset_y, 0, self.sprite_x, self.sprite_y, self.sprite_width, self.sprite_height, 11)

        # Draw the car selection animation
        center_x = (pyxel.width - self.sprite_width) // 2
        center_y = ((pyxel.height - self.sprite_height) // 2) - 50

        if self.animation_phase in ["moving_out", None]:
            # Draw current car sprite during moving out or idle with circular offset
            current_x = center_x + self.anim_offset + car_offset_x
            current_y = center_y + car_offset_y
            pyxel.blt(current_x, current_y, 0, self.sprite_x, self.sprite_y, self.sprite_width, self.sprite_height, 11)

        if self.animation_phase == "moving_in":
            # Draw new car sprite moving in from opposite side with circular offset
            next_x = center_x + self.anim_offset + car_offset_x
            next_y = center_y + car_offset_y
            pyxel.blt(next_x, next_y, 0, self.sprite_x, self.sprite_y, self.sprite_width, self.sprite_height, 11)

        # Draw the animated shaded triangles on both sides
        self.draw_triangles()
        pyxel.colors[11] = 0xFFFFFFF
        box_width, box_height = 120, 30
        y_box = pyxel.height // 2 + self.sprite_height // 2 + 10  # Position below the car
        x_start = (pyxel.width - 3 * box_width - 20) // 2  # Center all three boxes with 10 px spacing

        menu_title = "Team selection"
        title_x = pyxel.width // 2 - len(menu_title) * 16 // 2
        title_y = 20
        self.pyuni.text(title_x, title_y, menu_title, 11)
        title_x = pyxel.width // 2 - len(team_name) * 16 // 2
        self.pyuni.text(title_x, 50, f"{team_name}", 7)

        # Draw each box
        for i in range(3):
            x_box = x_start + i * (box_width + 10)
            self.drawbox(x_box, y_box, box_width, box_height, radius=5, border_thickness=2)

            # Add text to each box
            if i == 0:
                pyxel.text(x_box + 5, y_box + 10, f"Team: {team_name}", 11)  # White color (11)
            elif i == 1:
                driver = self.teams[self.current_team_index]["drivers"][0]["name"]
                pyxel.text(x_box + 5, y_box + 10, f"Driver 1: {driver}", 11)  # White color (11)
            elif i == 2:
                driver = self.teams[self.current_team_index]["drivers"][1]["name"]
                pyxel.text(x_box + 5, y_box + 10, f"Driver 2: {driver}", 11)  # White color (11)

    def confirm_team_selection(self):
        """Confirm the selected team and initiate flashing animation before transition."""
        self.flash_counter = 0  # Reset the flash counter
        self.animation_phase = "flashing"  # Start flashing phase
