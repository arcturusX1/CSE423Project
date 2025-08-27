from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

fovY = 120  # Field of view

# Camera-related variables
import math
camera_azimuth = 45.0  # horizontal angle (degrees)
camera_elevation = 30.0  # vertical angle (degrees)
camera_distance = 500.0

fovY = 120  # Field of view
GRID_LENGTH = 600  # Length of grid lines
rand_var = 423


def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1,1,1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    
    # Set up an orthographic projection that matches window coordinates
    gluOrtho2D(0, 1000, 0, 800)  # left, right, bottom, top

    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    # Draw text at (x, y) in screen coordinates
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    
    # Restore original projection and modelview matrices
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


# ---------------------------
# Vehicle model (civilian car)
# ---------------------------

def draw_wheel(radius=22, thickness=45):
    """Draw a disk-like wheel (cylinder) with given radius and thickness."""
    glPushMatrix()
    glColor3f(0.1, 0.1, 0.1)
    quad = gluNewQuadric()
    # Draw cylinder (disk)
    gluCylinder(quad, radius, radius, thickness, 32, 1)
    # Draw front face
    glColor3f(0.2, 0.2, 0.2)
    gluDisk(quad, 0.0, radius, 32, 1)
    # Draw back face
    glPushMatrix()
    glTranslatef(0, 0, thickness)
    gluDisk(quad, 0.0, radius, 32, 1)
    glPopMatrix()
    glPopMatrix()


def draw_vehicle():
    """
    Clean 3D car model: body, roof, windshield, headlights, taillights, wheels facing +x.
    """
    # Car dimensions
    L, W, H = 220.0, 120.0, 50.0   # body length/width/height
    roofL, roofW, roofH = 120.0, 70.0, 32.0  # roof length/width/height
    wheel_radius = 22.0
    wheel_thickness = 8.0

    # --- Body (rectangular box) ---
    glPushMatrix()
    glColor3f(0.12, 0.35, 0.85)
    glTranslatef(0.0, 0.0, H/2)
    glScalef(L/100.0, W/100.0, H/100.0)
    glutSolidCube(100.0)
    glPopMatrix()

    # --- Roof (rectangular box, sits on top, shorter and narrower) ---
    glPushMatrix()
    glColor3f(0.10, 0.25, 0.65)
    glTranslatef(10.0, 0.0, H + roofH/2)  # slightly forward
    glScalef(roofL/100.0, roofW/100.0, roofH/100.0)
    glutSolidCube(100.0)
    glPopMatrix()

    # --- Windshield (slanted quad, top edge flush with roof front) ---
    glPushMatrix()
    glColor3f(0.6, 0.85, 0.95)
    glBegin(GL_QUADS)
    # Bottom edge (on body roof, just in front of roof)
    ws_x = 10.0 + roofL/2 + 2.0
    glVertex3f(ws_x, -roofW/2, H)
    glVertex3f(ws_x,  roofW/2, H)
    # Top edge (at roof front top, flush with roof)
    roof_front_x = 10.0 + roofL/2
    glVertex3f(roof_front_x,  roofW/2, H + roofH)
    glVertex3f(roof_front_x, -roofW/2, H + roofH)
    glEnd()
    glPopMatrix()

    # --- Headlights (two spheres at front corners) ---
    headlight_z = 18.0
    headlight_y = W/2 - 18.0
    headlight_x = L/2 + 6.0
    for sgn in (-1, 1):
        glPushMatrix()
        glTranslatef(headlight_x, sgn*headlight_y, headlight_z)
        glColor3f(1.0, 0.95, 0.5)
        gluSphere(gluNewQuadric(), 7.0, 16, 12)
        glPopMatrix()

    # --- Taillights (two red cubes at rear corners) ---
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



    wx = L/2 - 32.0
    wheel_thickness = 28
    wz_pos = W/2 + wheel_thickness/2  # position wheels outside the body laterally
    wz = wheel_radius - 6.0  # lower so wheels are below body

    for sx in (-1, 1):  # front and rear wheels
        for sy in (-1, 1):  # left and right wheels
            glPushMatrix()
            # Position wheel outside the body laterally (along Y-axis, which is the car's width)
            y_offset = sy * wz_pos
            glTranslatef(sx*wx, y_offset, wz)
            # Orient disk: flat face always faces outward, matching previous cone logic
            if sy > 0:
                glRotatef(90, 1, 0, 0)  # right side: flat face faces +Y
            else:
                glRotatef(-90, 1, 0, 0)   # left side: flat face faces -Y
            draw_wheel(radius=wheel_radius, thickness=wheel_thickness)
            glPopMatrix()

# (kept for reference, not used any more)
# def draw_shapes():
#     glPushMatrix()
#     glColor3f(1, 0, 0)
#     glTranslatef(0, 0, 0)
#     glutSolidCube(60)
#     glTranslatef(0, 0, 100)
#     glColor3f(0, 1, 0)
#     glutSolidCube(60)
#     glColor3f(1, 1, 0)
#     gluCylinder(gluNewQuadric(), 40, 5, 150, 10, 10)
#     glTranslatef(100, 0, 100)
#     glRotatef(90, 0, 1, 0)
#     gluCylinder(gluNewQuadric(), 40, 5, 150, 10, 10)
#     glColor3f(0, 1, 1)
#     glTranslatef(300, 0, 100)
#     gluSphere(gluNewQuadric(), 80, 10, 10)
#     glPopMatrix()


def keyboardListener(key, x, y):
    """
    Handles keyboard inputs for player movement, gun rotation, camera updates, and cheat mode toggles.
    Also handles zoom in/out with + and - keys.
    """
    global camera_distance
    # Convert key to string if needed (Python3)
    if isinstance(key, bytes):
        key = key.decode('utf-8')
    if key == '+' or key == '=':
        camera_distance = max(50, camera_distance - 20)  # Zoom in
        glutPostRedisplay()
    elif key == '-' or key == '_':
        camera_distance = min(2000, camera_distance + 20)  # Zoom out
        glutPostRedisplay()


def specialKeyListener(key, x, y):
    """
    Handles special key inputs (arrow keys) for adjusting the camera azimuth and elevation.
    LEFT/RIGHT: rotate around car (azimuth)
    UP/DOWN: change elevation
    """
    global camera_azimuth, camera_elevation
    if key == GLUT_KEY_LEFT:
        camera_azimuth -= 5.0
    elif key == GLUT_KEY_RIGHT:
        camera_azimuth += 5.0
    elif key == GLUT_KEY_UP:
        camera_elevation += 5.0
        if camera_elevation > 89.0:
            camera_elevation = 89.0
    elif key == GLUT_KEY_DOWN:
        camera_elevation -= 5.0
        if camera_elevation < -10.0:
            camera_elevation = -10.0
    glutPostRedisplay()


def mouseListener(button, state, x, y):
    """
    Handles mouse inputs for firing bullets (left click) and toggling camera mode (right click).
    """
    pass


def setupCamera():
    """
    Configures the camera's projection and view settings.
    Uses a perspective projection and positions the camera to look at the target.
    Camera orbits around the car using azimuth and elevation angles.
    """
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, 1.25, 0.1, 1500)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    # Calculate camera position from spherical coordinates
    az = math.radians(camera_azimuth)
    el = math.radians(camera_elevation)
    x = camera_distance * math.cos(el) * math.cos(az)
    y = camera_distance * math.cos(el) * math.sin(az)
    z = camera_distance * math.sin(el)
    gluLookAt(x, y, z, 0, 0, 0, 0, 0, 1)


def idle():
    glutPostRedisplay()


def showScreen():
    """
    Display function to render the scene.
    """
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glEnable(GL_DEPTH_TEST)
    glLoadIdentity()
    glViewport(0, 0, 1000, 800)

    setupCamera()

    # Floor quads
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

    # UI text
    draw_text(10, 770, f"A Random Fixed Position Text")
    draw_text(10, 740, f"See how the position and variable change?: {rand_var}")


    # --- Axes (OpenGL convention: X=right, Y=up, Z=out of screen) ---
    glPushMatrix()
    glTranslatef(-140, -100, 0)  # Move axes next to car (adjust as needed)
    glLineWidth(3)
    glBegin(GL_LINES)
    # X axis (red, right)
    glColor3f(1,0,0)
    glVertex3f(0,0,0)
    glVertex3f(60,0,0)
    # Y axis (green, up)
    glColor3f(0,1,0)
    glVertex3f(0,0,0)
    glVertex3f(0,0,60)
    # Z axis (blue, out of screen)
    glColor3f(0,0,1)
    glVertex3f(0,0,0)
    glVertex3f(0,60,0)
    glEnd()
    # Draw axis labels (in 3D)
    glColor3f(1,0,0)
    glRasterPos3f(65, 0, 0)
    for ch in "X":
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    glColor3f(0,1,0)
    glRasterPos3f(0, 0, 65)
    for ch in "Y":
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    glColor3f(0,0,1)
    glRasterPos3f(0, 65, 0)
    for ch in "Z":
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    glPopMatrix()

    # --- Vehicle ---
    glPushMatrix()
    # Position the car near origin; tweak if you want it elsewhere
    glTranslatef(0.0, 0.0, 0.0)
    draw_vehicle()
    glPopMatrix()

    glutSwapBuffers()


# Main function to set up OpenGL window and loop

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Ass")

    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)

    glutMainLoop()

if __name__ == "__main__":
    main()
