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


BAT_CELL_NUMBER = 4

# ---------------------------- GUI Configuration ----------------------------------------

# Display settings
WIDTH, HEIGHT = 80, 160
FPS = 15


# ---------------------------- Base Configuration ----------------------------------------

# Set center point
CENTER_X, CENTER_Y = WIDTH / 2, HEIGHT / 2

# Set colors
GREEN = (0, 255, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
CYAN = (0, 169, 183)

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# Set surface
background_surface = pygame.Surface((WIDTH, HEIGHT))
dynamic_surface    = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
fixed_surface      = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

background_surface.fill(BLACK)

# Load fonts
font = pygame.font.Font("/boot/firmware/OpenCockpit/ViperDisplay-Bold.ttf", 8)
font_mid = pygame.font.Font("/boot/firmware/OpenCockpit/ViperDisplay-Bold.ttf", 6)
font_small = pygame.font.Font("/boot/firmware/OpenCockpit/ViperDisplay-Bold.ttf", 5)
font_tiny = pygame.font.Font("/boot/firmware/OpenCockpit/ViperDisplay-Bold.ttf", 3)


# ---------------------------- FC data Variables (for testing) ----------------------------------------
vbat = 15.4             # voltage
current = 23.5          # ampere
rssi = 500              # radio rssi 0 ~ 1023
throttle = 1500         # radio throttle 1000 ~ 2000


# ---------------------------- GUI draw functions ----------------------------------------

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


# ---------------------------- Draw vcell Gauge function ----------------------------------------

# Set circle parameters
cx_vcell, cy_vcell = CENTER_X - 15, CENTER_Y - 50
r_vcell = 16
start_angle_deg_vcell = 120
end_angle_deg_vcell = 360

# Set min/max voltage
min_vcell = 2.8
max_vcell = 4.2

# Draw arc (fixed components)
def draw_vcell_gauge_fixed(surface, max_vcell):

    # Set arc drawing parameters
    segments = 60 # number of line segments for smooth arc
    
    # Draw arc using line segments for smoother appearance
    for i in range(segments):

        # Determine arc color based on segment number
        if i < 8: color = RED
        elif i < 38: color = YELLOW
        else: color = GREEN
        
        angle1_deg = start_angle_deg_vcell + (end_angle_deg_vcell - start_angle_deg_vcell) * i / segments
        angle2_deg = start_angle_deg_vcell + (end_angle_deg_vcell - start_angle_deg_vcell) * (i + 1) / segments
        
        rad1, rad2 = math.radians(angle1_deg), math.radians(angle2_deg)
        x1 = cx_vcell + math.cos(rad1) * r_vcell
        y1 = cy_vcell + math.sin(rad1) * r_vcell
        x2 = cx_vcell + math.cos(rad2) * r_vcell
        y2 = cy_vcell + math.sin(rad2) * r_vcell
        
        # Use anti-aliased lines for smoother arc
        pygame.draw.aaline(surface, color, (int(x1), int(y1)), (int(x2), int(y2)))
        # fallback thinner line to ensure visibility
        pygame.draw.line(surface, color, (int(x1), int(y1)), (int(x2), int(y2)), 1)

    # text_scale: show only multiples of this value
    text_scale = 0.5
    value = min_vcell
    
    # Draw numeric labels and small ticks along the arc
    while value <= max_vcell:
        # Calculate the percentage of the current value in the full range (min to max)
        t = (value - min_vcell) / (max_vcell - min_vcell)
        angle_deg = start_angle_deg_vcell + t * (end_angle_deg_vcell - start_angle_deg_vcell)
        rad = math.radians(angle_deg)

        # tick positions on arc
        arc_x = cx_vcell + math.cos(rad) * (r_vcell + 1)
        arc_y = cy_vcell + math.sin(rad) * (r_vcell + 1)

        # tick toward center
        tick_in_x = cx_vcell + math.cos(rad) * (r_vcell - 2)
        tick_in_y = cy_vcell + math.sin(rad) * (r_vcell - 2)
        pygame.draw.line(surface, WHITE, (int(arc_x), int(arc_y)), (int(tick_in_x), int(tick_in_y)), 1)

        # label position slightly inside the tick
        label_r = r_vcell - 7
        label_x = cx_vcell + math.cos(rad) * label_r
        label_y = cy_vcell + math.sin(rad) * label_r

        surf = font_small.render(f"{value:.1f}", True, WHITE)
        rect = surf.get_rect(center=(int(label_x), int(label_y)))
        surface.blit(surf, rect)
        
        value += text_scale

    # Draw unit
    draw_text(surface, "V", cx_vcell + 30, cy_vcell + 5, font=font_mid, align="right", color=WHITE)

# Draw needle and text (Dynamic components)
def draw_vcell_gauge_dynamic(surface, vbat):

    vcell = vbat / BAT_CELL_NUMBER

    # Limit needle position (min~max)
    vcell_needle = vcell
    if vcell > max_vcell:
        vcell_needle = max_vcell
    elif vcell < min_vcell:
        vcell_needle = min_vcell

    # Needle angle calculation
    t = (vcell_needle - min_vcell) / (max_vcell - min_vcell)
    angle = start_angle_deg_vcell + t * (end_angle_deg_vcell - start_angle_deg_vcell)
    rad = math.radians(angle)

    nx = cx_vcell + math.cos(rad) * (r_vcell - 2)
    ny = cy_vcell + math.sin(rad) * (r_vcell - 2)

    # Draw needle
    pygame.draw.line(surface, WHITE, (cx_vcell, cy_vcell), (nx, ny), 2)

    # Draw value text box
    box_points = [(cx_vcell + 3, cy_vcell + 3), (cx_vcell + 23, cy_vcell + 3), (cx_vcell + 23, cy_vcell + 12), (cx_vcell + 3, cy_vcell + 12)]
    pygame.draw.polygon(surface, BLACK, box_points)
    pygame.draw.polygon(surface, WHITE, box_points, 1)
    # Draw value text
    draw_text(surface, f"{vcell:.2f}", cx_vcell + 22, cy_vcell + 5, font=font_mid, align="right", color=GREEN)


# ---------------------------- Draw current Gauge function ----------------------------------------

# Set circle parameters
cx_current, cy_current = CENTER_X - 15, CENTER_Y - 15
r_current = 14
start_angle_deg_current = 120
end_angle_deg_current = 360

# Set min/max current
min_current = 0
max_current = 100

# Draw arc (fixed components)
def draw_current_gauge_fixed(surface, max_current):

    # Set arc drawing parameters
    segments = 60 # number of line segments for smooth arc
    
    # Draw arc using line segments for smoother appearance
    for i in range(segments):

        color = WHITE
        
        angle1_deg = start_angle_deg_current + (end_angle_deg_current - start_angle_deg_current) * i / segments
        angle2_deg = start_angle_deg_current + (end_angle_deg_current - start_angle_deg_current) * (i + 1) / segments
        
        rad1, rad2 = math.radians(angle1_deg), math.radians(angle2_deg)
        x1 = cx_current + math.cos(rad1) * r_current
        y1 = cy_current + math.sin(rad1) * r_current
        x2 = cx_current + math.cos(rad2) * r_current
        y2 = cy_current + math.sin(rad2) * r_current
        
        # Use anti-aliased lines for smoother arc
        pygame.draw.aaline(surface, color, (int(x1), int(y1)), (int(x2), int(y2)))
        # fallback thinner line to ensure visibility
        pygame.draw.line(surface, color, (int(x1), int(y1)), (int(x2), int(y2)), 1)

    # text_scale: show only multiples of this value
    text_scale = 30
    value = min_current
    
    # Draw numeric labels and small ticks along the arc
    while value <= max_current:
        # Calculate the percentage of the current value in the full range (min to max)
        t = (value - min_current) / (max_current - min_current)
        
        angle_deg = start_angle_deg_current + t * (end_angle_deg_current - start_angle_deg_current)
        rad = math.radians(angle_deg)

        # tick positions on arc
        arc_x = cx_current + math.cos(rad) * (r_current + 1)
        arc_y = cy_current + math.sin(rad) * (r_current + 1)

        # tick toward center
        tick_in_x = cx_current + math.cos(rad) * (r_current - 2)
        tick_in_y = cy_current + math.sin(rad) * (r_current - 2)
        pygame.draw.line(surface, WHITE, (int(arc_x), int(arc_y)), (int(tick_in_x), int(tick_in_y)), 1)

        # label position slightly inside the tick
        label_r = r_current - 6
        label_x = cx_current + math.cos(rad) * label_r
        label_y = cy_current + math.sin(rad) * label_r

        surf = font_tiny.render(f"{value}", True, WHITE)
        rect = surf.get_rect(center=(int(label_x), int(label_y)))
        surface.blit(surf, rect)
        
        value += text_scale

    # Draw unit
    draw_text(surface, "A", cx_current + 28, cy_current + 5, font=font_mid, align="right", color=WHITE)

# Draw needle and text (Dynamic components)
def draw_current_gauge_dynamic(surface, current):

    # Limit needle position (min~max)
    current_needle = current
    if current > max_current:
        current_needle = max_current

    # Needle angle calculation
    t = (current_needle - min_current) / (max_current - min_current)
    angle = start_angle_deg_current + t * (end_angle_deg_current - start_angle_deg_current)
    rad = math.radians(angle)

    nx = cx_current + math.cos(rad) * (r_current - 2)
    ny = cy_current + math.sin(rad) * (r_current - 2)

    # Draw needle
    pygame.draw.line(surface, WHITE, (cx_current, cy_current), (nx, ny), 2)

    # Draw value text box
    box_points = [(cx_current + 3, cy_current + 3), (cx_current + 21, cy_current + 3), (cx_current + 21, cy_current + 12), (cx_current + 3, cy_current + 12)]
    pygame.draw.polygon(surface, BLACK, box_points)
    pygame.draw.polygon(surface, WHITE, box_points, 1)
    # Draw value text
    draw_text(surface, f"{int(current)}", cx_current + 20, cy_current + 5, font=font_mid, align="right", color=GREEN)


# ---------------------------- Draw rssi Gauge function ----------------------------------------

# Set circle parameters
cx_rssi, cy_rssi = CENTER_X - 15, CENTER_Y + 20
r_rssi = 14
start_angle_deg_rssi = 120
end_angle_deg_rssi = 360

# Set min/max rssi
min_rssi = 0
max_rssi = 1000

# Draw arc (fixed components)
def draw_rssi_gauge_fixed(surface, max_rssi):

    # Set arc drawing parameters
    segments = 60 # number of line segments for smooth arc
    
    # Draw arc using line segments for smoother appearance
    for i in range(segments):
        
        # Determine arc color based on segment number
        if i < 10: color = YELLOW
        else: color = WHITE
        
        angle1_deg = start_angle_deg_rssi + (end_angle_deg_rssi - start_angle_deg_rssi) * i / segments
        angle2_deg = start_angle_deg_rssi + (end_angle_deg_rssi - start_angle_deg_rssi) * (i + 1) / segments
        
        rad1, rad2 = math.radians(angle1_deg), math.radians(angle2_deg)
        x1 = cx_rssi + math.cos(rad1) * r_rssi
        y1 = cy_rssi + math.sin(rad1) * r_rssi
        x2 = cx_rssi + math.cos(rad2) * r_rssi
        y2 = cy_rssi + math.sin(rad2) * r_rssi
        
        # Use anti-aliased lines for smoother arc
        pygame.draw.aaline(surface, color, (int(x1), int(y1)), (int(x2), int(y2)))
        # fallback thinner line to ensure visibility
        pygame.draw.line(surface, color, (int(x1), int(y1)), (int(x2), int(y2)), 1)

    # text_scale: show only multiples of this value
    text_scale = 300
    value = min_rssi
    
    # Draw numeric labels and small ticks along the arc
    while value <= max_rssi:
        # Calculate the percentage of the current value in the full range (min to max)
        t = (value - min_rssi) / (max_rssi - min_rssi)
        angle_deg = start_angle_deg_rssi + t * (end_angle_deg_rssi - start_angle_deg_rssi)
        rad = math.radians(angle_deg)

        # tick positions on arc
        arc_x = cx_rssi + math.cos(rad) * (r_rssi + 1)
        arc_y = cy_rssi + math.sin(rad) * (r_rssi + 1)

        # tick toward center
        tick_in_x = cx_rssi + math.cos(rad) * (r_rssi - 2)
        tick_in_y = cy_rssi + math.sin(rad) * (r_rssi - 2)
        pygame.draw.line(surface, WHITE, (int(arc_x), int(arc_y)), (int(tick_in_x), int(tick_in_y)), 1)

        # label position slightly inside the tick
        label_r = r_rssi - 6
        label_x = cx_rssi + math.cos(rad) * label_r
        label_y = cy_rssi + math.sin(rad) * label_r

        surf = font_tiny.render(f"{value}", True, WHITE)
        rect = surf.get_rect(center=(int(label_x), int(label_y)))
        surface.blit(surf, rect)
        
        value += text_scale

# Draw needle and text (Dynamic components)
def draw_rssi_gauge_dynamic(surface, rssi):

    # Limit needle position (min~max)
    rssi_needle = rssi
    if rssi > max_rssi:
        rssi_needle = max_rssi

    # Needle angle calculation
    t = (rssi_needle - min_rssi) / (max_rssi - min_rssi)
    angle = start_angle_deg_rssi + t * (end_angle_deg_rssi - start_angle_deg_rssi)
    rad = math.radians(angle)

    nx = cx_rssi + math.cos(rad) * (r_rssi - 2)
    ny = cy_rssi + math.sin(rad) * (r_rssi - 2)

    # Draw needle
    pygame.draw.line(surface, WHITE, (cx_rssi, cy_rssi), (nx, ny), 2)

    # Draw value text box
    box_points = [(cx_rssi + 3, cy_rssi + 3), (cx_rssi + 21, cy_rssi + 3), (cx_rssi + 21, cy_rssi + 12), (cx_rssi + 3, cy_rssi + 12)]
    pygame.draw.polygon(surface, BLACK, box_points)
    pygame.draw.polygon(surface, WHITE, box_points, 1)
    # Draw value text
    draw_text(surface, f"{int(rssi)}", cx_rssi + 20, cy_rssi + 5, font=font_mid, align="right", color=GREEN)


# ---------------------------- Draw throttle Gauge function ----------------------------------------

# Set gauge parameters
startx_throttle, starty_throttle = CENTER_X + 25, CENTER_Y + 23
gauge_length = 50

min_throttle = 1000
max_throttle = 2000

# Draw gauge stick (fixed components)
def draw_throttle_gauge_fixed(surface):

    draw_text(surface, "THR", startx_throttle, starty_throttle - gauge_length - 3, font=font_mid, align="CENTER", color=WHITE)

    pygame.draw.line(surface, WHITE, (startx_throttle, starty_throttle), (startx_throttle, starty_throttle - gauge_length), 1)


# Draw line and text (Dynamic components)
def draw_throttle_gauge_dynamic(surface, throttle):

    throttle_line = throttle
    if throttle > max_throttle:
        throttle_line = max_throttle
    elif throttle < min_throttle:
        throttle_line = min_throttle

    # Calculate throttle point
    throttle_line = (throttle - min_throttle) / (max_throttle - min_throttle) * gauge_length

    # Draw throttle tick
    pygame.draw.line(surface, GREEN, (startx_throttle - 5, starty_throttle - throttle_line), (startx_throttle + 3, starty_throttle - throttle_line), 2)

    # Draw throttle tick triangle
    throttle_points = [(startx_throttle - 5, starty_throttle - throttle_line), (startx_throttle - 5, starty_throttle - throttle_line + 1),
                       (startx_throttle - 8, starty_throttle - throttle_line + 1 + 2), (startx_throttle - 8, starty_throttle - throttle_line - 2)]
    pygame.draw.polygon(surface, GREEN, throttle_points)
    
    # Draw value text box
    box_points = [(startx_throttle - 10, starty_throttle), (startx_throttle + 10, starty_throttle),
                  (startx_throttle + 10, starty_throttle + 9), (startx_throttle - 10, starty_throttle + 9)]
    pygame.draw.polygon(surface, BLACK, box_points)
    pygame.draw.polygon(surface, WHITE, box_points, 1)
    # Draw value text
    draw_text(surface, f"{int(throttle)}", startx_throttle + 1, starty_throttle + 5, font=font_mid, align="RIGHT", color=GREEN)


# ---------------------------- INFO Render Function ----------------------------------------

# Draw fixed parts
def render_info_fixed():
    
    fixed_surface.fill((0,0,0,0))

    # Draw top text box
    box_points = [(CENTER_X + 27, 1), (CENTER_X + 38, 1),
                  (CENTER_X + 38, 8), (CENTER_X + 27, 8)]
    pygame.draw.polygon(fixed_surface, BLACK, box_points)
    pygame.draw.polygon(fixed_surface, CYAN, box_points, 1)

    # Draw top text
    draw_text(fixed_surface, "HYD  ELEC  FUEL  ECS  ENG", 40, 5, font=font_small, align="LEFT", color=CYAN)

    draw_vcell_gauge_fixed(fixed_surface, max_vcell)
    draw_current_gauge_fixed(fixed_surface, max_current)
    draw_rssi_gauge_fixed(fixed_surface, max_rssi)
    draw_throttle_gauge_fixed(fixed_surface)

    # Draw bottom lines
    pygame.draw.line(fixed_surface, WHITE, (0, CENTER_Y + 40), (WIDTH, CENTER_Y + 40), 1)
    pygame.draw.line(fixed_surface, WHITE, (CENTER_X, CENTER_Y + 40), (CENTER_X, HEIGHT - 15), 1)

    # Draw bottom text
    draw_text(fixed_surface, "SYS  WARN  NAV  INST  GPS", 40, HEIGHT - 5, font=font_small, align="LEFT", color=CYAN)

# Draw moving parts
def render_info_dynamic(vbat, current, rssi, throttle):

    dynamic_surface.fill((0,0,0,0))

    draw_vcell_gauge_dynamic(dynamic_surface, vbat)
    draw_current_gauge_dynamic(dynamic_surface, current)
    draw_rssi_gauge_dynamic(dynamic_surface, rssi)
    draw_throttle_gauge_dynamic(dynamic_surface, throttle)


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
def main(MSP_data):

    # Render fixed parts of MFD
    render_info_fixed()

    while True:
        clock.tick(FPS)

        snap = get_msp_snapshot(MSP_Read_pi)

        # Get MSP data from MSP_Read module
        vbat = snap["vbat"] if snap["vbat"] is not None else 0.0
        current = snap["current"] if snap["current"] is not None else 0.0
        rssi = snap["rssi"] if snap["rssi"] is not None else 0.0
        throttle = snap["throttle"] if snap["throttle"] is not None else 0.0

        # Render dynamic parts of INFO
        render_info_dynamic(vbat, current, rssi, throttle)

        # Set surface order
        screen.blit(background_surface, (0,0)) # bottom surface
        screen.blit(dynamic_surface, (0,0))
        screen.blit(fixed_surface, (0,0)) # top surface

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
    cs_7735  = digitalio.DigitalInOut(board.D19)
    dc_7735  = digitalio.DigitalInOut(board.D26)
    rst_7735 = digitalio.DigitalInOut(board.D16)

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
        vbat = 15.4 + (math.sin(dt * 1) * -0.5)
        current = 35.4 + math.sin(dt * 1) * 15
        rssi = 600 + math.sin(dt * 2) * 50
        throttle = 1700 + math.sin(dt * 1) * 200

        return vbat, current, rssi, throttle
    
    # Render fixed parts of MFD
    render_info_fixed()

    # Main loop with virtual MSP data values
    while True:    
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # Get virtual MSP data values
        vbat, current, rssi, throttle = virtual_MSP_data()

        # Key controls for testing
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            vbat += 0.5
        if keys[pygame.K_s]:
            vbat -= 0.5
        if keys[pygame.K_a]:
            current -= 1
        if keys[pygame.K_d]:
            current += 1
        if keys[pygame.K_t]:
            rssi += 1
        if keys[pygame.K_g]:
            rssi -= 1
        if keys[pygame.K_r]:
            throttle += 1
        if keys[pygame.K_f]:
            throttle -= 1

        # Render dynamic parts of INFO
        render_info_dynamic(vbat, current, rssi, throttle)

        # Set surface order
        screen.blit(background_surface, (0,0))  # bottom surface
        screen.blit(dynamic_surface, (0,0))
        screen.blit(fixed_surface, (0,0))       # top surface

        # Get pygame surface data
        raw = pygame.image.tostring(screen, "RGB")
        # Convert RGB888 to RGB565
        buf = rgb888_to_rgb565(raw, WIDTH, HEIGHT)
        # ST7789 Display update (block write)
        disp_7735._block(0, 0, WIDTH - 1, HEIGHT - 1, buf)