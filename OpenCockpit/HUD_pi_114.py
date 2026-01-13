import MSP_Read_pi

import board
import digitalio
import busio
import math
import pygame
import time
import numpy as np

import adafruit_rgb_display.st7789 as ST7789


# Display hardware configuration (used by main.py to initialize)
DISPLAY_CONFIG = {
    "driver": "ST7789",
    "width": 135,
    "height": 240,
    "rotation": 0,
    "x_offset": 53,
    "y_offset": 40
}


# ---------------------------- GUI Configuration ----------------------------------------

# Display settings
WIDTH, HEIGHT = 135, 240
FPS = 30
PITCH_MOVE_SCALE = 10 # pixels moved per degree of pitch (horizontal line spacing)
ALT_MOVE_SCALE = 2 # pixels moved per altitude (vertical line spacing)
SPD_MOVE_SCALE = 2 # pixels moved per speed unit (vertical line spacing)


# ---------------------------- Base Configuration ----------------------------------------

# Set center point
CENTER_X, CENTER_Y = WIDTH / 2, HEIGHT / 2

# Set colors
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# Load fonts
font = pygame.font.Font("/boot/firmware/OpenCockpit/ViperDisplay-Bold.ttf",8)
font_mid = pygame.font.Font("/boot/firmware/OpenCockpit/ViperDisplay-Bold.ttf",6)
font_small = pygame.font.Font("/boot/firmware/OpenCockpit/ViperDisplay-Bold.ttf",5)


# ---------------------------- FC data Variables (for testing) ----------------------------------------
pitch = 0.0             # deg
roll = 0.0              # deg
yaw = 0.0               # deg
v_speed = 21.0          # vertical speed
alt = 256               # altitude
speed_3d = 94           # 3d speed
sats = 10               # GPS satellites count
course = 123            # GPS course
vbat = 16.2             # voltage
current = 12.5          # ampere
home_dist = 512         # meter
home_dir = 30           # degree

# ---------------------------- GUI rotation functions ----------------------------------------

# Line rotation function - for horizon lines
def rotate_point(x, y, angle_deg):
    rad = math.radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    return (
        x * cos_a - y * sin_a,
        x * sin_a + y * cos_a
    )

# Text rotation function - for pitch degree texts
def draw_text_rotated(text, x, y, angle_deg, align="left", font=font_mid):
    surf = font.render(text, True, GREEN)
    rotated_surf = pygame.transform.rotate(surf, angle_deg)
    rotated_rect = rotated_surf.get_rect()
    if align == "right":
        rotated_rect.topright = (x, y)
    else:
        rotated_rect.topleft = (x, y)
    screen.blit(rotated_surf, rotated_rect)

# Draw text function
def draw_text(text, x, y, align="left", font=font):
    surf = font.render(text, True, GREEN)
    rect = surf.get_rect()
    if align == "right":
        rect.topright = (x, y)
    else:
        rect.topleft = (x, y)
    screen.blit(surf, rect)


# ---------------------------- Draw horizon lines & pitch degree texts functions ----------------------------------------
def draw_horizon_lines(pitch, roll, yaw):
    for deg in range(-180, 180, 5):
        offset_y = (deg - pitch) * PITCH_MOVE_SCALE

        if abs(offset_y) > HEIGHT:
            continue

        # Set half line length based on degree
        if deg == 0:
            length_half = 140
        else:
            length_half = 24

        # Calculate Y position before rotation with pitch offset
        y = CENTER_Y + offset_y

        # Line endpoints before rotation
        x1, y1 = -length_half, 0
        x2, y2 = length_half, 0

        # Define endpoints before rotation in screen coordinates
        ux1, uy1 = CENTER_X + x1 + yaw, y + y1
        ux2, uy2 = CENTER_X + x2 + yaw, y + y2

        # Translate points to origin for rotation
        dx1, dy1 = ux1 - CENTER_X, uy1 - CENTER_Y
        dx2, dy2 = ux2 - CENTER_X, uy2 - CENTER_Y

        # Rotate according to roll
        rdx1, rdy1 = rotate_point(dx1, dy1, -roll)
        rdx2, rdy2 = rotate_point(dx2, dy2, -roll)

        # Endpoints after rotation
        x1_after_rotate, y1_after_rotate = CENTER_X + rdx1, CENTER_Y + rdy1
        x2_after_rotate, y2_after_rotate = CENTER_X + rdx2, CENTER_Y + rdy2

        # Calculate total line length after rotation
        dx = x2_after_rotate - x1_after_rotate
        dy = y2_after_rotate - y1_after_rotate
        L = math.hypot(dx, dy)

        if L == 0:
            continue

        # Calculate center point after rotation
        x_center_after_rotate = x1_after_rotate + dx / 2
        y_center_after_rotate = y1_after_rotate + dy / 2

        # Set middle gaps size at center of lines
        mid_gap = 8
        ox = dx * mid_gap / L
        oy = dy * mid_gap / L

        # Draw lines and markers - below horizon
        if deg > 0:

            # Set small gap(gap in line) size
            small_gap = 1.6
            ox_small = dx * small_gap / L
            oy_small = dy * small_gap / L

            # Set small gap(gap in line) positions
            small_gap1_position = (1 / 9)
            small_gap2_position = (1 / 4)
            small_gap3_position = 1 - small_gap2_position
            small_gap4_position = 1 - small_gap1_position

            p1x = x1_after_rotate + dx * small_gap1_position # left small gap 1 center position
            p1y = y1_after_rotate + dy * small_gap1_position # left small gap 1 center position
            p2x = x1_after_rotate + dx * small_gap2_position # left small gap 2 center position
            p2y = y1_after_rotate + dy * small_gap2_position # left small gap 2 center position
            p3x = x1_after_rotate + dx * small_gap3_position # right small gap 1 center position
            p3y = y1_after_rotate + dy * small_gap3_position # right small gap 1 center position
            p4x = x1_after_rotate + dx * small_gap4_position # right small gap 2 center position
            p4y = y1_after_rotate + dy * small_gap4_position # right small gap 2 center position

            # Draw first line (between left end and left small gap 1)
            pygame.draw.line(screen, GREEN, (x1_after_rotate, y1_after_rotate), (p1x - ox_small, p1y - oy_small), 1)
            # Draw second line (between left small gap 1 and left small gap 2)
            pygame.draw.line(screen, GREEN, (p1x + ox_small, p1y + oy_small), (p2x - ox_small, p2y - oy_small), 1)
            # Draw second line (between left small gap 2 and middle gap)
            pygame.draw.line(screen, GREEN, (p2x + ox_small, p2y + oy_small), (x_center_after_rotate - ox, y_center_after_rotate - oy), 1)
            # Draw third line (between middle gap and right small gap 1)
            pygame.draw.line(screen, GREEN, (x_center_after_rotate + ox, y_center_after_rotate + oy), (p3x - ox_small, p3y - oy_small), 1)
            # Draw third line (between right small gap 1 and right small gap 2)
            pygame.draw.line(screen, GREEN, (p3x + ox_small, p3y + oy_small), (p4x - ox_small, p4y - oy_small), 1)
            # Draw fourth line (between right small gap 2 and right end)
            pygame.draw.line(screen, GREEN, (p4x + ox_small, p4y + oy_small), (x2_after_rotate, y2_after_rotate), 1)
            
            # Set marker length and direction (perpendicular to horizon line)
            marker_length = 2.4
            perp_x = -dy / L
            perp_y = dx / L
            marker_line_width = 1
            
            # Draw markers at left side of middle gap
            marker_left_x = x_center_after_rotate - ox # left side of middle gap
            marker_left_y = y_center_after_rotate - oy # left side of middle gap
            marker_left_end_x = marker_left_x - marker_length * perp_x # End point of left marker
            marker_left_end_y = marker_left_y - marker_length * perp_y # End point of left marker
            pygame.draw.line(screen, GREEN, (marker_left_x, marker_left_y), (marker_left_end_x, marker_left_end_y), marker_line_width)
            
            # Draw markers at right side of middle gap
            marker_right_x = x_center_after_rotate + ox # right side of middle gap
            marker_right_y = y_center_after_rotate + oy # right side of middle gap
            marker_right_end_x = marker_right_x - marker_length * perp_x # End point of right marker
            marker_right_end_y = marker_right_y - marker_length * perp_y # End point of right marker
            pygame.draw.line(screen, GREEN, (marker_right_x, marker_right_y), (marker_right_end_x, marker_right_end_y), marker_line_width)
            
        # Draw lines and markers - above horizon
        elif deg < 0:
            
            # Draw first line (left side of middle gap)
            pygame.draw.line(screen, GREEN, (x1_after_rotate, y1_after_rotate), (x_center_after_rotate - ox, y_center_after_rotate - oy), 1)
            # Draw second line (right side of middle gap)
            pygame.draw.line(screen, GREEN, (x_center_after_rotate + ox, y_center_after_rotate + oy), (x2_after_rotate, y2_after_rotate), 1)
            
            # Set marker length and direction (perpendicular to horizon line)
            marker_length = 3
            perp_x = -dy / L
            perp_y = dx / L
            marker_line_width = 1
            
            # Draw markers at left side of middle gap
            marker_left_x = x_center_after_rotate - ox # left side of middle gap
            marker_left_y = y_center_after_rotate - oy # left side of middle gap
            marker_left_end_x = marker_left_x + marker_length * perp_x # End point of left marker
            marker_left_end_y = marker_left_y + marker_length * perp_y # End point of left marker
            pygame.draw.line(screen, GREEN, (marker_left_x, marker_left_y), (marker_left_end_x, marker_left_end_y), marker_line_width)
            
            # Draw markers at right side of middle gap
            marker_right_x = x_center_after_rotate + ox # right side of middle gap
            marker_right_y = y_center_after_rotate + oy # right side of middle gap
            marker_right_end_x = marker_right_x + marker_length * perp_x # End point of right marker
            marker_right_end_y = marker_right_y + marker_length * perp_y # End point of right marker
            pygame.draw.line(screen, GREEN, (marker_right_x, marker_right_y), (marker_right_end_x, marker_right_end_y), marker_line_width)
        else:
            # deg == 0
            # Draw line (left side of middle gap)
            pygame.draw.line(screen, GREEN, (x1_after_rotate, y1_after_rotate), (x_center_after_rotate - ox, y_center_after_rotate - oy), 2)
            # Draw line (right side of middle gap)
            pygame.draw.line(screen, GREEN, (x_center_after_rotate + ox, y_center_after_rotate + oy), (x2_after_rotate, y2_after_rotate), 2)


        # Draw pitch degree texts (except 0 degree) - below horizon
        if deg > 0:

            # Set text position offsets
            text_offset_x = 1
            text_offset_y = -8

            # Draw left end deg value text
            text_x_left = x1_after_rotate - text_offset_x * (dx / L) - text_offset_y * (dy / L)
            text_y_left = y1_after_rotate - text_offset_x * (dy / L) + text_offset_y * (dx / L)
            text_angle = math.degrees(math.atan2(dy, dx))
            draw_text_rotated(f"{deg}", int(text_x_left), int(text_y_left), -text_angle, align="left")
            
            # Draw right end deg value text
            text_x_right = x2_after_rotate + text_offset_x * (dx / L) - text_offset_y * (dy / L)
            text_y_right = y2_after_rotate + text_offset_x * (dy / L) + text_offset_y * (dx / L)
            draw_text_rotated(f"{deg}", int(text_x_right), int(text_y_right), -text_angle, align="right")
        
        # Draw pitch degree texts (except 0 degree) - above horizon
        if deg < 0:
            # Set text position offsets
            text_offset_x = 1
            text_offset_y = -2

            # Draw left end deg value text
            text_x_left = x1_after_rotate - text_offset_x * (dx / L) + text_offset_y * (dy / L)
            text_y_left = y1_after_rotate - text_offset_x * (dy / L) - text_offset_y * (dx / L)
            text_angle = math.degrees(math.atan2(dy, dx))
            draw_text_rotated(f"{-deg}", int(text_x_left), int(text_y_left), -text_angle, align="left")
            
            # Draw right end deg value text
            text_x_right = x2_after_rotate + text_offset_x * (dx / L) + text_offset_y * (dy / L)
            text_y_right = y2_after_rotate + text_offset_x * (dy / L) - text_offset_y * (dx / L)
            draw_text_rotated(f"{-deg}", int(text_x_right), int(text_y_right), -text_angle, align="right")


# ---------------------------- Draw altitude & 3d speed lines and texts functions ----------------------------------------

# Draw altitude line function
def draw_altmeter(alt):
    alt_center_x = CENTER_X + 36
    alt_center_y = CENTER_Y
    altmeter_display_range = 20

    # Draw center line
    pygame.draw.line(screen, GREEN, (alt_center_x - 5, alt_center_y), (alt_center_x - 2, alt_center_y), 1)

    # Set small scale for altitude ticks
    alt_scale = 2

    # Draw altitude ticks (small ticks)
    for alt_tick in range(int(alt) - 60, int(alt) + 61, alt_scale):
        if alt_tick % 10 == 0:
            continue  # Scale of 10 will be drawn later
            
        # Calculate alt_tick position (centered around current alt)
        offset = (alt - alt_tick) * ALT_MOVE_SCALE
        
        # Set screen Y position
        tick_y = alt_center_y + offset
        
        # Check range
        if abs(offset) > altmeter_display_range:
            continue

        # Draw small ticks
        pygame.draw.line(screen, GREEN, (alt_center_x + 3, tick_y), (alt_center_x, tick_y), 1)
    
    # Draw altitude ticks (10s ticks with text)
    start_alt = (int(alt) // 10) * 10 - 60
    for alt_tick in range(start_alt, int(alt) + 70, 10):
        # Calculate alt_tick position (centered around current alt)
        offset = (alt - alt_tick) * ALT_MOVE_SCALE
        
        # Set screen Y position
        tick_y = alt_center_y + offset

        # Check range
        if abs(offset) > altmeter_display_range:
            continue

        # Draw 10s ticks with longer line
        pygame.draw.line(screen, GREEN, (alt_center_x + 7, tick_y), (alt_center_x, tick_y), 1)
        
        # Draw altitude value text (skip center value to avoid overlapping with altitude number)
        if not (tick_y < alt_center_y + 10 and tick_y > alt_center_y - 3):
            draw_text(f"{alt_tick}", alt_center_x + 9, int(tick_y - 2), align="left", font=font_small)

# Draw 3d speed line function
def draw_speedmeter(speed_3d):
    speed_center_x = CENTER_X - 36
    speed_center_y = CENTER_Y
    speed_display_range = 20

    # Draw center line
    pygame.draw.line(screen, GREEN, (speed_center_x + 2, speed_center_y), (speed_center_x + 5, speed_center_y), 1)

    # Set small scale for speed ticks
    speed_scale = 2

    # Draw speed ticks (small ticks)
    for speed_tick in range(int(speed_3d) - 60, int(speed_3d) + 61, speed_scale):
        if speed_tick % 10 == 0:
            continue  # Scale of 10 will be drawn later
            
        # Calculate speed_tick position (centered around current speed)
        offset = (speed_3d - speed_tick) * SPD_MOVE_SCALE
        
        # Set screen Y position
        tick_y = speed_center_y + offset
        
        # Check range
        if abs(offset) > speed_display_range:
            continue

        # Draw small ticks
        pygame.draw.line(screen, GREEN, (speed_center_x - 3, tick_y), (speed_center_x, tick_y), 1)
    
    # Draw speed ticks (10s ticks with text)
    start_speed = (int(speed_3d) // 10) * 10 - 60
    for speed_tick in range(start_speed, int(speed_3d) + 70, 10):
        # Calculate speed_tick position (centered around current speed)
        offset = (speed_3d - speed_tick) * ALT_MOVE_SCALE
        
        # Set screen Y position
        tick_y = speed_center_y + offset

        # Check range
        if abs(offset) > speed_display_range:
            continue

        # Draw 10s ticks with longer line
        pygame.draw.line(screen, GREEN, (speed_center_x - 7, tick_y), (speed_center_x, tick_y), 1)
        
        # Draw speed value text (skip center value to avoid overlapping with speed number)
        if not (tick_y < speed_center_y + 10 and tick_y > speed_center_y - 3):
            draw_text(f"{speed_tick}", speed_center_x - 9, int(tick_y - 2), align="right", font=font_small)


# ---------------------------- Draw Crosshiar function ----------------------------------------

# Draw center crosshair function
def draw_center_crosshair():
    crosshair_size = 3
    crosshair_mid_gap = 1.6
    crosshair_line_width = 1
    pygame.draw.line(screen, GREEN, (CENTER_X - crosshair_size, CENTER_Y), (CENTER_X - crosshair_mid_gap, CENTER_Y), crosshair_line_width)
    pygame.draw.line(screen, GREEN, (CENTER_X + crosshair_mid_gap, CENTER_Y), (CENTER_X + crosshair_size, CENTER_Y), crosshair_line_width)
    pygame.draw.line(screen, GREEN, (CENTER_X, CENTER_Y - crosshair_size), (CENTER_X, CENTER_Y - crosshair_mid_gap), crosshair_line_width)
    pygame.draw.line(screen, GREEN, (CENTER_X, CENTER_Y + crosshair_mid_gap), (CENTER_X, CENTER_Y + crosshair_size), crosshair_line_width)


# ---------------------------- Render all lines and texts functions ----------------------------------------

# Render HUD lines and texts
def render_hud(pitch, roll, yaw, v_speed, alt, speed_3d, sats, course, vbat, current, home_dist, home_dir):
    
        # Clear screen
        screen.fill(BLACK)

        # Draw horizon lines
        draw_horizon_lines(pitch, roll, yaw = 0)

        # Draw center crosshair
        draw_center_crosshair()

        # Draw 3D speed meter (left side of HUD)
        draw_speedmeter(speed_3d)

        # 3D speed text (left side of HUD)
        draw_text(f"{int(speed_3d)}", CENTER_X - 45, CENTER_Y, align="right")

        # Draw altitude meter (right side of HUD)
        draw_altmeter(alt)

        # Altitude text (right side of HUD)
        draw_text(f"{int(alt)}", CENTER_X + 45, CENTER_Y, align="left")

        # Info texts (bottom right side of HUD)
        draw_text(f"BAT {vbat:.1f}V", CENTER_X + 33, CENTER_Y + 30, align="left", font=font_small)
        draw_text(f"CUR {current:.1f}A", CENTER_X + 33, CENTER_Y + 35, align="left", font=font_small)
        draw_text(f"HOME {home_dist}m", CENTER_X + 33, CENTER_Y + 40, align="left", font=font_small)
        draw_text(f"HOME {home_dir}°", CENTER_X + 33, CENTER_Y + 45, align="left", font=font_small)


#---------------------------- Setup for Threading environment & SPI Display ----------------------------------------

# Get MSP data snapshot safely (Prevent data flow interruption in multi-threading environment)
def get_msp_snapshot(msp):
    with msp.data_lock:
        return dict(msp.data)

# RGB888 to RGB565 conversion function
def rgb888_to_rgb565(raw, width, height):
    arr = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))

    # Flip screen vertically (enable with reflect HUD screen)
    #arr = arr[::-1, :, :]

    r = (arr[:, :, 0] >> 3).astype(np.uint16)
    g = (arr[:, :, 1] >> 2).astype(np.uint16)
    b = (arr[:, :, 2] >> 3).astype(np.uint16)

    rgb565 = (r << 11) | (g << 5) | b

    rgb565_be = rgb565.byteswap()

    return rgb565_be.tobytes()


#---------------------------- Main loop with MSP data ----------------------------------------

# Main loop with MSP data
def main(MSP_data):
    while True:
        clock.tick(FPS)

        snap = get_msp_snapshot(MSP_Read_pi)

        pitch = snap["pitch"] if snap["pitch"] is not None else 0.0
        roll  = snap["roll"]  if snap["roll"]  is not None else 0.0
        yaw   = snap["yaw"]   if snap["yaw"]   is not None else 0.0
        alt = snap["alt"] if snap["alt"] is not None else 0.0
        v_speed = snap["v_speed"] if snap["v_speed"] is not None else 0.0
        speed_3d = snap["speed_3d"] if snap["speed_3d"] is not None else 0.0
        sats = snap["sats"] if snap["sats"] is not None else 0
        course = snap["course"] if snap["course"] is not None else 0
        vbat = snap["vbat"] if snap["vbat"] is not None else 0.0
        current = snap["current"] if snap["current"] is not None else 0.0
        home_dist = snap["home_dist"] if snap["home_dist"] is not None else 0
        home_dir = snap["home_dir"] if snap["home_dir"] is not None else 0

        # Render HUD
        render_hud(pitch, roll, yaw, v_speed, alt, speed_3d, sats, course, vbat, current, home_dist, home_dir)

        # Get pygame surface data
        raw = pygame.image.tostring(screen, "RGB")
        # Convert RGB888 to RGB565
        buf = rgb888_to_rgb565(raw, WIDTH, HEIGHT)
        # ST7789 Display update (block write)
        disp_7789._block(0, 0, WIDTH - 1, HEIGHT - 1, buf)



# Execute at develop environment
if __name__ == "__main__":

    # ---------------------------- Base Configuration ----------------------------------------

    # Init 7789 SPI Display
    spi = busio.SPI(board.SCK, MOSI=board.MOSI)

    cs_7789  = digitalio.DigitalInOut(board.D5)
    dc_7789  = digitalio.DigitalInOut(board.D25)
    rst_7789 = digitalio.DigitalInOut(board.D22)

    disp_7789 = ST7789.ST7789(
        spi,
        cs=cs_7789,
        dc=dc_7789,
        rst=rst_7789,
        width=135,
        height=240,
        rotation=0,
        x_offset=53,
        y_offset=40,
        baudrate=36000000
    )

    t_init = time.time()

    # Generate virtual MSP data for testing
    def virtual_MSP_data():
        t = time.time()
        dt = t - t_init

        # Generate virtual MSP data values
        pitch = math.sin(dt * 1) * 10
        roll  = math.sin(dt * 1.5) * 10
        yaw = 45 + math.sin(dt * 0.2) * 180
        alt = 2250 + math.sin(dt * 1 + 1) * 30
        speed_3d = 110 + math.sin(dt * 1 + 1) * -20
        sats = 10 + int((math.sin(dt * 0.2) + 1) * 5)
        course = 45 + (int(math.sin(dt * 0.2) * 180 % 360))
        vbat = 15.8 + (math.sin(dt * 1) * 1)
        current = 12.5 + math.sin(dt * 1) * -5
        home_dist = 512 + int(math.sin(dt * 1) * 5)
        home_dir = (int(dt * 10) % 360)

        return pitch, roll, yaw, alt, speed_3d, sats, course, vbat, current, home_dist, home_dir

    # Main loop with virtual MSP data values
    while True:
        clock.tick(FPS)

        # Get virtual MSP data values
        pitch, roll, yaw, alt, speed_3d, sats, course, vbat, current, home_dist, home_dir = virtual_MSP_data()

        # Render HUD
        render_hud(pitch, roll, yaw, v_speed, alt, speed_3d, sats, course, vbat, current, home_dist, home_dir)

        # Get pygame surface data
        raw = pygame.image.tostring(screen, "RGB")
        # Convert RGB888 to RGB565
        buf = rgb888_to_rgb565(raw, WIDTH, HEIGHT)
        # ST7789 Display update (block write)
        disp_7789._block(0, 0, WIDTH - 1, HEIGHT - 1, buf)