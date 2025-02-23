import pyxel
from constants import CURRENT_VER, GAME_TITLE
from pyxelunicode import PyxelUnicode

# Import necessary constants and functions
WINDOW_WIDTH = 500
WINDOW_HEIGHT = 500
roadW = 2000  # road width (left to right)
segL = 200  # segment length (top to bottom)
camD = 1 # camera depth
show_N_seg = 200

x_map = 50
y_map = 60
angle_map = 0

# Define line length and angle increment
length_map = 1

dark_road = 5
white_rumble = 1
light_grass = 7
dark_grass = 8


def drawQuad(color, x1, y1, w1, x2, y2, w2):
    points = [(x1 - w1, y1), (x2 - w2, y2), (x2 + w2, y2), (x1 + w1, y1)]
    draw_polygon(points, color)

def draw_polygon(points, color):
    # Triangulate the polygon using the ear clipping algorithm
    triangles = []
    remaining_points = points.copy()
    while len(remaining_points) >= 3:
        # Find an "ear" triangle
        for i in range(len(remaining_points)):
            prev = remaining_points[(i - 1) % len(remaining_points)]
            curr = remaining_points[i]
            next = remaining_points[(i + 1) % len(remaining_points)]
            if is_ear(prev, curr, next, remaining_points):
                triangles.append((prev, curr, next))
                remaining_points.remove(curr)
                break

    # Draw each triangle with the specified color
    for triangle in triangles:
        x1, y1 = triangle[0]
        x2, y2 = triangle[1]
        x3, y3 = triangle[2]
        pyxel.tri(x1, y1, x2, y2, x3, y3, col=color)

def is_ear(p1, p2, p3, polygon):
    # Check if the triangle formed by p1, p2, p3 is an "ear"
    if not is_ccw(p1, p2, p3):
        return False
    for point in polygon:
        if point in (p1, p2, p3):
            continue
        if is_inside_triangle(p1, p2, p3, point):
            return False
    return True

def is_ccw(p1, p2, p3):
    # Check if the points p1, p2, p3 are in counter-clockwise order
    # using the cross product method
    return (p2[0] - p1[0]) * (p3[1] - p1[1]) > (p2[1] - p1[1]) * (p3[0] - p1[0])

def is_inside_triangle(p1, p2, p3, point):
    # Check if the point is inside the triangle formed by p1, p2, p3
    u = ((p2[0] - p1[0]) * (point[1] - p1[1]) - (p2[1] - p1[1]) * (point[0] - p1[0])) / (
            (p2[1] - p1[1]) * (p3[0] - p2[0]) - (p2[0] - p1[0]) * (p3[1] - p2[1]))
    v = ((p3[0] - p2[0]) * (point[1] - p2[1]) - (p3[1] - p2[1]) * (point[0] - p2[0])) / (
            (p2[1] - p1[1]) * (p3[0] - p2[0]) - (p2[0] - p1[0]) * (p3[1] - p2[1]))
    return 0 <= u <= 1 and 0 <= v <= 1 and u + v <= 1

# Define necessary colors
light_grass = 3
dark_grass = 11
white_rumble = 7
dark_road = 13

class Line:
    def __init__(self, i):
        self.i = i
        self.x = self.y = self.z = 0.0  # game position (3D space)
        self.X = self.Y = self.W = 0.0  # screen position (2D projection)
        self.scale = 0.0  # scale from camera position
        self.curve = 0.0  # curve radius
        self.spriteX = 0.0  # sprite position X
        self.clip = 0.0  # correct sprite Y position
        self.sprite = None

        self.grass_color = 0
        self.rumble_color = 0
        self.road_color = 0
        self.stripe_color = 0

    def project(self, camX, camY, camZ):
        self.scale = camD / (self.z - camZ)
        self.X = (1 + self.scale * (self.x - camX)) * WINDOW_WIDTH / 2
        self.Y = (1 - self.scale * (self.y - camY)) * WINDOW_HEIGHT / 2
        self.W = self.scale * roadW * WINDOW_WIDTH / 2

class RoadEffect:
    def __init__(self):
        self.pos = 0
        self.playerX = 0  # player starts at the center of the road
        self.playerY = 700  # camera height offset
        self.speed = 800  # constant speed for title screen
        self.linespr = 0

        # Create road lines for each segment
        self.lines = []
        N = 1600
        for i in range(N):
            line = Line(i)
            line.z = i * segL + 0.00001

            # Change color every other 3 lines
            grass_color = light_grass if (i // 40) % 2 else dark_grass
            rumble_color = 8 if (i // 15) % 2 else 7
            road_color = dark_road
            stripe_color = dark_road

            line.grass_color = grass_color
            line.rumble_color = rumble_color
            line.road_color = road_color
            line.stripe_color = stripe_color

            # Right curve
            if 300 < i < 400:
                line.curve = 2.2

            # Uphill and downhill
            if 1600 > i > 750:
                line.y = pyxel.sin((i / 30.0) * 180 / 3.14159265358979323846) * 1500

            # Left curve
            if i > 1100:
                line.curve = -0.7

            self.lines.append(line)

    def update(self):
        # Update the road effect state
        self.pos += self.speed
        N = len(self.lines)
        while self.pos >= N * segL:
            self.pos -= N * segL

    def draw(self):
        # Draw the road effect
        pyxel.cls(6)  # Sky color

        lines = self.lines
        N = len(lines)
        startPos = int(self.pos // segL)
        x = dx = 0.0  # Curve offset on x axis
        camH = lines[startPos].y + self.playerY
        maxy = WINDOW_HEIGHT

        for n in range(startPos, startPos + show_N_seg):
            current = lines[n % N]
            current.project(self.playerX - x, camH, self.pos - (N * segL if n >= N else 0))
            x += dx
            dx += current.curve
            current.clip = maxy
            if current.Y >= maxy:
                continue
            maxy = current.Y
            prev = lines[(n - 1) % N]
            # Draw the road segments
            drawQuad(
                current.grass_color,
                0,
                prev.Y,
                WINDOW_WIDTH,
                0,
                current.Y,
                WINDOW_WIDTH,
            )
            drawQuad(
                current.rumble_color,
                prev.X,
                prev.Y,
                prev.W * 1.25,
                current.X,
                current.Y,
                current.W * 1.25,
            )
            drawQuad(
                current.road_color,
                prev.X,
                prev.Y,
                prev.W,
                current.X,
                current.Y,
                current.W,
            )
            drawQuad(
                current.stripe_color,
                prev.X,
                prev.Y,
                prev.W * 0.90,
                current.X,
                current.Y,
                current.W * 0.90,
            )

def reset_palette():
    default_colors = [
        0x000000, 0x2B335F, 0x7E2072, 0x19959C,
        0x8B4B52, 0x395C98, 0xA9C1FF, 0xEEEEEE,
        0xD41B6C, 0xD38441, 0xE9C35B, 0x70C6A9,
        0x7696DE, 0xA3A3A3, 0xFF9798, 0xEDC7B0
    ]
    for i in range(16):
        pyxel.colors[i] = default_colors[i]

class TitleScreen:
    def __init__(self, game):
        self.game = game
        self.font_path = str(self.game.font_path)
        self.font_size = 16
        self.pyunititle = PyxelUnicode(self.font_path, self.font_size)
        self.pyuni = self.game.pyuni
        self.title_text = GAME_TITLE
        self.subtitle_text = "Press any key to continue"
        self.road_effect = RoadEffect()

    def update(self):
        # Update the road effect
        self.road_effect.update()
        # Proceed to the main menu when any key is pressed
        if self.any_key_pressed():
            # Restore the palette to default
            reset_palette()
            self.game.state = 'main_menu'

    def any_key_pressed(self):
        # Check if any key is pressed
        return any(pyxel.btnp(key) for key in range(pyxel.KEY_SPACE, pyxel.KEY_Z + 1))

    def draw(self):
        self.road_effect.draw()
        # Now draw the title text over the road effect
        # Remove the color-changing code
        color = 0  # Fixed color

        # Draw the title with the fixed color
        title_x = pyxel.width // 2 - len(self.title_text) * self.font_size // 2
        title_y = pyxel.height // 2 - 20
        self.pyunititle.text(title_x, title_y, self.title_text, color)

        # Draw the subtitle with a static color
        subtitle_x = pyxel.width // 2 - len(self.subtitle_text) * self.font_size // 2
        subtitle_y = pyxel.height // 2
        self.pyunititle.text(subtitle_x, subtitle_y, self.subtitle_text, color)

        # Display the version
        self.pyuni.text(370, 480, CURRENT_VER, 7)
