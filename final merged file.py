from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

import time
import random
import math

# Camera-related variables
camera_pos = (0, 200, 300)  # Closer behind the bike for better perspective
camera_mode = "third_person"  # "third_person" or "first_person"
first_person_cam = (0, 3, 0)  # At rider's head level for first-person view

fovY = 90  # Narrower FOV for better 3D perspective
GRID_LENGTH = 600  # Length of grid lines
rand_var = 423


# free look global vars
free_look_yaw = 180.0      # degrees, left/right yaw
free_look_pitch = -10.0    # degrees, up/down pitch
free_look_enabled = False
key_down = { 'w': False, 'a': False, 's': False, 'd': False }

#  Gameplay globals 
LANES_X = (-150.0, 0.0, 150.0)
player_lane = 1  # 0..2
player_target_lane = 1  # target lane for smooth movement
player_x = 0.0  # current x position for smooth lane transitions
player_y = -10.0 
player_z = 0.0

# Lane transition animation
lane_transition_speed = 300.0  # units per second
lane_transition_t = 0.0  # 0.0 = complete, 1.0 = just started

hop_charges = 3
max_hop_charges = 5
in_air = False
vertical_v = 0.0
jump_height = 120.0   # peak height in world units (same as before)
gravity = 1200.0      # units/sec^2 — increase this to make drop faster

scroll_speed = 220.0  # base world scroll speed (units/sec)

distance_travelled = 0.0
high_score = 0.0

# power-ups active state
active = {
    'nitro_until': 0.0,
    'slow_until': 0.0,
    'shield_hits': 0,
    'mult_until': 0.0,
    'magnet_until': 0.0,
}
ROAD_LENGTH = 40000  # Length of the road
ROAD_WIDTH = 400  # Width of the road

# Human (player) params
human_x = 0
human_y = -ROAD_LENGTH/2 + 200  # Start near the beginning of the road
human_z = 0
human_rotation = 0

# Environment objects
trees = []
buildings = []

time_scale = 1.0

obstacles = []  # list of dicts: { 'lane': int, 'y': float, 'type': 'car'|'barrier' }
pickups = []    # list of dicts: { 'lane': int, 'y': float, 'kind': 'nitro'|'slow'|'shield'|'jump'|'mult'|'magnet' }

rng = random.Random(rand_var)
spawn_cooldown = 0.0

last_time = None

# Reuse a single quadric for GLU primitives
_quadric = None

def _get_quadric():
    global _quadric
    if _quadric is None:
        _quadric = gluNewQuadric()
    return _quadric


def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1,1,1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


# ---------------- Rendering helpers (only allowed primitives) ----------------

def draw_cylinder(radius_base, radius_top, height, slices=16, stacks=1):
    gluCylinder(_get_quadric(), radius_base, radius_top, height, slices, stacks)


def draw_sphere(radius, slices=16, stacks=16):
    gluSphere(_get_quadric(), radius, slices, stacks)
    
def draw_rectangular_cuboid(width, height, depth):
    """
    Draw a rectangular cuboid with specified width, height, and depth.
    Origin is at the center of the cuboid.
    """
    # Calculate half dimensions
    half_width = width / 2
    half_height = height / 2
    half_depth = depth / 2
    
    # Front face
    glBegin(GL_QUADS)
    glVertex3f(-half_width, -half_height, half_depth)  # Bottom left
    glVertex3f(half_width, -half_height, half_depth)   # Bottom right
    glVertex3f(half_width, half_height, half_depth)    # Top right
    glVertex3f(-half_width, half_height, half_depth)   # Top left
    glEnd()
    
    # Back face
    glBegin(GL_QUADS)
    glVertex3f(-half_width, -half_height, -half_depth) # Bottom left
    glVertex3f(half_width, -half_height, -half_depth)  # Bottom right
    glVertex3f(half_width, half_height, -half_depth)   # Top right
    glVertex3f(-half_width, half_height, -half_depth)  # Top left
    glEnd()
    
    # Top face
    glBegin(GL_QUADS)
    glVertex3f(-half_width, half_height, half_depth)   # Front left
    glVertex3f(half_width, half_height, half_depth)    # Front right
    glVertex3f(half_width, half_height, -half_depth)   # Back right
    glVertex3f(-half_width, half_height, -half_depth)  # Back left
    glEnd()
    
    # Bottom face
    glBegin(GL_QUADS)
    glVertex3f(-half_width, -half_height, half_depth)  # Front left
    glVertex3f(half_width, -half_height, half_depth)   # Front right
    glVertex3f(half_width, -half_height, -half_depth)  # Back right
    glVertex3f(-half_width, -half_height, -half_depth) # Back left
    glEnd()
    
    # Right face
    glBegin(GL_QUADS)
    glVertex3f(half_width, -half_height, half_depth)   # Bottom front
    glVertex3f(half_width, -half_height, -half_depth)  # Bottom back
    glVertex3f(half_width, half_height, -half_depth)   # Top back
    glVertex3f(half_width, half_height, half_depth)    # Top front
    glEnd()
    
    # Left face
    glBegin(GL_QUADS)
    glVertex3f(-half_width, -half_height, half_depth)  # Bottom front
    glVertex3f(-half_width, -half_height, -half_depth) # Bottom back
    glVertex3f(-half_width, half_height, -half_depth)  # Top back
    glVertex3f(-half_width, half_height, half_depth)   # Top front
    glEnd()



def draw_wheel(x, y, z, radius, width, rotation):
    """Draw a wheel with visible rim effect and rotation"""
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(90, 1, 0, 0)  # Orient wheel correctly
    glRotatef(rotation, 0, 0, 1)  # Apply rotation
    
    # Tire (outer cylinder)
    glColor3f(0.1, 0.1, 0.1)  # Black tire
    gluCylinder(_get_quadric(), radius, radius, width, 16, 1)
    
    # Rim (inner cylinder)
    glColor3f(0.8, 0.8, 0.9)  # Chrome rim
    gluCylinder(_get_quadric(), radius-2, radius-2, width+1, 16, 1)
    
    # Spokes effect using disks
    glColor3f(0.6, 0.6, 0.6)  # Gray spokes
    gluDisk(_get_quadric(), 0, radius-4, 16, 1)
    glTranslatef(0, 0, width)
    gluDisk(_get_quadric(), 0, radius-4, 16, 1)
    
    glPopMatrix()
def init_environment():
    global trees, buildings
    
    # Create trees on both sides of the road
    for i in range(-ROAD_LENGTH//2, ROAD_LENGTH//2, 200):  # Trees along the road
        # Left side trees
        trees.append({
            'pos': [-ROAD_WIDTH/2 - 100, i, 0],
            'height': random.randint(100, 150),
            'trunk_radius': random.randint(5, 10),
            'crown_radius': random.randint(30, 50)
        })
        
        # Right side trees
        trees.append({
            'pos': [ROAD_WIDTH/2 + 100, i, 0],
            'height': random.randint(100, 150),
            'trunk_radius': random.randint(5, 10),
            'crown_radius': random.randint(30, 50)
        })
    
    # Create buildings (boxes) on both sides of the road
    for i in range(-ROAD_LENGTH//2, ROAD_LENGTH//2, 400):  # Buildings along the road
        # Left side buildings
        buildings.append({
            'pos': [-ROAD_WIDTH/2 - 250, i, 0],
            'width': random.randint(100, 150),
            'depth': random.randint(100, 150),
            'height': random.randint(150, 300),
            'color': [random.uniform(0.5, 0.9), random.uniform(0.5, 0.9), random.uniform(0.5, 0.9)]
        })
        
        # Right side buildings
        buildings.append({
            'pos': [ROAD_WIDTH/2 + 250, i, 0],
            'width': random.randint(100, 150),
            'depth': random.randint(100, 150),
            'height': random.randint(150, 300),
            'color': [random.uniform(0.5, 0.9), random.uniform(0.5, 0.9), random.uniform(0.5, 0.9)]
        })
def draw_road():
    """
    Draw a road whose lane markings scroll with the world (in sync with distance_travelled).
    Center stripe removed; two inner lane dividers are dashed. Fewer, smoother dashes.
    """
    # Bigger gap = fewer dashes; dash_length shorter than gap for clear gaps
    dash_gap = 160.0
    dash_length = 40.0
    pattern_length = dash_gap + dash_length

    # continuous offset using distance_travelled for smooth movement
    offset = distance_travelled % pattern_length

    # Road surface
    glColor3f(0.2, 0.2, 0.2)  # Dark gray for asphalt
    glBegin(GL_QUADS)
    glVertex3f(-ROAD_WIDTH/2, -ROAD_LENGTH/2, 0)
    glVertex3f(ROAD_WIDTH/2, -ROAD_LENGTH/2, 0)
    glVertex3f(ROAD_WIDTH/2, ROAD_LENGTH/2, 0)
    glVertex3f(-ROAD_WIDTH/2, ROAD_LENGTH/2, 0)
    glEnd()

    # Side continuous lines (left & right)
    glColor3f(1.0, 1.0, 1.0)
    glBegin(GL_QUADS)
    # Left side
    glVertex3f(-ROAD_WIDTH/2, -ROAD_LENGTH/2, 1)
    glVertex3f(-ROAD_WIDTH/2 + 5, -ROAD_LENGTH/2, 1)
    glVertex3f(-ROAD_WIDTH/2 + 5, ROAD_LENGTH/2, 1)
    glVertex3f(-ROAD_WIDTH/2, ROAD_LENGTH/2, 1)
    # Right side
    glVertex3f(ROAD_WIDTH/2 - 5, -ROAD_LENGTH/2, 1)
    glVertex3f(ROAD_WIDTH/2, -ROAD_LENGTH/2, 1)
    glVertex3f(ROAD_WIDTH/2, ROAD_LENGTH/2, 1)
    glVertex3f(ROAD_WIDTH/2 - 5, ROAD_LENGTH/2, 1)
    glEnd()

    # Draw lane dividers (two dashed lines) and move them using offset
    lane_width = ROAD_WIDTH / 3
    half_len = ROAD_LENGTH / 2

    # compute how many pattern steps needed to cover visible road (+buffer)
    num_steps = int(ROAD_LENGTH / pattern_length) + 6
    start_i = -3

    for i in range(start_i, num_steps):
        # position of this dash segment (moves as distance_travelled increases)
        line_pos = -half_len + i * pattern_length + offset

        # only draw dashes that are within a small buffer of the visible road
        if line_pos < -half_len - pattern_length or line_pos > half_len + pattern_length:
            continue

        # left divider dash
        glColor3f(1.0, 1.0, 1.0)
        glBegin(GL_QUADS)
        glVertex3f(-lane_width/2 - 3.0, line_pos, 1)
        glVertex3f(-lane_width/2 + 3.0, line_pos, 1)
        glVertex3f(-lane_width/2 + 3.0, line_pos + dash_length, 1)
        glVertex3f(-lane_width/2 - 3.0, line_pos + dash_length, 1)
        glEnd()

        # right divider dash
        glBegin(GL_QUADS)
        glVertex3f(lane_width/2 - 3.0, line_pos, 1)
        glVertex3f(lane_width/2 + 3.0, line_pos, 1)
        glVertex3f(lane_width/2 + 3.0, line_pos + dash_length, 1)
        glVertex3f(lane_width/2 - 3.0, line_pos + dash_length, 1)
        glEnd()

    # Start line (unchanged)
    glColor3f(1, 1, 0)  # Yellow
    glBegin(GL_QUADS)
    glVertex3f(-ROAD_WIDTH/2, -half_len + 100, 1)
    glVertex3f(ROAD_WIDTH/2, -half_len + 100, 1)
    glVertex3f(ROAD_WIDTH/2, -half_len + 110, 1)
    glVertex3f(-ROAD_WIDTH/2, -half_len + 110, 1)
    glEnd()

    # Finish line (unchanged)
    glColor3f(1, 0, 0)  # Red
    glBegin(GL_QUADS)
    glVertex3f(-ROAD_WIDTH/2, half_len - 100, 1)
    glVertex3f(ROAD_WIDTH/2, half_len - 100, 1)
    glVertex3f(ROAD_WIDTH/2, half_len - 90, 1)
    glVertex3f(-ROAD_WIDTH/2, half_len - 90, 1)
    glEnd()

def draw_environment():
    """
    Draw all environment objects (trees, buildings).
    """
    global trees, buildings
    
    # Draw all trees
    for tree in trees:
        draw_tree(tree['pos'][0], tree['pos'][1], tree['pos'][2], 
                 tree['height'], tree['trunk_radius'], tree['crown_radius'])
    
    # Draw all buildings
    for building in buildings:
        draw_building(building['pos'][0], building['pos'][1], building['pos'][2],
                     building['width'], building['depth'], building['height'], 
                     building['color'])
        
        
def draw_tree(x, y, z, trunk_height, trunk_radius, crown_radius):
    # Draw trunk (brown cylinder) using shared quadric
    glPushMatrix()
    glColor3f(0.55, 0.27, 0.07)  # Brown color
    glTranslatef(x, y, z)
    # trunk grows along +Z
    glRotatef(0, 1, 0, 0)
    gluCylinder(_get_quadric(), trunk_radius, trunk_radius, trunk_height, 10, 10)
    glPopMatrix()

    # Draw crown (green sphere) using shared quadric
    glPushMatrix()
    glColor3f(0.0, 0.5, 0.0)  # Green color
    glTranslatef(x, y, z + trunk_height)
    gluSphere(_get_quadric(), crown_radius, 10, 10)
    glPopMatrix()

# Draw a building (box)
def draw_building(x, y, z, width, depth, height, color):
    glPushMatrix()
    glColor3f(color[0], color[1], color[2])
    glTranslatef(x, y, z + height/2)  # Center at the bottom of the building
    draw_rectangular_cuboid(width, depth, height)
    glPopMatrix()

#SAIF PART
def draw_bike():
    glPushMatrix()

    # Bike position and lean
    if 'player_x' in globals() and 'lane_transition_t' in globals() and lane_transition_t > 0.0:
        current_x = player_x
    else:
        current_x = LANES_X[player_lane]
    glTranslatef(current_x, player_y, player_z)

    wheel_rotation = (distance_travelled * 2.5) % 360.0
    banking_angle = 0.0
    if 'lane_transition_t' in globals() and lane_transition_t > 0.0:
        direction = 1.0 if player_target_lane > player_lane else -1.0
        t = 1.0 - lane_transition_t
        banking_angle = direction * 15.0 * t
    glRotatef(banking_angle, 0, 0, 1)

    # Wheels
    wheel_radius = 16
    wheel_width = 8

    # front wheel
    glPushMatrix()
    glTranslatef(-5, -32, wheel_radius)
    glRotatef(90, 0, 1, 0)
    glRotatef(wheel_rotation, 0, 0, 1)
    glColor3f(0.05, 0.05, 0.05)
    draw_cylinder(wheel_radius, wheel_radius, wheel_width)
    glColor3f(0.85, 0.85, 0.9)
    draw_cylinder(wheel_radius-3, wheel_radius-3, wheel_width+1)
    glColor3f(0.7, 0.7, 0.75)
    for i in range(5):
        glPushMatrix()
        glRotatef(i * 72, 0, 0, 1)
        glTranslatef(wheel_radius*0.3, 0, wheel_width*0.5)
        glRotatef(90, 0, 1, 0)
        draw_cylinder(0.8, 0.8, wheel_radius*0.6)
        glPopMatrix()
    glPopMatrix()

    # rear wheel
    glPushMatrix()
    glTranslatef(-5, 32, wheel_radius)
    glRotatef(90, 0, 1, 0)
    glRotatef(wheel_rotation, 0, 0, 1)
    glColor3f(0.05, 0.05, 0.05)
    draw_cylinder(wheel_radius+2, wheel_radius+2, wheel_width+2)
    glColor3f(0.85, 0.85, 0.9)
    draw_cylinder(wheel_radius-1, wheel_radius-1, wheel_width+3)
    glColor3f(0.7, 0.7, 0.75)
    for i in range(5):
        glPushMatrix()
        glRotatef(i * 72, 0, 0, 1)
        glTranslatef(wheel_radius*0.3, 0, wheel_width*0.5)
        glRotatef(90, 0, 1, 0)
        draw_cylinder(0.8, 0.8, wheel_radius*0.6)
        glPopMatrix()
    glPopMatrix()

    # Frame backbone
    glColor3f(0.18, 0.18, 0.22)
    glPushMatrix()
    glTranslatef(0, 0, wheel_radius + 8)
    glRotatef(90, 0, 0, 0)
    draw_cylinder(3.5, 3.5, 64, 16)
    glPopMatrix()

    # shamner frame 2ta
    glColor3f(0.22, 0.22, 0.28)
    glPushMatrix()
    glTranslatef(-6, -18, wheel_radius + 4)
    glRotatef(35, 1, 0, 0)
    draw_cylinder(2.2, 2.2, 28)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(6, -18, wheel_radius + 4)
    glRotatef(35, 1, 0, 0)
    draw_cylinder(2.2, 2.2, 28)
    glPopMatrix()

    # picher exhaust
    glColor3f(0.7, 0.9, 1.0)
    glPushMatrix()
    glTranslatef(-6, 18, wheel_radius + 4)
    glRotatef(-35, 1, 0, 0)
    draw_cylinder(2.2, 2.2, 28)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(6, 18, wheel_radius + 4)
    glRotatef(-35, 1, 0, 0)
    draw_cylinder(2.2, 2.2, 28)
    glColor3f(0.7, 0.9, 1.0)
    glPopMatrix()

    # Fuel tank
    glColor3f(1.0, 0.55, 0.0)
    glPushMatrix()
    glTranslatef(0,-8,wheel_radius + 18)
    glRotatef(90, 1, 0, 0)
    glRotatef(90, 0, 1, 0)
    glScalef(1.5, 0.7, 0.6)
    draw_sphere(13)
    glPopMatrix()

    # horizontal handlebar 
    glColor3f(0.05, 0.05, 0.05)
    glPushMatrix()
    glTranslatef(-20, -28, wheel_radius + 26)  # position
    glRotatef(90, 0, 1, 0)
    draw_cylinder(1.5, 1.5, 40, 12) #length height girth
    glPopMatrix()

    # compute handlebar grip world positions (match cylinder endpoints)
    left_hand_pos = (-20.0, -28.0, wheel_radius + 26.0)
    right_hand_pos = (20.0, -28.0, wheel_radius + 26.0)

    # Seat base
    glColor3f(0.08, 0.08, 0.12)
    glPushMatrix()
    glTranslatef(0, 14, wheel_radius + 10)
    glScalef(1.2, 0.7, 0.5)
    glutSolidCube(16)
    glPopMatrix()

    # Seat padding
    glColor3f(0.18, 0.18, 0.22)
    glPushMatrix()
    glTranslatef(0, 14, wheel_radius + 13)
    glScalef(1.0, 0.5, 0.3)
    glutSolidCube(14)
    glPopMatrix()

    # Front fairing (blue headlight)
    glPushMatrix()
    glColor3f(0.8, 0.35, 0.0)
    glTranslatef(0, -32, wheel_radius + 20)
    glScalef(1.2, 0.7, 0.8)
    draw_sphere(10)
    glPopMatrix()

    # Headlight
    glPushMatrix()
    glColor3f(1.0, 1.0, 0.8)
    glTranslatef(0, -36, wheel_radius + 20)
    glScalef(0.5, 0.5, 0.5)
    draw_sphere(4)
    glPopMatrix()

    glPopMatrix()


def draw_obstacle(o):
    # Draw at lane center, z on ground plane
    x = LANES_X[o['lane']]
    y = o['y']
    glPushMatrix()
    glTranslatef(x, y, 0)
    if o['type'] == 'car':
        glPushMatrix()
        # rotate so vehicle 
        glRotatef(90, 0, 0, 1)
        # scale up the car
        s = 100.0 / 220.0  # previously 40.0/220.0, increased for a bigger car
        glScalef(s, s, s)
        draw_vehicle_model()
        glPopMatrix()
    else:  # barrier
        glColor3f(0.9, 0.1, 0.1)  # Bright red for barriers
        glutSolidCube(30)
    glPopMatrix()


def draw_pickup(p, t):
    x = LANES_X[p['lane']]
    y = p['y']
    # bob and spin around Z
    bob = math.sin(t * 2.0) * 4.0
    spin = (t * 90.0) % 360.0
    glPushMatrix()
    glTranslatef(x, y, 12 + bob)
    glRotatef(spin, 0, 0, 1)

    kind = p['kind']
    if kind == 'nitro':
        glColor3f(0.0, 0.6, 1.0)  # Blue for nitro
        glRotatef(90, 1, 0, 0)
        draw_cylinder(5, 5, 18)
        glPushMatrix()
        glTranslatef(0, 0, 0)
        draw_sphere(5)
        glTranslatef(0, 0, 18)
        draw_sphere(5)
        glPopMatrix()
    elif kind == 'slow':
        glColor3f(0.0, 1.0, 0.8)  # Cyan for slow motion
        draw_sphere(8)
    elif kind == 'shield':
        glColor3f(0.0, 0.8, 0.0)  # Green for shield
        draw_sphere(8)
    elif kind == 'jump':
        glColor3f(0.8, 0.0, 1.0)  # Purple for jump boost
        glutSolidCube(14)
    elif kind == 'mult':
        glColor3f(1.0, 0.4, 0.0)  # Orange for multiplier
        draw_sphere(9)
    else:  # magnet
        glColor3f(0.6, 0.0, 0.8)  # Dark purple for magnet
        glRotatef(90, 1, 0, 0)
        draw_cylinder(3, 3, 14)
        glTranslatef(0, 0, 14)
        draw_cylinder(3, 3, 14)
    glPopMatrix()


# --- Vehicle model (integrated from car yasir) ---
def draw_vehicle_wheel(radius=22.0, thickness=8.0):
    """Disk-like wheel (cylinder) using shared quadric"""
    quad = _get_quadric()
    glPushMatrix()
    glColor3f(0.1, 0.1, 0.1)
    gluCylinder(quad, radius, radius, thickness, 24, 1)
    # front face
    glColor3f(0.2, 0.2, 0.2)
    gluDisk(quad, 0.0, radius, 24, 1)
    # back face
    glPushMatrix()
    glTranslatef(0, 0, thickness)
    gluDisk(quad, 0.0, radius, 24, 1)
    glPopMatrix()
    glPopMatrix()

def draw_vehicle_model():
    """
    Clean 3D car model adapted to use the shared quadric and GLUT primitives.
    Model is centered at origin; call sites can scale/translate as needed.
    """
    # Car dimensions (logical)
    L, W, H = 220.0, 120.0, 50.0   # body length/width/height
    roofL, roofW, roofH = 120.0, 70.0, 32.0  # roof size
    wheel_radius = 22.0
    wheel_thickness = 28.0

    # Body
    glPushMatrix()
    glColor3f(0.12, 0.35, 0.85)
    glTranslatef(0.0, 0.0, H/2)
    glScalef(L/100.0, W/100.0, H/100.0)
    glutSolidCube(100.0)
    glPopMatrix()

    # Roof
    glPushMatrix()
    glColor3f(0.10, 0.25, 0.65)
    glTranslatef(10.0, 0.0, H + roofH/2)
    glScalef(roofL/100.0, roofW/100.0, roofH/100.0)
    glutSolidCube(100.0)
    glPopMatrix()

    # Windshield (simple quad)
    glPushMatrix()
    glColor3f(0.6, 0.85, 0.95)
    glBegin(GL_QUADS)
    ws_x = 10.0 + roofL/2 + 2.0
    glVertex3f(ws_x, -roofW/2, H)
    glVertex3f(ws_x,  roofW/2, H)
    roof_front_x = 10.0 + roofL/2
    glVertex3f(roof_front_x,  roofW/2, H + roofH)
    glVertex3f(roof_front_x, -roofW/2, H + roofH)
    glEnd()
    glPopMatrix()

    # Headlights
    headlight_z = 18.0
    headlight_y = W/2 - 18.0
    headlight_x = L/2 + 6.0
    for sgn in (-1, 1):
        glPushMatrix()
        glTranslatef(headlight_x, sgn*headlight_y, headlight_z)
        glColor3f(1.0, 0.95, 0.5)
        gluSphere(_get_quadric(), 7.0, 12, 8)
        glPopMatrix()

    # Taillights
    tail_x = -L/2 - 6.0
    tail_y = W/2 - 18.0
    tail_z = 18.0
    for sgn in (-1, 1):
        glPushMatrix()
        glTranslatef(tail_x, sgn*tail_y, tail_z)
        glScalef(0.18, 0.18, 0.18)
        glColor3f(0.9, 0.05, 0.05)
        glutSolidCube(30.0)
        glPopMatrix()

    # Wheels (4)
    wx = L/2 - 32.0
    wz_pos = W/2 + wheel_thickness/2
    wz = wheel_radius - 6.0
    for sx in (-1, 1):  # front/rear
        for sy in (-1, 1):  # left/right
            glPushMatrix()
            y_offset = sy * wz_pos
            glTranslatef(sx*wx, y_offset, wz)
            # orient wheel so flat face points outward (match original)
            if sy > 0:
                glRotatef(90, 1, 0, 0)
            else:
                glRotatef(-90, 1, 0, 0)
            draw_vehicle_wheel(radius=wheel_radius, thickness=wheel_thickness)
            glPopMatrix()

# ---------------- Game logic ----------------

def reset_game():
    global player_lane, player_y, player_z, hop_charges, hop_t, distance_travelled
    global active, time_scale, obstacles, pickups, spawn_cooldown
    player_lane = 1
    player_y = -50.0  
    player_z = 0.0
    hop_charges = 3
    hop_t = 0.0
    distance_travelled = 0.0
    active = {
        'nitro_until': 0.0,
        'slow_until': 0.0,
        'shield_hits': 0,
        'mult_until': 0.0,
        'magnet_until': 0.0,
    }
    time_scale = 1.0
    obstacles = []
    pickups = []
    spawn_cooldown = 0.0


def check_collisions():
    global obstacles, pickups, hop_charges, distance_travelled, high_score
    # Bike collision bounds simplified by lane and y-distance threshold
    hit_threshold = 30.0

    # Obstacles
    remaining = []
    collided = False
    for o in obstacles:
        if o['lane'] == player_lane and abs(o['y'] - player_y) < hit_threshold:
            collided = True
        else:
            remaining.append(o)
    obstacles = remaining

    if collided and player_z <= 1.0:
        if active['shield_hits'] > 0:
            active['shield_hits'] = 0
        else:
            # On hit: update high score and reset run
            if distance_travelled > high_score:
                high_score = distance_travelled
            reset_game()
            return

    # Pickups
    remaining_p = []
    for p in pickups:
        attracted = False
        if time.perf_counter() < active['magnet_until'] and p['lane'] == player_lane:
            # Pull toward player on y (no extra GL calls; just logic)
            if p['y'] < player_y:
                p['y'] = min(player_y, p['y'] + 120.0 * (1.0))
            elif p['y'] > player_y:
                p['y'] = max(player_y, p['y'] - 120.0 * (1.0))
            attracted = True
        if p['lane'] == player_lane and abs(p['y'] - player_y) < hit_threshold:
            apply_pickup(p['kind'])
        else:
            remaining_p.append(p)
    pickups = remaining_p


def apply_pickup(kind):
    now = time.perf_counter()
    global time_scale, hop_charges
    if kind == 'nitro':
        active['nitro_until'] = max(active['nitro_until'], now + 4.0)
    elif kind == 'slow':
        time_scale = 0.5
        active['slow_until'] = now + 3.0
    elif kind == 'shield':
        active['shield_hits'] = 1
    elif kind == 'jump':
        hop_charges = min(max_hop_charges, hop_charges + 1)
    elif kind == 'mult':
        active['mult_until'] = max(active['mult_until'], now + 8.0)
    elif kind == 'magnet':
        active['magnet_until'] = max(active['magnet_until'], now + 6.0)


def late_update_time_scale():
    global time_scale
    if time.perf_counter() >= active['slow_until']:
        time_scale = 1.0


def update_game(dt):
    global spawn_cooldown, player_z, distance_travelled, player_x, lane_transition_t, player_lane, player_target_lane
    global in_air, vertical_v, trees, buildings

    now = time.perf_counter()

    # effective_speed calculation unchanged...
    effective_speed = scroll_speed
    if now < active['nitro_until']:
        effective_speed *= 1.7

    # lane transition (unchanged)...
    if 'lane_transition_t' in globals() and lane_transition_t > 0.0:
        lane_transition_t = max(0.0, lane_transition_t - dt * 300.0 / 150.0)
        t = 1.0 - lane_transition_t
        ease_t = t * t * (3.0 - 2.0 * t)
        start_x = LANES_X[player_lane]
        end_x = LANES_X[player_target_lane]
        player_x = start_x + (end_x - start_x) * ease_t
        if lane_transition_t <= 0.0:
            player_lane = player_target_lane
            player_x = LANES_X[player_lane]

    # advance world (obstacles/pickups)
    for o in obstacles:
        o['y'] += effective_speed * dt
    for p in pickups:
        p['y'] += effective_speed * dt

    # Move environment (trees & buildings) with the same scroll so they pass by
    for tr in trees:
        tr['pos'][1] += effective_speed * dt
        # wrap around when they go past the far end so environment is endless
        if tr['pos'][1] > (ROAD_LENGTH/2 + 200):
            tr['pos'][1] -= ROAD_LENGTH
    for b in buildings:
        b['pos'][1] += effective_speed * dt
        if b['pos'][1] > (ROAD_LENGTH/2 + 400):
            b['pos'][1] -= ROAD_LENGTH

    obstacles[:] = [o for o in obstacles if o['y'] < 700]
    pickups[:] = [p for p in pickups if p['y'] < 700]

    # spawn logic unchanged...
    spawn_cooldown -= dt
    if spawn_cooldown <= 0.0:
        lane = rng.randrange(0, 3)
        if rng.random() < 0.7:
            obstacles.append({'lane': lane, 'y': -900.0, 'type': ('car' if rng.random() < 0.75 else 'barrier')})
        else:
            kind = rng.choice(['nitro','slow','shield','jump','mult','magnet'])
            pickups.append({'lane': lane, 'y': -900.0, 'kind': kind})
        spawn_cooldown = max(0.4, 1.2 - distance_travelled/3000.0)

    # PHYSICS JUMP: update vertical velocity and position
    if in_air:
        vertical_v -= gravity * dt            # gravity accelerates downward
        player_z += vertical_v * dt           # integrate velocity
        if player_z <= 0.0:                   # landed
            player_z = 0.0
            in_air = False
            vertical_v = 0.0
    else:
        player_z = 0.0
        # collisions only when grounded
        check_collisions()

    # scoring and rest unchanged...
    gain = effective_speed * dt
    if now < active['mult_until']:
        gain *= 2.0
    distance_travelled += gain

    late_update_time_scale()


# ---------------- Input handlers ----------------

def keyboardListener(key, x, y):
    global hop_charges, in_air, vertical_v, high_score, camera_mode
    k = key.decode('utf-8').lower()
    if k == ' ':
        # start jump using physics impulse
        if hop_charges > 0 and not in_air:
            hop_charges -= 1
            # set initial upward velocity to reach desired jump_height: vy = sqrt(2*g*h)
            vertical_v = math.sqrt(2.0 * gravity * jump_height)
            in_air = True
    elif k == 'r':
        if distance_travelled > high_score:
            high_score = distance_travelled
        reset_game()
    elif k == 'f':
        camera_mode = "first_person" if camera_mode == "third_person" else "third_person"
        print(f"Camera mode: {camera_mode}")
    elif k in ('w','a','s','d'):
        key_down[k] = True
        _update_free_look_state()

def keyboardUpListener(key, x, y):
    k = key.decode('utf-8').lower()
    if k in ('w','a','s','d'):
        key_down[k] = False
        _update_free_look_state()

def _update_free_look_state():
    global free_look_enabled
    free_look_enabled = key_down['w'] or key_down['a'] or key_down['s'] or key_down['d']


def specialKeyListener(key, x, y):
    global camera_pos, player_lane, player_target_lane, lane_transition_t
    cx, cy, cz = camera_pos
    if key == GLUT_KEY_LEFT and player_target_lane < 2 and lane_transition_t <= 0.0:
        player_target_lane += 1
        lane_transition_t = 1.0
    if key == GLUT_KEY_RIGHT and player_target_lane > 0 and lane_transition_t <= 0.0:
        player_target_lane -= 1
        lane_transition_t = 1.0
    camera_pos = (cx, cy, cz)


def mouseListener(button, state, x, y):
    # Not used for gameplay in this skeleton
    return


# ---------------- Camera and loop ----------------

def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, 1.25, 0.1, 1500)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    if camera_mode == "third_person":
        # Target: bike position (lane-aligned)
        target_x = player_x if lane_transition_t > 0.0 else LANES_X[player_lane]
        target_y = player_y
        target_z = player_z + 20  # aim slightly above bike center

        # Orbit parameters (feel free to tune)
        base_dist = 300.0
        base_height = 260.0

        # Convert persistent yaw/pitch (degrees) to world-space offset around target
        cy = math.cos(math.radians(free_look_yaw))
        sy = math.sin(math.radians(free_look_yaw))
        cp = math.cos(math.radians(free_look_pitch))
        sp = math.sin(math.radians(free_look_pitch))

        # Horizontal ring offset with yaw; -Y is forward in this world
        off_x =  base_dist * (-sy) * cp
        off_y =  base_dist * (-cy) * cp   # more negative => more forward
        off_z =  base_height + base_dist * sp

        eye_x = target_x + off_x
        eye_y = target_y + off_y
        eye_z = target_z + off_z

        gluLookAt(eye_x, eye_y, eye_z, target_x, target_y, target_z, 0, 0, 1)

    else:  # first_person (unchanged)
        bike_x = player_x if lane_transition_t > 0.0 else LANES_X[player_lane]
        bike_y = player_y
        bike_z = player_z

        eye_x = bike_x
        eye_y = bike_y + 22
        eye_z = bike_z + 28

        center_x = eye_x
        center_y = eye_y - 140   # look down the road (-Y)
        center_z = eye_z - 8     # slight downward tilt

        gluLookAt(eye_x, eye_y, eye_z, center_x, center_y, center_z, 0, 0, 1)


def idle():
    global last_time, free_look_yaw, free_look_pitch
    now = time.perf_counter()
    if last_time is None:
        last_time = now
        glutPostRedisplay()
        return
    dt = (now - last_time) * time_scale
    last_time = now
    if dt > 0.05:
        dt = 0.05

    # Third-person free-look only
    if camera_mode == "third_person" and free_look_enabled:
        yaw_speed = 90.0      # deg/s
        pitch_speed = 75.0    # deg/s
        if key_down['a']:
            free_look_yaw -= yaw_speed * dt
        if key_down['d']:
            free_look_yaw += yaw_speed * dt
        if key_down['w']:
            free_look_pitch += pitch_speed * dt
        if key_down['s']:
            free_look_pitch -= pitch_speed * dt
        # clamp pitch to avoid flipping the up vector
        if free_look_pitch > 85.0: free_look_pitch = 85.0
        if free_look_pitch < -85.0: free_look_pitch = -85.0

    update_game(dt)
    glutPostRedisplay()


# ---------------- Frame rendering ----------------


def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, 1000, 800)

    setupCamera()

    # Optional point marker
    glPointSize(4)
    glBegin(GL_POINTS)
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, 0)
    glEnd()

    # Draw ground/road
    draw_road()
    draw_environment()

    
    t = time.perf_counter()
    draw_bike()  

    # Draw obstacles and pickups
    for o in sorted(obstacles, key=lambda e: e['y']):
        draw_obstacle(o)
    for p in sorted(pickups, key=lambda e: e['y']):
        draw_pickup(p, t)

    # HUD
    draw_text(10, 770, f"Distance: {int(distance_travelled)}  High: {int(high_score)}")
    draw_text(10, 740, f"Lane: {player_lane+1}/3  Hops: {hop_charges}")
    draw_text(10, 710, f"Camera: {camera_mode.upper()} (Press F to toggle)")
    now = time.perf_counter()
    statuses = []
    if now < active['nitro_until']:
        statuses.append('NITRO')
    if now < active['slow_until']:
        statuses.append('SLOW')
    if active['shield_hits'] > 0:
        statuses.append('SHIELD')
    if now < active['mult_until']:
        statuses.append('x2')
    if now < active['magnet_until']:
        statuses.append('MAG')
    draw_text(10, 680, " ".join(statuses) if statuses else "")

    glutSwapBuffers()


# ---------------- Main ----------------

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"CSE423 Endless Runner (OpenGL) - Enhanced Bike Model")

    # create GL resources after context exists
    _get_quadric()

    # ensure depth testing and a visible clear color are enabled
    glEnable(GL_DEPTH_TEST)
    glClearColor(0.2, 0.6, 0.9, 1.0)

    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutKeyboardUpFunc(keyboardUpListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)
    
    print("Enhanced Bike Simulation Controls:")
    print("Arrow Keys: Lane switching (left/right)")
    print("Spacebar: Hop/Jump")
    print("F: Toggle camera view (third-person/first-person)")
    print("R: Reset game")

    glutMainLoop()


if __name__ == "__main__":
    init_environment()
    main()
