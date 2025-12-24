import pygame
import math
import sys
import time

# ---------------------------- Base Configuration ----------------------------------------

# Display settings
WIDTH, HEIGHT = 80, 160
CENTER_X, CENTER_Y = WIDTH / 2, HEIGHT / 2

GREEN = (0, 255, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE  = (40, 90, 160)
BROWN = (120, 70, 20)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)

FPS = 30
PITCH_MOVE_SCALE = 1 # pixels moved per degree of pitch (horizontal line spacing)
ALT_MOVE_SCALE = 2 # pixels moved per altitude (vertical line spacing)
SPD_MOVE_SCALE = 2 # pixels moved per speed unit (vertical line spacing)

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

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
def draw_text(text, x, y, align="left", font=font, color=WHITE):
    surf = font.render(text, True, color)
    rect = surf.get_rect()
    if align == "right":
        rect.topright = (x, y)
    else:
        rect.topleft = (x, y)
    screen.blit(surf, rect)

# ---------------------------- Attitude indicator drawing function ----------------------------------------
def draw_attitude_circle(pitch, roll):
    
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

    # Blit masked attitude temp surface onto main screen
    screen.blit(temp_surface, (0, 0))

    # Apply circular mask: clear pixels outside the circle
    pygame.draw.circle(mask_surface, (0, 0, 0, 0), (CENTER_X, ATT_Y), radius)
    screen.blit(mask_surface, (0, 0))

    # Mask & border (draw over to produce clean rim)
    pygame.draw.circle(screen, BLACK, (int(x_center_circle), int(y_center_circle)), radius + 1, 1)
    pygame.draw.circle(screen, WHITE, (int(x_center_circle), int(y_center_circle)), radius, 1)

    # Draw aircraft symbol in the center of attitude circle
    pygame.draw.line(screen, BLACK, (int(x_center_circle - 9), int(y_center_circle)), (int(x_center_circle + 9), int(y_center_circle)), 4)
    pygame.draw.circle(screen, BLACK, (int(x_center_circle), int(y_center_circle)), 3)
    pygame.draw.line(screen, WHITE, (int(x_center_circle - 7), int(y_center_circle)), (int(x_center_circle + 7), int(y_center_circle)), 1)
    pygame.draw.circle(screen, WHITE, (int(x_center_circle), int(y_center_circle)), 1)


# ---------------------------- Draw Speed Gauge function ----------------------------------------
def draw_speed_gauge(speed):

    # Set circle parameters
    cx, cy = 20, CENTER_Y
    r = 14

    max_speed = 200  # maximum speed for full scale

    # Set arc drawing parameters
    start_angle_deg = -40
    end_angle_deg = 220
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
        
        angle1_deg = start_angle_deg + (end_angle_deg - start_angle_deg) * i / segments
        angle2_deg = start_angle_deg + (end_angle_deg - start_angle_deg) * (i + 1) / segments
        
        rad1 = math.radians(angle1_deg)
        rad2 = math.radians(angle2_deg)
        
        x1 = cx + math.cos(rad1) * r
        y1 = cy + math.sin(rad1) * r
        x2 = cx + math.cos(rad2) * r
        y2 = cy + math.sin(rad2) * r
        
        # Use anti-aliased lines for smoother arc
        pygame.draw.aaline(screen, color, (int(x1), int(y1)), (int(x2), int(y2)))
        # fallback thinner line to ensure visibility
        pygame.draw.line(screen, color, (int(x1), int(y1)), (int(x2), int(y2)), 1)

    # text_scale: show only multiples of this value (e.g. 10, 20)
    text_scale = 40
    if max_speed <= 0:
        max_speed = 1

    # Draw numeric labels and small ticks along the arc
    for value in range(0, max_speed + 1, text_scale):
        t = value / max_speed
        angle_deg = start_angle_deg + t * (end_angle_deg - start_angle_deg)
        rad = math.radians(angle_deg)

        # positions on arc
        arc_x = cx + math.cos(rad) * r
        arc_y = cy + math.sin(rad) * r

        # tick toward center
        tick_length = 2
        tick_in_x = cx + math.cos(rad) * (r - tick_length)
        tick_in_y = cy + math.sin(rad) * (r - tick_length)
        pygame.draw.line(screen, WHITE, (int(arc_x), int(arc_y)), (int(tick_in_x), int(tick_in_y)), 1)

        # label position slightly inside the tick
        label_r = r - 6
        label_x = cx + math.cos(rad) * label_r
        label_y = cy + math.sin(rad) * label_r

        surf = font_tiny.render(f"{int(value)}", True, WHITE)
        rect = surf.get_rect(center=(int(label_x), int(label_y)))
        screen.blit(surf, rect)

    # Set speed needle value
    speed_needle = speed

    # Limit speed to max_speed
    if speed > max_speed:
        speed_needle = max_speed

    # Needle angle calculation
    angle = start_angle_deg + (speed_needle / max_speed) * (end_angle_deg - start_angle_deg)
    rad = math.radians(angle)

    nx = cx + math.cos(rad) * (r - 2)
    ny = cy + math.sin(rad) * (r - 2)

    # Draw speed needle
    pygame.draw.line(screen, WHITE, (cx, cy), (nx, ny), 2)

    # Draw speed value text box
    box_points = [(cx-8, cy-13), (cx+8, cy-13), (cx+8, cy-4), (cx-8, cy-4)]
    pygame.draw.polygon(screen, BLACK, box_points)
    pygame.draw.polygon(screen, WHITE, box_points, 1)
    # Draw speed value text    
    draw_text(f"{int(speed)}", cx + 7, cy - 11, font=font_mid, align="right", color=WHITE)


# ---------------------------- Draw Altitude Gauge function ----------------------------------------
def draw_alt_gauge(alt):

    # Set circle parameters
    cx, cy = WIDTH - 20, CENTER_Y
    r = 14

    max_alt = 500  # maximum altitude for full scale

    # Set arc drawing parameters
    start_angle_deg = -40
    end_angle_deg = 220
    segments = 60  # number of line segments for smooth arc
    
    # Draw arc using line segments for smoother appearance
    for i in range(segments):        
        angle1_deg = start_angle_deg + (end_angle_deg - start_angle_deg) * i / segments
        angle2_deg = start_angle_deg + (end_angle_deg - start_angle_deg) * (i + 1) / segments
        
        rad1 = math.radians(angle1_deg)
        rad2 = math.radians(angle2_deg)
        
        x1 = cx + math.cos(rad1) * r
        y1 = cy + math.sin(rad1) * r
        x2 = cx + math.cos(rad2) * r
        y2 = cy + math.sin(rad2) * r
        
        # Use anti-aliased lines for smoother arc
        pygame.draw.aaline(screen, WHITE, (int(x1), int(y1)), (int(x2), int(y2)))
        # fallback thinner line to ensure visibility
        pygame.draw.line(screen, WHITE, (int(x1), int(y1)), (int(x2), int(y2)), 1)

    # text_scale: show only multiples of this value (e.g. 10, 20)
    text_scale = 100
    if max_alt <= 0:
        max_alt = 1

    # Draw numeric labels and small ticks along the arc
    for value in range(0, max_alt + 1, text_scale):
        t = value / max_alt
        angle_deg = start_angle_deg + t * (end_angle_deg - start_angle_deg)
        rad = math.radians(angle_deg)

        # positions on arc
        arc_x = cx + math.cos(rad) * r
        arc_y = cy + math.sin(rad) * r

        # tick toward center
        tick_length = 2
        tick_in_x = cx + math.cos(rad) * (r - tick_length)
        tick_in_y = cy + math.sin(rad) * (r - tick_length)
        pygame.draw.line(screen, WHITE, (int(arc_x), int(arc_y)), (int(tick_in_x), int(tick_in_y)), 1)

        # label position slightly inside the tick
        label_r = r - 6
        label_x = cx + math.cos(rad) * label_r
        label_y = cy + math.sin(rad) * label_r

        surf = font_tiny.render(f"{int(value)}", True, WHITE)
        rect = surf.get_rect(center=(int(label_x), int(label_y)))
        screen.blit(surf, rect)

    # Set altitude needle value
    alt_needle = alt

    # Limit altitude to max_alt
    if alt > max_alt:
        alt_needle = max_alt

    # Needle angle calculation
    angle = start_angle_deg + (alt_needle / max_alt) * (end_angle_deg - start_angle_deg)
    rad = math.radians(angle)

    nx = cx + math.cos(rad) * (r - 2)
    ny = cy + math.sin(rad) * (r - 2)

    # Draw altitude needle
    pygame.draw.line(screen, WHITE, (cx, cy), (nx, ny), 2)

    # Draw altitude value text box
    box_points = [(cx-9, cy-13), (cx+9, cy-13), (cx+9, cy-4), (cx-9, cy-4)]
    pygame.draw.polygon(screen, BLACK, box_points)
    pygame.draw.polygon(screen, WHITE, box_points, 1)
    # Draw altitude value text
    draw_text(f"{int(alt)}", cx + 8, cy - 11, font=font_mid, align="right", color=WHITE)


# ---------------------------- Heading Indicator Drawing ----------------------------------------

def draw_heading(yaw, sats, course, speed):

    # Set heading circle parameters
    HDG_Y = CENTER_Y + 45
    cx, cy = CENTER_X, HDG_Y
    r = 25

    # Draw heading circle
    pygame.draw.circle(screen, WHITE, (cx, cy), r, 1)

    # Set heading based on GPS if fixed, else use yaw
    if sats > 3 and speed > 1.5:
        heading = course      # gps based direction
    else:
        heading = yaw         # yaw based direction

    # Draw scale marks on heading circle
    for deg in range(0, 360, 30):
        rel = deg - heading
        rad = math.radians(rel - 90)

        x1 = cx + math.cos(rad) * (r - 2)
        y1 = cy + math.sin(rad) * (r - 2)
        x2 = cx + math.cos(rad) * r
        y2 = cy + math.sin(rad) * r

        pygame.draw.line(screen, WHITE, (x1, y1), (x2, y2), 1)

        # Draw numeric labels at every 90 degrees
        if deg % 90 == 0:
            label = {0:"N",90:"E",180:"S",270:"W"}[deg]
            tx = cx + math.cos(rad) * (r - 7)
            ty = cy + math.sin(rad) * (r - 7)
            draw_text(label, int(tx-1), int(ty-2), font=font_small, align="left")

    # Draw heading pointer
    pygame.draw.polygon(screen, YELLOW, [(cx, cy - r), (cx - 1, cy - r - 2), (cx + 1, cy - r - 2)])

    # Draw heading text box
    box_points = [(cx - 7, cy - r - 10), (cx + 7, cy - r - 10), (cx + 7, cy - r - 3), (cx - 7, cy - r - 3)]
    pygame.draw.polygon(screen, BLACK, box_points)
    pygame.draw.polygon(screen, WHITE, box_points, 1)

    # Draw heading value text
    draw_text(f"{int(heading)}", cx + 7, cy - r - 8, font=font_small, align="right", color=WHITE)

    # Draw plane symbol in the center of heading circle
    pygame.draw.line(screen, YELLOW, (cx - 3, cy - 2), (cx + 3, cy - 2), 1)     # wing
    pygame.draw.line(screen, YELLOW, (cx - 1, cy + 2), (cx + 1, cy + 2), 1)     # tail
    pygame.draw.line(screen, YELLOW, (cx, cy - 4), (cx, cy + 2), 1)             # body


# ---------------------------- MFD Render Function ----------------------------------------
def render_mfd(pitch, roll, yaw, v_speed, alt, speed_3d, sats, course, vbat, current, home_dist, home_dir):
    screen.fill(BLACK)

    draw_attitude_circle(pitch, roll)
    draw_speed_gauge(speed_3d)
    draw_alt_gauge(alt)
    draw_heading(yaw, sats, course, speed_3d)

    # Info texts (top left side of MFD)
    draw_text(f"V", CENTER_X - 35, CENTER_Y - 73, font=font_tiny, align="left", color=WHITE)
    draw_text(f"{vbat:.2f}", CENTER_X - 32, CENTER_Y - 73, font=font_tiny, align="left", color=GREEN)

    # Info texts (bottom left side of MFD)
    draw_text(f"SAT {sats:.1f}", CENTER_X - 35, CENTER_Y + 70, font=font_tiny, align="left", color=GREEN)

    # Info texts (bottom right side of MFD)
    draw_text(f"H-dis", CENTER_X + 18, CENTER_Y + 67, font=font_tiny, align="left", color=WHITE)
    draw_text(f"H-dir", CENTER_X + 18, CENTER_Y + 70, font=font_tiny, align="left", color=WHITE)
    draw_text(f"{home_dist}", CENTER_X + 30, CENTER_Y + 67, font=font_tiny, align="left", color=GREEN)
    draw_text(f"{home_dir}", CENTER_X + 30, CENTER_Y + 70, font=font_tiny, align="left", color=GREEN)

#---------------------------- Main loop with MSP data ----------------------------------------

# Main loop with MSP data
def main(msp_data):
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

        # Render MFD
        render_mfd(pitch, roll, yaw, v_speed, alt, speed_3d, sats, course, vbat, current, home_dist, home_dir)

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

        # Render MFD
        render_mfd(pitch, roll, yaw, v_speed, alt, speed_3d, sats, course, vbat, current, home_dist, home_dir)

        pygame.display.flip()