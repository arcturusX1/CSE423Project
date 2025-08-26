from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

import time
import random
import math

# Camera-related variables
camera_pos = (0, 200, 300)  # Closer behind the bike for better perspective

fovY = 90  # Narrower FOV for better 3D perspective
GRID_LENGTH = 600  # Length of grid lines
rand_var = 423

#  Gameplay globals 
LANES_X = (-150.0, 0.0, 150.0)
player_lane = 1  # 0..2
player_target_lane = 1  # target lane for smooth movement
player_x = 0.0  # current x position for smooth lane transitions
player_y = -50.0 
player_z = 0.0

# Lane transition animation
lane_transition_speed = 300.0  # units per second
lane_transition_t = 0.0  # 0.0 = complete, 1.0 = just started

hop_charges = 2
max_hop_charges = 3
hop_duration = 1.2  # Increased from 0.6 to 1.2 seconds
hop_t = 0.0

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


def draw_bike():
    # Bike positioned with its origin at ground contact point under the seat
    glPushMatrix()
    
    # Use smooth x position if transitioning, otherwise use current lane
    if 'player_x' in globals() and 'lane_transition_t' in globals() and lane_transition_t > 0.0:
        current_x = player_x
    else:
        current_x = LANES_X[player_lane]
    
    glTranslatef(current_x, player_y, player_z)
    
    # Calculate wheel rotation based on distance travelled (forward rotation)
    wheel_rotation = (distance_travelled * 1.5) % 360.0  # Reduced from 4.0 to 1.5 for more realistic rotation
    
    # Calculate banking angle for turns (lean into turns)
    banking_angle = 0.0
    if 'lane_transition_t' in globals() and lane_transition_t > 0.0:
        # Calculate direction of movement
        direction = 1.0 if player_target_lane > player_lane else -1.0
        # Banking angle based on transition progress
        t = 1.0 - lane_transition_t
        banking_angle = direction * 15.0 * t  # max 15 degrees
    
    # Apply banking rotation
    glRotatef(banking_angle, 0, 0, 1)

    # Main frame: simple black square body
    glColor3f(0.0, 0.0, 0.0)  # Black
    glPushMatrix()
    glTranslatef(0, 0, 10)
    glutSolidCube(20)  # Simple square
    glPopMatrix()

    # Fuel tank: bright blue sphere in front-top
    glPushMatrix()
    glColor3f(0.1, 0.8, 1.0)
    glTranslatef(0, 6, 22)
    glScalef(0.8, 0.5, 0.8)
    draw_sphere(12)
    glPopMatrix()

    # Seat: bright green rectangular seat
    glPushMatrix()
    glColor3f(0.2, 0.9, 0.3)
    glTranslatef(0, -8, 18)
    glScalef(0.9, 0.3, 0.6)
    glutSolidCube(18)
    glPopMatrix()

    # Seat cushion - lighter green
    glPushMatrix()
    glColor3f(0.4, 1.0, 0.5)
    glTranslatef(0, -8, 20)
    glScalef(0.7, 0.2, 0.4)
    glutSolidCube(16)
    glPopMatrix()

    # Headlight: modern LED style - bright white
    glPushMatrix()
    glColor3f(1.0, 1.0, 1.0)
    glTranslatef(0, 26, 20)
    glScalef(0.8, 0.8, 0.6)
    draw_sphere(7)
    glPopMatrix()

    # Headlight housing - dark gray
    glPushMatrix()
    glColor3f(0.3, 0.3, 0.35)
    glTranslatef(0, 26, 20)
    glScalef(1.1, 1.1, 0.8)
    draw_sphere(7)
    glPopMatrix()

    # Front fork: sleek suspension - chrome
    glPushMatrix()
    glColor3f(0.8, 0.8, 0.9)
    glTranslatef(0, 24, 12)
    glRotatef(90, 1, 0, 0)
    draw_cylinder(1.8, 1.8, 28)
    glPopMatrix()

    # Rear suspension: modern mono-shock - chrome
    glPushMatrix()
    glColor3f(0.8, 0.8, 0.9)
    glTranslatef(0, -22, 12)
    glRotatef(90, 1, 0, 0)
    draw_cylinder(1.5, 1.5, 22)
    glPopMatrix()

    # Exhaust pipe: sporty dual exhaust - dark metal
    glPushMatrix()
    glColor3f(0.4, 0.4, 0.45)
    glTranslatef(-8, -18, 8)
    glRotatef(90, 1, 0, 0)
    draw_cylinder(1.2, 1.2, 18)
    glPopMatrix()
    glPushMatrix()
    glColor3f(0.4, 0.4, 0.45)
    glTranslatef(8, -18, 8)
    glRotatef(90, 1, 0, 0)
    draw_cylinder(1.2, 1.2, 18)
    glPopMatrix()

    # Wheels: modern sport bike wheels with PROPER forward rotation
    wheel_radius = 18
    wheel_width = 10

    # Front wheel - bright orange with chrome rim
    glPushMatrix()
    glColor3f(1.0, 0.6, 0.1)
    glTranslatef(0, 28, wheel_radius)
    glRotatef(90, 0, 1, 0)  # FIXED: align along Z-axis (vertical) instead of Y
    glRotatef(wheel_rotation, 0, 0, 1)  # rotate around Z for proper forward rotation
    draw_cylinder(wheel_radius, wheel_radius, wheel_width)
    glPopMatrix()
    
    # Front wheel rim - chrome
    glPushMatrix()
    glColor3f(0.8, 0.8, 0.9)
    glTranslatef(0, 28, wheel_radius)
    glRotatef(90, 0, 1, 0)  # FIXED: same alignment
    glRotatef(wheel_rotation, 0, 0, 1)  # same rotation
    draw_cylinder(wheel_radius-2, wheel_radius-2, wheel_width+1)
    glPopMatrix()

    # Rear wheel - bright purple with chrome rim
    glPushMatrix()
    glColor3f(0.8, 0.3, 1.0)
    glTranslatef(0, -28, wheel_radius)
    glRotatef(90, 0, 1, 0)  # FIXED: same alignment
    glRotatef(wheel_rotation, 0, 0, 1)  # same rotation
    draw_cylinder(wheel_radius, wheel_radius, wheel_width)
    glPopMatrix()
    
    # Rear wheel rim - chrome
    glPushMatrix()
    glColor3f(0.8, 0.8, 0.9)
    glTranslatef(0, -28, wheel_radius)
    glRotatef(90, 0, 1, 0)  # FIXED: same alignment
    glRotatef(wheel_rotation, 0, 0, 1)  # same rotation
    draw_cylinder(wheel_radius-2, wheel_radius-2, wheel_width+1)
    glPopMatrix()

    # Brake discs - metallic gray
    glPushMatrix()
    glColor3f(0.6, 0.6, 0.65)
    glTranslatef(0, 28, wheel_radius-1)
    glRotatef(90, 0, 1, 0)  # FIXED: same alignment
    glRotatef(wheel_rotation, 0, 0, 1)  # same rotation
    draw_cylinder(8, 8, 1)
    glPopMatrix()
    glPushMatrix()
    glColor3f(0.6, 0.6, 0.65)
    glTranslatef(0, -28, wheel_radius-1)
    glRotatef(90, 0, 1, 0)  # FIXED: same alignment
    glRotatef(wheel_rotation, 0, 0, 1)  # same rotation
    draw_cylinder(8, 8, 1)
    glPopMatrix()

    # Side mirrors - chrome
    glPushMatrix()
    glColor3f(0.8, 0.8, 0.9)
    glTranslatef(-12, 22, 22)
    glRotatef(45, 0, 0, 1)
    glutSolidCube(5)
    glPopMatrix()
    glPushMatrix()
    glColor3f(0.8, 0.8, 0.9)
    glTranslatef(12, 22, 22)
    glRotatef(-45, 0, 0, 1)
    glutSolidCube(5)
    glPopMatrix()

    # Tail light - bright red
    glPushMatrix()
    glColor3f(1.0, 0.1, 0.1)
    glTranslatef(0, -32, 20)
    glScalef(0.6, 0.6, 0.4)
    draw_sphere(5)
    glPopMatrix()

    # License plate holder - dark gray
    glPushMatrix()
    glColor3f(0.3, 0.3, 0.35)
    glTranslatef(0, -34, 17)
    glScalef(0.8, 0.1, 0.6)
    glutSolidCube(14)
    glPopMatrix()

    # Front indicators - bright yellow
    glPushMatrix()
    glColor3f(1.0, 1.0, 0.0)
    glTranslatef(-8, 26, 18)
    glScalef(0.4, 0.4, 0.3)
    draw_sphere(4)
    glPopMatrix()
    glPushMatrix()
    glColor3f(1.0, 1.0, 0.0)
    glTranslatef(8, 26, 18)
    glScalef(0.4, 0.4, 0.3)
    draw_sphere(4)
    glPopMatrix()

    # Rear indicators - bright yellow
    glPushMatrix()
    glColor3f(1.0, 1.0, 0.0)
    glTranslatef(-6, -32, 18)
    glScalef(0.4, 0.4, 0.3)
    draw_sphere(4)
    glPopMatrix()
    glPushMatrix()
    glColor3f(1.0, 1.0, 0.0)
    glTranslatef(6, -32, 18)
    glScalef(0.4, 0.4, 0.3)
    draw_sphere(4)
    glPopMatrix()

    # Shield indicator if active - bright gold with glow effect
    if active['shield_hits'] > 0:
        glPushMatrix()
        glColor3f(1.0, 0.8, 0.0)
        glTranslatef(0, 0, 32)
        draw_sphere(8)
        glPopMatrix()
        # Inner shield glow
        glPushMatrix()
        glColor3f(1.0, 0.9, 0.3)
        glTranslatef(0, 0, 32)
        draw_sphere(5)
        glPopMatrix()

    glPopMatrix()


def draw_obstacle(o):
    # Draw at lane center, z on ground plane
    x = LANES_X[o['lane']]
    y = o['y']
    glPushMatrix()
    glTranslatef(x, y, 0)
    if o['type'] == 'car':
        glColor3f(0.9, 0.1, 0.1)  # Bright red for cars
        glutSolidCube(40)
        # simple roof - also red
        glPushMatrix()
        glColor3f(0.7, 0.1, 0.1)  # Darker red for roof
        glTranslatef(0, 0, 20)
        glutSolidCube(20)
        glPopMatrix()
    else:  # barrier
        glColor3f(0.9, 0.1, 0.1)  # Bright red for barriers too
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


# ---------------- Game logic ----------------

def reset_game():
    global player_lane, player_y, player_z, hop_charges, hop_t, distance_travelled
    global active, time_scale, obstacles, pickups, spawn_cooldown
    player_lane = 1
    player_y = -50.0  
    player_z = 0.0
    hop_charges = 2
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
    global spawn_cooldown, player_z, hop_t, distance_travelled, player_x, lane_transition_t, player_lane, player_target_lane

    now = time.perf_counter()

    # Effective speed with nitro
    effective_speed = scroll_speed
    if now < active['nitro_until']:
        effective_speed *= 1.7

    # Smooth lane transition
    if 'lane_transition_t' in globals() and lane_transition_t > 0.0:
        lane_transition_t = max(0.0, lane_transition_t - dt * 300.0 / 150.0)
        t = 1.0 - lane_transition_t  # 0.0 = start, 1.0 = complete
        
        # Smooth easing function for natural movement
        ease_t = t * t * (3.0 - 2.0 * t)  # smoothstep
        
        start_x = LANES_X[player_lane]
        end_x = LANES_X[player_target_lane]
        player_x = start_x + (end_x - start_x) * ease_t
        
        if lane_transition_t <= 0.0:
            player_lane = player_target_lane
            player_x = LANES_X[player_lane]

    # Move world forward (toward camera)
    for o in obstacles:
        o['y'] += effective_speed * dt
    for p in pickups:
        p['y'] += effective_speed * dt

    # Despawn past camera
    obstacles[:] = [o for o in obstacles if o['y'] < 700]
    pickups[:] = [p for p in pickups if p['y'] < 700]

    # Spawn logic
    spawn_cooldown -= dt
    if spawn_cooldown <= 0.0:
        lane = rng.randrange(0, 3)
        if rng.random() < 0.7:
            obstacles.append({'lane': lane, 'y': -900.0, 'type': ('car' if rng.random() < 0.75 else 'barrier')})
        else:
            kind = rng.choice(['nitro','slow','shield','jump','mult','magnet'])
            pickups.append({'lane': lane, 'y': -900.0, 'kind': kind})
        spawn_cooldown = max(0.4, 1.2 - distance_travelled/3000.0)

    # Hop animation (simple parabola)
    if hop_t > 0.0:
        hop_t = max(0.0, hop_t - dt)
        t = 1.0 - (hop_t / hop_duration)  # 0..1
        player_z = 120.0 * (4*t*(1-t))  # Increased height from 70 to 120
    else:
        player_z = 0.0

    # Collisions when not mid-air
    if player_z <= 1.0:
        check_collisions()

    # Scoring
    gain = effective_speed * dt
    if now < active['mult_until']:
        gain *= 2.0
    distance_travelled += gain

    # Restore time scale if slow expired
    late_update_time_scale()


# ---------------- Input handlers ----------------

def keyboardListener(key, x, y):
    global hop_charges, hop_t, high_score
    if key == b' ':
        if hop_charges > 0 and hop_t <= 0.0:
            hop_charges -= 1
            hop_t = hop_duration
    if key == b'r':
        if distance_travelled > high_score:
            high_score = distance_travelled
        reset_game()


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
    x, y, z = camera_pos
    # Look straight ahead from behind the bike, not at the bike itself
    gluLookAt(x, y, z, 0, 0, 0, 0, 0, 1)


def idle():
    global last_time
    now = time.perf_counter()
    if last_time is None:
        last_time = now
        glutPostRedisplay()
        return
    dt = (now - last_time) * time_scale
    last_time = now
    if dt > 0.05:
        dt = 0.05
    update_game(dt)
    glutPostRedisplay()


# ---------------- Frame rendering ----------------

def draw_ground():
    glBegin(GL_QUADS)
    glColor3f(1, 1, 1)
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(0, GRID_LENGTH, 0)
    glVertex3f(0, 0, 0)
    glVertex3f(-GRID_LENGTH, 0, 0)

    glVertex3f(GRID_LENGTH, -GRID_LENGTH, 0)
    glVertex3f(0, -GRID_LENGTH, 0)
    glVertex3f(0, 0, 0)
    glVertex3f(GRID_LENGTH, 0, 0)

    glColor3f(0.7, 0.5, 0.95)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, 0)
    glVertex3f(-GRID_LENGTH, 0, 0)
    glVertex3f(0, 0, 0)
    glVertex3f(0, -GRID_LENGTH, 0)

    glVertex3f(GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, 0, 0)
    glVertex3f(0, 0, 0)
    glVertex3f(0, GRID_LENGTH, 0)
    glEnd()


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
    draw_ground()

    # Draw world: sort by y (far to near) to mitigate no depth-test
    t = time.perf_counter()

    draw_bike()  # bike at fixed y; draw after ground

    # Collect and sort renders
    # Far (low y) first, near (high y) last
    for o in sorted(obstacles, key=lambda e: e['y']):
        draw_obstacle(o)
    for p in sorted(pickups, key=lambda e: e['y']):
        draw_pickup(p, t)

    # HUD
    draw_text(10, 770, f"Distance: {int(distance_travelled)}  High: {int(high_score)}")
    draw_text(10, 740, f"Lane: {player_lane+1}/3  Hops: {hop_charges}")
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
    draw_text(10, 710, " ".join(statuses) if statuses else "")

    glutSwapBuffers()


# ---------------- Main ----------------

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"CSE423 Endless Runner (OpenGL)")

    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)

    glutMainLoop()


if __name__ == "__main__":
    main()
