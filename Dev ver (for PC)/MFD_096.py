import pygame
import math
import sys
import time


# ---------------------------- GUI Configuration ----------------------------------------

# Display settings
WIDTH, HEIGHT = 80, 160
FPS = 15
PITCH_MOVE_SCALE = 1.5 # pixels moved per degree of pitch (horizontal line spacing)
ALT_MOVE_SCALE = 2 # pixels moved per altitude (vertical line spacing)
SPD_MOVE_SCALE = 2 # pixels moved per speed unit (vertical line spacing)


# ---------------------------- Base Configuration ----------------------------------------

# Set center point
CENTER_X, CENTER_Y = WIDTH / 2, HEIGHT / 2

# Set colors
GREEN = (0, 255, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE  = (40, 90, 160)
BROWN = (120, 70, 20)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# Set surface
background_surface = pygame.Surface((WIDTH, HEIGHT))
dynamic_surface    = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
fixed_surface      = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

background_surface.fill(BLACK)

# Create mask surface outside attitude indicator
mask_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
mask_surface.fill(BLACK)

# Load fonts
font = pygame.font.Font("C:/Users/dbstj/Desktop/Project/5. OpenCockpit/ViperDisplay-Bold.ttf", 8)
font_mid = pygame.font.Font("C:/Users/dbstj/Desktop/Project/5. OpenCockpit/ViperDisplay-Bold.ttf", 6)
font_small = pygame.font.Font("C:/Users/dbstj/Desktop/Project/5. OpenCockpit/ViperDisplay-Bold.ttf", 5)
font_tiny = pygame.font.Font("C:/Users/dbstj/Desktop/Project/5. OpenCockpit/ViperDisplay-Bold.ttf", 3)


# ---------------------------- FC data Variables (for testing) ----------------------------------------
pitch = 0.0             # deg
roll = 0.0              # deg
yaw = 0.0               # deg
v_speed = 21.0          # vertical speed
alt = 256               # altitude
speed_3d = 94           # 3d speed
sats = 1               # GPS satellites count
course = 125            # degree
vbat = 16.2             # voltage
current = 12.5          # ampere
home_dist = 512         # meter
home_dir = 30           # degree


# ---------------------------- GUI rotation functions ----------------------------------------

# Line rotation function - for horizon lines and gound polygon
def rotate_point(x, y, angle_deg):
    rad = math.radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    return (
        x * cos_a - y * sin_a,
        x * sin_a + y * cos_a
    )

# Draw rotated text on surface function - for pitch degree texts
def draw_text_rotated_on(surface, text, x, y, angle_deg, font=font):
    surf = font.render(text, True, WHITE)
    rotated_surf = pygame.transform.rotate(surf, angle_deg)
    rotated_rect = rotated_surf.get_rect(center=(int(x), int(y)))
    surface.blit(rotated_surf, rotated_rect)

# Draw text function
def draw_text(surface, text, x, y, align="left", font=font, color=WHITE):
    surf = font.render(text, True, color)
    rect = surf.get_rect()
    if align == "right":
        rect.topright = (x, y)
    elif align == "left":
        rect.topleft = (x, y)
    else:
        rect.center = (x, y)
    surface.blit(surf, rect)


# ---------------------------- Attitude indicator drawing function ----------------------------------------
def draw_attitude_circle(surface, pitch, roll):
    
    # Set circle parameters
    radius = 28
    ATT_Y = CENTER_Y - 45

    # Calculate center point
    x_center_circle, y_center_circle = CENTER_X, ATT_Y

    # Horizon offset
    horizon_y = y_center_circle - pitch * PITCH_MOVE_SCALE

    # Create temporary surface for Sky/Ground and lines (for mask outside circle)
    temp_surface = pygame.Surface((WIDTH, HEIGHT))

    # Fill entire surface as sky first
    temp_surface.fill(BLUE)

    # Set horizon line endpoints relative to center
    line_length = radius

    # Set endpoints before rotation (center-based)
    dxh1, dyh1 = -line_length, horizon_y - y_center_circle
    dxh2, dyh2 = line_length, horizon_y - y_center_circle

    # rotate using the same rotate_point used for horizon lines
    rdxh1, rdyh1 = rotate_point(dxh1, dyh1, -roll)
    rdxh2, rdyh2 = rotate_point(dxh2, dyh2, -roll)

    # Endpoints after rotation
    x1_h, y1_h = x_center_circle + rdxh1, y_center_circle + rdyh1
    x2_h, y2_h = x_center_circle + rdxh2, y_center_circle + rdyh2

    # Calculate perpendicular pointing downward after same roll rotation (For drawing ground polygon)
    perp_x, perp_y = rotate_point(0, 1, -roll)

    # Scale perpendicular to cover screen
    norm = math.hypot(perp_x, perp_y)
    
    if norm > 0:
        scale = (HEIGHT + 200) / norm
        perp_x_s, perp_y_s = perp_x * scale, perp_y * scale
    else:
        perp_x_s, perp_y_s = 0, HEIGHT + 200

    # Set ground polygon points
    p1_ext = (x1_h + perp_x_s, y1_h + perp_y_s)
    p2_ext = (x2_h + perp_x_s, y2_h + perp_y_s)
    ground_points = [(x1_h, y1_h), (x2_h, y2_h), p2_ext, p1_ext]

    # Draw ground polygon
    pygame.draw.polygon(temp_surface, BROWN, [(int(px), int(py)) for px, py in ground_points])

    # Draw horizon lines onto temp_surface so it will be masked
    for deg in range(-180, 180, 5):

        # vertical offset relative to attitude center (before rotation)
        offset_y = (deg - pitch) * PITCH_MOVE_SCALE
        y = y_center_circle + offset_y

        # Skip if far outside circle vertically to save work
        if abs(offset_y) > radius + 8:
            continue

        # Set line length
        if deg != 0 and deg % 10 == 0:
            half_len = 10
        elif deg == 0:
            half_len = 30
        else:
            half_len = 4

        # Draw Zero-degree line thicker
        line_width = 2 if deg == 0 else 1

        # Line endpoints in screen coords before rotation (center-based)
        x1, y1 = x_center_circle - half_len, y
        x2, y2 = x_center_circle + half_len, y

        # Translate to center and rotate around center by -roll
        dx1, dy1 = x1 - x_center_circle, y1 - y_center_circle
        dx2, dy2 = x2 - x_center_circle, y2 - y_center_circle

        # Rotate according to roll
        rdx1, rdy1 = rotate_point(dx1, dy1, -roll)
        rdx2, rdy2 = rotate_point(dx2, dy2, -roll)

        # Endpoints after rotation
        x1_after_rotate, y1_after_rotate = x_center_circle + rdx1, y_center_circle + rdy1
        x2_after_rotate, y2_after_rotate = x_center_circle + rdx2, y_center_circle + rdy2

        # Draw lines on temp surface
        pygame.draw.line(temp_surface, WHITE, (int(x1_after_rotate), int(y1_after_rotate)), (int(x2_after_rotate), int(y2_after_rotate)), line_width)

        # Calculate total line length after rotation
        dx = x2_after_rotate - x1_after_rotate
        dy = y2_after_rotate - y1_after_rotate
        L = math.hypot(dx, dy)
        
        if L == 0:
            continue

        # For multiples of 10, draw numeric texts at both ends, rotated with the line
        if deg > 0 and deg % 10 == 0:

            # Set text position offsets
            text_offset_x = 5
            text_offset_y = 0

            # Set deg value text positions
            text_x_left = x1_after_rotate - text_offset_x * (dx / L) - text_offset_y * (dy / L)
            text_y_left = y1_after_rotate - text_offset_x * (dy / L) + text_offset_y * (dx / L)
            text_x_right = x2_after_rotate + text_offset_x * (dx / L) - text_offset_y * (dy / L)
            text_y_right = y2_after_rotate + text_offset_x * (dy / L) + text_offset_y * (dx / L)
            text_angle = math.degrees(math.atan2(dy, dx))

            # Draw deg value text at both ends
            draw_text_rotated_on(temp_surface, f"{deg}", text_x_left, text_y_left, -text_angle, font=font_small)
            draw_text_rotated_on(temp_surface, f"{deg}", text_x_right, text_y_right, -text_angle, font=font_small)

        elif deg < 0 and deg % 10 == 0:
            # Set text position offsets
            text_offset_x = 5
            text_offset_y = 0

            # Set deg value text positions
            text_x_left = x1_after_rotate - text_offset_x * (dx / L) + text_offset_y * (dy / L)
            text_y_left = y1_after_rotate - text_offset_x * (dy / L) - text_offset_y * (dx / L)
            text_x_right = x2_after_rotate + text_offset_x * (dx / L) + text_offset_y * (dy / L)
            text_y_right = y2_after_rotate + text_offset_x * (dy / L) - text_offset_y * (dx / L)
            text_angle = math.degrees(math.atan2(dy, dx))

            # Draw deg value text at both ends
            draw_text_rotated_on(temp_surface, f"{-deg}", text_x_left, text_y_left, -text_angle, font=font_small)
            draw_text_rotated_on(temp_surface, f"{-deg}", text_x_right, text_y_right, -text_angle, font=font_small)

    # Blit attitude temp surface onto main screen
    surface.blit(temp_surface, (0, 0))

    # Apply circular mask: clear pixels outside the circle
    pygame.draw.circle(mask_surface, (0, 0, 0, 0), (CENTER_X, ATT_Y), radius)
    surface.blit(mask_surface, (0, 0))

    # Mask & border (draw over to produce clean rim)
    pygame.draw.circle(surface, BLACK, (int(x_center_circle), int(y_center_circle)), radius + 1, 1)
    pygame.draw.circle(surface, WHITE, (int(x_center_circle), int(y_center_circle)), radius, 1)

    # Draw aircraft symbol in the center of attitude circle
    pygame.draw.line(surface, BLACK, (int(x_center_circle - 9), int(y_center_circle)), (int(x_center_circle + 9), int(y_center_circle)), 4)
    pygame.draw.circle(surface, BLACK, (int(x_center_circle), int(y_center_circle)), 3)
    pygame.draw.line(surface, WHITE, (int(x_center_circle - 7), int(y_center_circle)), (int(x_center_circle + 7), int(y_center_circle)), 1)
    pygame.draw.circle(surface, WHITE, (int(x_center_circle), int(y_center_circle)), 1)


# ---------------------------- Draw Speed Gauge function ----------------------------------------

# Set circle parameters
cx_speed, cy_speed = 20, CENTER_Y
r_speed = 14

max_speed = 200  # maximum speed for full scale

# Set arc drawing parameters
start_angle_deg_speed = -40
end_angle_deg_speed = 220

# Draw arc (fixed components)
def draw_speed_gauge_fixed(surface, max_speed):

    # Set arc drawing parameters
    segments = 60  # number of line segments for smooth arc

    # Draw arc using line segments for smoother appearance
    for i in range(segments):

        # Determine arc color based on segment number
        if i < 15:
            color = WHITE
        elif i < 45:
            color = GREEN
        else:
            color = RED
        
        angle1_deg = start_angle_deg_speed + (end_angle_deg_speed - start_angle_deg_speed) * i / segments
        angle2_deg = start_angle_deg_speed + (end_angle_deg_speed - start_angle_deg_speed) * (i + 1) / segments
        
        rad1 = math.radians(angle1_deg)
        rad2 = math.radians(angle2_deg)
        
        x1 = cx_speed + math.cos(rad1) * r_speed
        y1 = cy_speed + math.sin(rad1) * r_speed
        x2 = cx_speed + math.cos(rad2) * r_speed
        y2 = cy_speed + math.sin(rad2) * r_speed
        
        # Use anti-aliased lines for smoother arc
        pygame.draw.aaline(surface, color, (int(x1), int(y1)), (int(x2), int(y2)))
        # fallback thinner line to ensure visibility
        pygame.draw.line(surface, color, (int(x1), int(y1)), (int(x2), int(y2)), 1)

    # text_scale: show only multiples of this value (e.g. 10, 20)
    text_scale = 40
    if max_speed <= 0:
        max_speed = 1

    # Draw numeric labels and small ticks along the arc
    for value in range(0, max_speed + 1, text_scale):
        t = value / max_speed
        angle_deg = start_angle_deg_speed + t * (end_angle_deg_speed - start_angle_deg_speed)
        rad = math.radians(angle_deg)

        # positions on arc
        arc_x = cx_speed + math.cos(rad) * r_speed
        arc_y = cy_speed + math.sin(rad) * r_speed

        # tick toward center
        tick_length = 2
        tick_in_x = cx_speed + math.cos(rad) * (r_speed - tick_length)
        tick_in_y = cy_speed + math.sin(rad) * (r_speed - tick_length)
        pygame.draw.line(surface, WHITE, (int(arc_x), int(arc_y)), (int(tick_in_x), int(tick_in_y)), 1)

        # label position slightly inside the tick
        label_r = r_speed - 6
        label_x = cx_speed + math.cos(rad) * label_r
        label_y = cy_speed + math.sin(rad) * label_r

        surf = font_tiny.render(f"{int(value)}", True, WHITE)
        rect = surf.get_rect(center=(int(label_x), int(label_y)))
        surface.blit(surf, rect)

# Draw needle and text (Dynamic components)
def draw_speed_gauge_dynamic(surface, speed):

    # Set speed needle value
    speed_needle = speed

    # Limit speed to max_speed
    if speed > max_speed:
        speed_needle = max_speed

    # Needle angle calculation
    angle = start_angle_deg_speed + (speed_needle / max_speed) * (end_angle_deg_speed - start_angle_deg_speed)
    rad = math.radians(angle)

    nx = cx_speed + math.cos(rad) * (r_speed - 2)
    ny = cy_speed + math.sin(rad) * (r_speed - 2)

    # Draw speed needle
    pygame.draw.line(surface, WHITE, (cx_speed, cy_speed), (nx, ny), 2)

    # Draw speed value text box
    box_points = [(cx_speed - 7, cy_speed - 16), (cx_speed + 7, cy_speed - 16), (cx_speed + 7, cy_speed - 9), (cx_speed - 7, cy_speed - 9)]
    pygame.draw.polygon(surface, BLACK, box_points)
    pygame.draw.polygon(surface, WHITE, box_points, 1)
    # Draw speed value text    
    draw_text(surface, f"{int(speed)}", cx_speed + 6, cy_speed - 14, font=font_small, align="right", color=WHITE)


# ---------------------------- Draw Altitude Gauge function ----------------------------------------

# Set circle parameters
cx_alt, cy_alt = WIDTH - 20, CENTER_Y
r_alt = 14

max_alt = 500  # maximum altitude for full scale

# Set arc drawing parameters
start_angle_deg_alt = -40
end_angle_deg_alt = 220

# Draw arc (fixed components)
def draw_alt_gauge_fixed(surface, max_alt):

    segments = 60  # number of line segments for smooth arc
    
    # Draw arc using line segments for smoother appearance
    for i in range(segments):        
        angle1_deg = start_angle_deg_alt + (end_angle_deg_alt - start_angle_deg_alt) * i / segments
        angle2_deg = start_angle_deg_alt + (end_angle_deg_alt - start_angle_deg_alt) * (i + 1) / segments
        
        rad1 = math.radians(angle1_deg)
        rad2 = math.radians(angle2_deg)
        
        x1 = cx_alt + math.cos(rad1) * r_alt
        y1 = cy_alt + math.sin(rad1) * r_alt
        x2 = cx_alt + math.cos(rad2) * r_alt
        y2 = cy_alt + math.sin(rad2) * r_alt
        
        # Use anti-aliased lines for smoother arc
        pygame.draw.aaline(surface, WHITE, (int(x1), int(y1)), (int(x2), int(y2)))
        # fallback thinner line to ensure visibility
        pygame.draw.line(surface, WHITE, (int(x1), int(y1)), (int(x2), int(y2)), 1)

    # text_scale: show only multiples of this value (e.g. 10, 20)
    text_scale = 100
    if max_alt <= 0:
        max_alt = 1

    # Draw numeric labels and small ticks along the arc
    for value in range(0, max_alt + 1, text_scale):
        t = value / max_alt
        angle_deg = start_angle_deg_alt + t * (end_angle_deg_alt - start_angle_deg_alt)
        rad = math.radians(angle_deg)

        # positions on arc
        arc_x = cx_alt + math.cos(rad) * r_alt
        arc_y = cy_alt + math.sin(rad) * r_alt

        # tick toward center
        tick_length = 2
        tick_in_x = cx_alt + math.cos(rad) * (r_alt - tick_length)
        tick_in_y = cy_alt + math.sin(rad) * (r_alt - tick_length)
        pygame.draw.line(surface, WHITE, (int(arc_x), int(arc_y)), (int(tick_in_x), int(tick_in_y)), 1)

        # label position slightly inside the tick
        label_r = r_alt - 6
        label_x = cx_alt + math.cos(rad) * label_r
        label_y = cy_alt + math.sin(rad) * label_r

        surf = font_tiny.render(f"{int(value)}", True, WHITE)
        rect = surf.get_rect(center=(int(label_x), int(label_y)))
        surface.blit(surf, rect)

# Draw needle and text (Dynamic components)
def draw_alt_gauge_dynamic(surface, alt):

    # Set altitude needle value
    alt_needle = alt

    # Limit altitude to max_alt
    if alt > max_alt:
        alt_needle = max_alt

    # Needle angle calculation
    angle = start_angle_deg_alt + (alt_needle / max_alt) * (end_angle_deg_alt - start_angle_deg_alt)
    rad = math.radians(angle)

    nx = cx_alt + math.cos(rad) * (r_alt - 2)
    ny = cy_alt + math.sin(rad) * (r_alt - 2)

    # Draw altitude needle
    pygame.draw.line(surface, WHITE, (cx_alt, cy_alt), (nx, ny), 2)

    # Draw altitude value text box
    box_points = [(cx_alt - 8, cy_alt - 16), (cx_alt + 7, cy_alt - 16), (cx_alt + 7, cy_alt - 9), (cx_alt - 8, cy_alt - 9)]
    pygame.draw.polygon(surface, BLACK, box_points)
    pygame.draw.polygon(surface, WHITE, box_points, 1)
    # Draw altitude value text
    draw_text(surface, f"{int(alt)}", cx_alt + 6, cy_alt - 14, font=font_small, align="right", color=WHITE)


# ---------------------------- Heading Indicator Drawing ----------------------------------------

# Set heading circle parameters
HDG_Y = CENTER_Y + 45
cx_heading, cy_heading = CENTER_X, HDG_Y
r_heading = 25

# Draw heading circle and plane symbol (fixed components)
def draw_heading_fixed(surface):

    # Draw heading circle
    pygame.draw.circle(surface, WHITE, (cx_heading, cy_heading), r_heading, 1)

    # Draw plane symbol
    pygame.draw.line(surface, YELLOW, (cx_heading - 3, cy_heading - 2), (cx_heading + 3, cy_heading - 2), 1)     # wing
    pygame.draw.line(surface, YELLOW, (cx_heading - 1, cy_heading + 2), (cx_heading + 1, cy_heading + 2), 1)     # tail
    pygame.draw.line(surface, YELLOW, (cx_heading, cy_heading - 4), (cx_heading, cy_heading + 2), 1)             # body

    # Draw heading pointer
    pygame.draw.polygon(surface, YELLOW, [(cx_heading, cy_heading - r_heading), (cx_heading - 1, cy_heading - r_heading - 2), (cx_heading + 1, cy_heading - r_heading - 2)])

    # Draw heading text box
    box_points = [(cx_heading - 6, cy_heading - r_heading - 10), (cx_heading + 6, cy_heading - r_heading - 10), (cx_heading + 6, cy_heading - r_heading - 3), (cx_heading - 6, cy_heading - r_heading - 3)]
    pygame.draw.polygon(surface, WHITE, box_points, 1)

# Draw heading (Dynamic components)
def draw_heading_dynamic(surface, yaw, sats, course, speed):

    # Set heading based on GPS if fixed, else use yaw
    if sats > 3 and speed > 1.5:
        heading = course      # gps based direction
    else:
        heading = yaw         # yaw based direction

    # Draw scale marks on heading circle
    for deg in range(0, 360, 30):
        rel = deg - heading
        rad = math.radians(rel - 90)

        x1 = cx_heading + math.cos(rad) * (r_heading - 2)
        y1 = cy_heading + math.sin(rad) * (r_heading - 2)
        x2 = cx_heading + math.cos(rad) * r_heading
        y2 = cy_heading + math.sin(rad) * r_heading

        pygame.draw.line(surface, WHITE, (x1, y1), (x2, y2), 1)

        # Draw numeric labels at every 90 degrees
        if deg % 90 == 0:
            label = {0:"N",90:"E",180:"S",270:"W"}[deg]
            tx = cx_heading + math.cos(rad) * (r_heading - 7)
            ty = cy_heading + math.sin(rad) * (r_heading - 7)
            draw_text(surface, label, int(tx-1), int(ty-2), font=font_small, align="left")

    # Draw heading value text
    draw_text(surface, f"{int(heading)}", cx_heading, cy_heading - r_heading - 6, font=font_small, align="center", color=WHITE)


# ---------------------------- MFD Render Function ----------------------------------------

# Draw fixed parts
def render_mfd_fixed():
    
    fixed_surface.fill((0,0,0,0))

    draw_speed_gauge_fixed(fixed_surface, max_speed)
    draw_alt_gauge_fixed(fixed_surface, max_alt)
    draw_heading_fixed(fixed_surface)

# Draw moving parts
def render_mfd(pitch, roll, yaw, v_speed, alt, speed_3d, sats, course, vbat, current, home_dist, home_dir):

    dynamic_surface.fill((0,0,0,0))

    draw_attitude_circle(dynamic_surface, pitch, roll)
    draw_speed_gauge_dynamic(dynamic_surface, speed_3d)
    draw_alt_gauge_dynamic(dynamic_surface, alt)
    draw_heading_dynamic(dynamic_surface, yaw, sats, course, speed_3d)

    # Info texts (top left side of MFD)
    draw_text(dynamic_surface, f"V", CENTER_X - 35, CENTER_Y - 73, font=font_tiny, align="left", color=WHITE)
    draw_text(dynamic_surface, f"{vbat:.2f}", CENTER_X - 32, CENTER_Y - 73, font=font_tiny, align="left", color=GREEN)

    # Info texts (bottom left side of MFD)
    draw_text(dynamic_surface, f"SAT {sats:.1f}", CENTER_X - 35, CENTER_Y + 70, font=font_tiny, align="left", color=GREEN)

    # Info texts (bottom right side of MFD)
    draw_text(dynamic_surface, f"H-dis", CENTER_X + 18, CENTER_Y + 67, font=font_tiny, align="left", color=WHITE)
    draw_text(dynamic_surface, f"H-dir", CENTER_X + 18, CENTER_Y + 70, font=font_tiny, align="left", color=WHITE)
    draw_text(dynamic_surface, f"{home_dist}", CENTER_X + 30, CENTER_Y + 67, font=font_tiny, align="left", color=GREEN)
    draw_text(dynamic_surface, f"{home_dir}", CENTER_X + 30, CENTER_Y + 70, font=font_tiny, align="left", color=GREEN)


#---------------------------- Main loop with MSP data ----------------------------------------

# Main loop with MSP data
def main(msp_data):

    # Render fixed parts of MFD
    render_mfd_fixed()

    while True:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # Get MSP data from MSP_Read module
        pitch = msp_data["pitch"] if msp_data["pitch"] is not None else 0.0
        roll = msp_data["roll"] if msp_data["roll"] is not None else 0.0
        yaw = msp_data["yaw"] if msp_data["yaw"] is not None else 0.0
        alt = msp_data["alt"] if msp_data["alt"] is not None else 0.0
        v_speed = msp_data["v_speed"] if msp_data["v_speed"] is not None else 0.0
        speed_3d = msp_data["speed_3d"] if msp_data["speed_3d"] is not None else 0.0
        sats = msp_data["sats"] if msp_data["sats"] is not None else 0
        course = msp_data["course"] if msp_data["course"] is not None else 0
        vbat = msp_data["vbat"] if msp_data["vbat"] is not None else 0.0
        current = msp_data["current"] if msp_data["current"] is not None else 0.0
        home_dist = msp_data["home_dist"] if msp_data["home_dist"] is not None else 0
        home_dir = msp_data["home_dir"] if msp_data["home_dir"] is not None else 0

        # Render dynamic parts of MFD
        render_mfd(pitch, roll, yaw, v_speed, alt, speed_3d, sats, course, vbat, current, home_dist, home_dir)

        # Set surface order
        screen.blit(background_surface, (0,0)) # bottom surface
        screen.blit(dynamic_surface, (0,0))
        screen.blit(fixed_surface, (0,0)) # top surface

        pygame.display.flip()

# Execute at develop environment
if __name__ == "__main__":

    t_init = time.time()

    # Generate virtual MSP data for testing
    def virtual_MSP_data():
        t = time.time()
        dt = t - t_init

        # Generate virtual MSP data values
        pitch = math.sin(dt * 1) * 10
        roll  = math.sin(dt * 1.5) * 10
        yaw = 45 + math.sin(dt * 0.2) * 180
        alt = 250 + math.sin(dt * 1 + 1) * 30
        speed_3d = 110 + math.sin(dt * 1 + 1) * -20
        sats = 10 + int((math.sin(dt * 0.2) + 1) * 5)
        course = 45 + (int(math.sin(dt * 0.2) * 180 % 360))
        vbat = 15.8 + (math.sin(dt * 1) * 1)
        current = 12.5 + math.sin(dt * 1) * -5
        home_dist = 512 + int(math.sin(dt * 1) * 5)
        home_dir = (int(dt * 10) % 360)

        return pitch, roll, yaw, v_speed, alt, speed_3d, sats, course, vbat, current, home_dist, home_dir
    
    # Render fixed parts of MFD
    render_mfd_fixed()

    # Main loop with virtual MSP data values
    while True:    
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # Get virtual MSP data values
        pitch, roll, yaw, v_speed, alt, speed_3d, sats, course, vbat, current, home_dist, home_dir = virtual_MSP_data()

        # Key controls for testing
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            pitch += 0.5
        if keys[pygame.K_s]:
            pitch -= 0.5
        if keys[pygame.K_a]:
            roll -= 1
        if keys[pygame.K_d]:
            roll += 1
        if keys[pygame.K_e]:
            yaw -= 1
        if keys[pygame.K_q]:
            yaw += 1
        if keys[pygame.K_t]:
            alt += 1
        if keys[pygame.K_g]:
            alt -= 1
        if keys[pygame.K_r]:
            speed_3d += 1
        if keys[pygame.K_f]:
            speed_3d -= 1

        # Render dynamic parts of MFD
        render_mfd(pitch, roll, yaw, v_speed, alt, speed_3d, sats, course, vbat, current, home_dist, home_dir)

        # Set surface order
        screen.blit(background_surface, (0,0))  # bottom surface
        screen.blit(dynamic_surface, (0,0))
        screen.blit(fixed_surface, (0,0))       # top surface

        pygame.display.flip()