import MSP_Read_pi

import pygame
import board
import digitalio
import busio
import math
import time
import numpy as np

import adafruit_rgb_display.st7735 as ST7735


# Display hardware configuration (used by SPI_out_main to initialize)
DISPLAY_CONFIG = {
    "driver": "ST7735",
    "width": 80,
    "height": 160,
    "rotation": 0,
    "x_offset": 24,
    "y_offset": 0,
    "baudrate": 60000000,
    "invert": False
}


# ---------------------------- GUI Configuration ----------------------------------------

# Display settings
WIDTH, HEIGHT = 80, 160
FPS = 15


# ---------------------------- Base Configuration ----------------------------------------

# Set center point
CENTER_X, CENTER_Y = WIDTH / 2, HEIGHT / 2

# Set colors
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
screen.fill(BLACK)
clock = pygame.time.Clock()

# Load fonts
font = pygame.font.Font("/boot/firmware/OpenCockpit/ViperDisplay-Bold.ttf", 8)
font_mid = pygame.font.Font("/boot/firmware/OpenCockpit/ViperDisplay-Bold.ttf", 6)
font_small = pygame.font.Font("/boot/firmware/OpenCockpit/ViperDisplay-Bold.ttf", 5)
font_tiny = pygame.font.Font("/boot/firmware/OpenCockpit/ViperDisplay-Bold.ttf", 3)


# ---------------------------- Map Configuration ----------------------------------------

# MAP Configuration
MAP_PATH = "/boot/firmware/OpenCockpit/map.png"
MAP_LAT_TOP, MAP_LON_LEFT     = 36.5667, 127.1867
MAP_LAT_BOTTOM, MAP_LON_RIGHT = 36.3263, 127.6326

'''      Map configuration diagram

After you capture map image from online map service,
note down the latitude and longitude of top-left and bottom-right corners

When you capture map image, more than 40 pixels per 1 kilometers is recommended resolution

 (MAP_LAT_TOP,MAP_LON_LEFT) @ --------------
                            |              |
                            |              |
                            |   map.png    |
                            |              |
                            |              |
                            |              |
                            ---------------@ (MAP_LAT_BOTTOM,MAP_LON_RIGHT)
'''


# MAP Rotation control
ROTATE_HZ = 15.0
ROTATE_DT = 1.0 / ROTATE_HZ

# Overscan size (map rotation diagonal safe)
OVERSCAN = int(math.sqrt(WIDTH**2 + HEIGHT**2)) + 1


# ---------------------------- FC data Variables (for testing) ----------------------------------------
yaw = 0.0               # deg
v_speed = 21.0          # vertical speed
lat = 36.45325          # latitude
lon = 127.40603         # longitude
alt = 256               # altitude
speed_3d = 94           # 3d speed
sats = 10               # GPS satellites count
course = 123            # GPS course
vbat = 16.2             # voltage
current = 12.5          # ampere
home_dist = 512         # meter
home_dir = 30           # degree


# Calculate pixel position from lat/lon
def position_to_pixel(lat, lon, img_w, img_h):
    x = (lon - MAP_LON_LEFT) / (MAP_LON_RIGHT - MAP_LON_LEFT) * img_w
    y = (MAP_LAT_TOP - lat) / (MAP_LAT_TOP - MAP_LAT_BOTTOM) * img_h
    return x, y


# ---------------------------- Draw GUI components functions ----------------------------------------

# ---------------- MAP STATIC RESOURCES ----------------
map_img = pygame.image.load(MAP_PATH).convert()
MAP_W, MAP_H = map_img.get_size()

last_rotate_time = 0.0
rotated_cache = None
last_heading = None

# Draw MAP and rotate function
def draw_MAP(lat, lon, yaw, sats, course, speed_3d):

    global last_rotate_time, rotated_cache, last_heading

    # ---------------- Heading selection ----------------
    if sats > 3 and speed_3d > 1.5:
        heading = course
    else:
        heading = yaw

    # Set heading step
    HEADING_STEP = 1.0
    heading = round(heading / HEADING_STEP) * HEADING_STEP

    # ---------------- GPS → map pixel ----------------
    px, py = position_to_pixel(lat, lon, MAP_W, MAP_H)

    # ---------------- Overscan crop ----------------
    crop_x = int(px - OVERSCAN // 2)
    crop_y = int(py - OVERSCAN // 2)

    overscan_surf = pygame.Surface((OVERSCAN, OVERSCAN))
    overscan_surf.fill(BLACK)

    src_x = max(0, crop_x)
    src_y = max(0, crop_y)

    dst_x = max(0, -crop_x)
    dst_y = max(0, -crop_y)

    src_w = min(MAP_W - src_x, OVERSCAN - dst_x)
    src_h = min(MAP_H - src_y, OVERSCAN - dst_y)

    if src_w > 0 and src_h > 0:
        overscan_surf.blit(
            map_img,
            (dst_x, dst_y),
            area=(src_x, src_y, src_w, src_h)
        )

    # ---------------- Rotate (ROTATE_HZ applied) ----------------
    now = time.time()
    time_ok = (now - last_rotate_time) >= ROTATE_DT

    if rotated_cache is None or time_ok:
        rotated_cache = pygame.transform.rotate(overscan_surf, heading)
        last_rotate_time = now

    # ---------------- Final crop ----------------
    rw, rh = rotated_cache.get_size()
    fx = (rw - WIDTH) // 2
    fy = (rh - HEIGHT) // 2

    screen.blit(
        rotated_cache,
        (0, 0),
        area=(fx, fy, WIDTH, HEIGHT)
    )

# Draw crosshair function
def draw_crosshair(surface):
    cx, cy = WIDTH // 2, HEIGHT // 2
    size = 6
    pygame.draw.line(surface, BLACK, (cx - size - 2, cy), (cx + size + 2, cy), 3)
    pygame.draw.line(surface, BLACK, (cx, cy - size - 2), (cx, cy + size + 2), 3)
    pygame.draw.line(surface, WHITE, (cx - size, cy), (cx + size, cy), 1)
    pygame.draw.line(surface, WHITE, (cx, cy - size), (cx, cy + size), 1)

# Draw text function
def draw_text(text, x, y, align="left", font=font, color=BLACK):
    surf = font.render(text, True, color)
    rect = surf.get_rect()
    if align == "right":
        rect.topright = (x, y)
    else:
        rect.topleft = (x, y)
    screen.blit(surf, rect)

# Render MAP function
def render_map(yaw, v_speed, alt, lat, lon, speed_3d, sats, course, vbat, current, home_dist, home_dir):

    # Map rendering logic here
    draw_MAP(lat, lon, yaw, sats, course, speed_3d)

    # Draw crosshair
    draw_crosshair(screen)

    # Draw position text
    draw_text(f"Lat {lat:.5f}", CENTER_X - 35, CENTER_Y - 70, align="left", font=font_small, color=BLACK)
    draw_text(f"Lon {lon:.5f}", CENTER_X - 35, CENTER_Y - 65, align="left", font=font_small, color=BLACK)


#---------------------------- Setup for Threading environment & SPI Display ----------------------------------------

# Get MSP data snapshot safely (Prevent data flow interruption in multi-threading environment)
def get_msp_snapshot(msp):
    with msp.data_lock:
        return dict(msp.data)

# RGB888 to RGB565 conversion function
def rgb888_to_rgb565(raw, width, height):
    arr = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))

    r = (arr[:, :, 0] >> 3).astype(np.uint16)
    g = (arr[:, :, 1] >> 2).astype(np.uint16)
    b = (arr[:, :, 2] >> 3).astype(np.uint16)

    rgb565 = (r << 11) | (g << 5) | b

    rgb565_be = rgb565.byteswap()

    return rgb565_be.tobytes()


#---------------------------- Main loop with MSP data ----------------------------------------

# Main loop with MSP data
def main(msp_data):
    while True:
        clock.tick(FPS)

        snap = get_msp_snapshot(MSP_Read_pi)

        # Get MSP data from MSP_Read module
        yaw   = snap["yaw"]   if snap["yaw"]   is not None else 0.0
        alt = snap["alt"] if snap["alt"] is not None else 0.0
        lat = snap["lat"] if snap["lat"] is not None else (MAP_LAT_TOP + MAP_LAT_BOTTOM) / 2
        lon = snap["lon"] if snap["lon"] is not None else (MAP_LON_LEFT + MAP_LON_RIGHT) / 2
        v_speed = snap["v_speed"] if snap["v_speed"] is not None else 0.0
        speed_3d = snap["speed_3d"] if snap["speed_3d"] is not None else 0.0
        sats = snap["sats"] if snap["sats"] is not None else 0
        course = snap["course"] if snap["course"] is not None else 0
        vbat = snap["vbat"] if snap["vbat"] is not None else 0.0
        current = snap["current"] if snap["current"] is not None else 0.0
        home_dist = snap["home_dist"] if snap["home_dist"] is not None else 0
        home_dir = snap["home_dir"] if snap["home_dir"] is not None else 0

        # Render MAP
        render_map(yaw, v_speed, alt, lat, lon, speed_3d, sats, course, vbat, current, home_dist, home_dir)

        # Get pygame surface data
        raw = pygame.image.tostring(screen, "RGB")
        # Convert RGB888 to RGB565
        buf = rgb888_to_rgb565(raw, WIDTH, HEIGHT)
        # ST7789 Display update (block write)
        disp_7735._block(0, 0, WIDTH - 1, HEIGHT - 1, buf)


# Execute at develop environment
if __name__ == "__main__":

    # ---------------------------- Base Configuration ----------------------------------------

    # Init 7735 SPI display
    spi = busio.SPI(board.SCK, MOSI=board.MOSI)

    # 제어 핀
    cs_7735  = digitalio.DigitalInOut(board.D13)
    dc_7735  = digitalio.DigitalInOut(board.D23)
    rst_7735 = digitalio.DigitalInOut(board.D17)

    disp_7735 = ST7735.ST7735R(
        spi,
        cs=cs_7735,
        dc=dc_7735,
        rst=rst_7735,
        width=80,
        height=160,
        rotation=0,
        x_offset=24,
        y_offset=0,
        baudrate=36000000
)

    t_init = time.time()

    # Generate virtual MSP data for testing
    def virtual_MSP_data():
        t = time.time()
        dt = t - t_init

        # Generate virtual MSP data values
        yaw = 45 + math.sin(dt * 0.2) * 180
        alt = 250 + math.sin(dt * 1 + 1) * 30
        lon = (MAP_LON_LEFT + MAP_LON_RIGHT) / 2 + math.sin(dt * 0.4) * 0.003
        lat = (MAP_LAT_TOP + MAP_LAT_BOTTOM) / 2 + math.sin(dt * 0.4) * 0.003
        speed_3d = 110 + math.sin(dt * 1 + 1) * -20
        sats = 10 + int((math.sin(dt * 0.2) + 1) * 5)
        course = 45 + (int(math.sin(dt * 0.2) * 180 % 360))
        vbat = 15.8 + (math.sin(dt * 1) * 1)
        current = 12.5 + math.sin(dt * 1) * -5
        home_dist = 512 + int(math.sin(dt * 1) * 5)
        home_dir = (int(dt * 10) % 360)

        return yaw, v_speed, alt, lat, lon, speed_3d, sats, course, vbat, current, home_dist, home_dir
    
    # Main loop with virtual MSP data values
    while True:
        clock.tick(FPS)

        # Get virtual MSP data values
        yaw, v_speed, alt, lat, lon, speed_3d, sats, course, vbat, current, home_dist, home_dir = virtual_MSP_data()

        # Render MAP
        render_map(yaw, v_speed, alt, lat, lon, speed_3d, sats, course, vbat, current, home_dist, home_dir)
        
        # Get pygame surface data
        raw = pygame.image.tostring(screen, "RGB")
        # Convert RGB888 to RGB565
        buf = rgb888_to_rgb565(raw, WIDTH, HEIGHT)
        # ST7789 Display update (block write)
        disp_7735._block(0, 0, WIDTH - 1, HEIGHT - 1, buf)