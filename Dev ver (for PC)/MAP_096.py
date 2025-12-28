import pygame
import math
import sys
import time


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
font = pygame.font.Font("C:/Users/dbstj/Desktop/Project/5. OpenCockpit/ViperDisplay-Bold.ttf", 8)
font_mid = pygame.font.Font("C:/Users/dbstj/Desktop/Project/5. OpenCockpit/ViperDisplay-Bold.ttf", 6)
font_small = pygame.font.Font("C:/Users/dbstj/Desktop/Project/5. OpenCockpit/ViperDisplay-Bold.ttf", 5)
font_tiny = pygame.font.Font("C:/Users/dbstj/Desktop/Project/5. OpenCockpit/ViperDisplay-Bold.ttf", 3)


# ---------------------------- Map Configuration ----------------------------------------

# MAP Configuration
MAP_PATH = "C:/Users/dbstj/Desktop/Project/5. OpenCockpit/map.png"
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

    final_view = pygame.Surface((WIDTH, HEIGHT))
    final_view.blit(
        rotated_cache,
        (0, 0),
        area=(fx, fy, WIDTH, HEIGHT)
    )

    screen.blit(final_view, (0, 0))

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
        yaw = msp_data["yaw"] if msp_data["yaw"] is not None else 0.0
        alt = msp_data["alt"] if msp_data["alt"] is not None else 0.0
        lat = msp_data["lat"] if msp_data["lat"] is not None else (MAP_LAT_TOP + MAP_LAT_BOTTOM) / 2
        lon = msp_data["lon"] if msp_data["lon"] is not None else (MAP_LON_LEFT + MAP_LON_RIGHT) / 2
        v_speed = msp_data["v_speed"] if msp_data["v_speed"] is not None else 0.0
        speed_3d = msp_data["speed_3d"] if msp_data["speed_3d"] is not None else 0.0
        sats = msp_data["sats"] if msp_data["sats"] is not None else 0
        course = msp_data["course"] if msp_data["course"] is not None else 0
        vbat = msp_data["vbat"] if msp_data["vbat"] is not None else 0.0
        current = msp_data["current"] if msp_data["current"] is not None else 0.0
        home_dist = msp_data["home_dist"] if msp_data["home_dist"] is not None else 0
        home_dir = msp_data["home_dir"] if msp_data["home_dir"] is not None else 0

        # Render MAP
        render_map(yaw, v_speed, alt, lat, lon, speed_3d, sats, course, vbat, current, home_dist, home_dir)

        pygame.display.flip()


# Execute at develop environment
if __name__ == "__main__":

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

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # Get virtual MSP data values
        yaw, v_speed, alt, lat, lon, speed_3d, sats, course, vbat, current, home_dist, home_dir = virtual_MSP_data()

        # Key controls for testing
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            lat += 0.001
        if keys[pygame.K_s]:
            lat -= 0.001
        if keys[pygame.K_a]:
            lon -= 0.001
        if keys[pygame.K_d]:
            lon += 0.001
        if keys[pygame.K_e]:
            course += 2
        if keys[pygame.K_q]:
            course -= 2

        # Render MAP
        render_map(yaw, v_speed, alt, lat, lon, speed_3d, sats, course, vbat, current, home_dist, home_dir)
        
        pygame.display.flip()