import threading
import time
import sys
import math

import pygame
import board
import digitalio
import busio
import numpy as np

# Import display modules
import MSP_Read_pi
import HUD_pi
import MFD_pi
import MAP_pi

import adafruit_rgb_display.st7735 as st7735_7735
import adafruit_rgb_display.st7789 as st7789_7789

# Central config
DEFAULT_FPS = 30
MAP_FPS = 15

# Utility: create busio.SPI once and share
spi = busio.SPI(board.SCK, MOSI=board.MOSI)

# Map of driver name to constructor
DRIVER_MAP = {
    "ST7735": st7735_7735.ST7735R,
    "ST7789": st7789_7789.ST7789,
}

# Helper to create digitalio pin from name string like 'D5'
def pin_from_name(name):
    # Expect format 'D<number>' -> attribute on board
    try:
        return getattr(board, name)
    except Exception:
        # Fallback: if already a pin or object, return as-is
        return name

# Initialize display from DISPLAY_CONFIG dict
def init_display(cfg):
    driver_name = cfg.get("driver")
    constructor = DRIVER_MAP.get(driver_name)
    if constructor is None:
        raise RuntimeError(f"Unsupported driver: {driver_name}")

    cs = digitalio.DigitalInOut(pin_from_name(cfg["cs_pin"]))
    dc = digitalio.DigitalInOut(pin_from_name(cfg["dc_pin"]))
    rst = digitalio.DigitalInOut(pin_from_name(cfg["rst_pin"]))

    disp = constructor(
        spi,
        cs=cs,
        dc=dc,
        rst=rst,
        width=cfg.get("width"),
        height=cfg.get("height"),
        rotation=cfg.get("rotation"),
        x_offset=cfg.get("x_offset"),
        y_offset=cfg.get("y_offset"),
        baudrate=cfg.get("baudrate"),
    )
    return disp

# RGB888 -> RGB565 conversion (same as modules)
def rgb888_to_rgb565(raw, width, height):
    arr = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
    r = (arr[:, :, 0] >> 3).astype(np.uint16)
    g = (arr[:, :, 1] >> 2).astype(np.uint16)
    b = (arr[:, :, 2] >> 3).astype(np.uint16)
    rgb565 = (r << 11) | (g << 5) | b
    rgb565_be = rgb565.byteswap()
    return rgb565_be.tobytes()

# Safe snapshot helper
def get_msp_snapshot():
    with MSP_Read_pi.data_lock:
        return dict(MSP_Read_pi.data)

# Thread target: run MSP reader (in-process)
def msp_thread():
    MSP_Read_pi.main()

# Screen flip function
def flip_surface_vertical(surface):
    return pygame.transform.flip(surface, False, True)

# Thread target: display loop for a module
def display_loop(module, disp, width, height, fps=DEFAULT_FPS):
    # Create a pygame surface the size expected by module
    # Module rendering functions use global screen variable inside module; monkeypatch it
    module.screen = pygame.Surface((width, height))
    module.WIDTH = width
    module.HEIGHT = height
    module.CENTER_X = width / 2
    module.CENTER_Y = height / 2

    clock = pygame.time.Clock()

    while True:
        clock.tick(fps)

        snap = get_msp_snapshot()

        # Extract fields with None fallback
        pitch = snap["pitch"] if snap["pitch"] is not None else 0.0
        roll  = snap["roll"]  if snap["roll"]  is not None else 0.0
        yaw   = snap["yaw"]   if snap["yaw"]   is not None else 0.0
        alt = snap["alt"] if snap["alt"] is not None else 0.0
        lat = snap["lat"] if snap["lat"] is not None else 36.45325
        lon = snap["lon"] if snap["lon"] is not None else 127.40603
        v_speed = snap["v_speed"] if snap["v_speed"] is not None else 0.0
        speed_3d = snap["speed_3d"] if snap["speed_3d"] is not None else 0.0
        sats = snap["sats"] if snap["sats"] is not None else 0
        course = snap["course"] if snap["course"] is not None else 0
        vbat = snap["vbat"] if snap["vbat"] is not None else 0.0
        current = snap["current"] if snap["current"] is not None else 0.0
        home_dist = snap["home_dist"] if snap["home_dist"] is not None else 0
        home_dir = snap["home_dir"] if snap["home_dir"] is not None else 0

        # Call module-render functions by name
        if hasattr(module, "render_hud"):
            module.render_hud(pitch, roll, yaw, v_speed, alt, speed_3d, sats, course, vbat, current, home_dist, home_dir)
        elif hasattr(module, "render_mfd"):
            module.render_mfd(pitch, roll, yaw, v_speed, alt, speed_3d, sats, course, vbat, current, home_dist, home_dir)
        elif hasattr(module, "render_map"):
            module.render_map(yaw, v_speed, alt, lat, lon, speed_3d, sats, course, vbat, current, home_dist, home_dir)
        else:
            # Try generic render function name
            if hasattr(module, "render"):
                module.render(snap)

        # Get raw surface and send to display
        if module is HUD_pi:
            # Flip screen vertically (enable with reflect HUD screen)
            flipped = flip_surface_vertical(module.screen)
            raw = pygame.image.tostring(flipped, "RGB")
        else:
            raw = pygame.image.tostring(module.screen, "RGB")

        buf = rgb888_to_rgb565(raw, width, height)
        disp._block(0, 0, width - 1, height - 1, buf)

def main():
    # Start MSP thread
    t_msp = threading.Thread(target=msp_thread, daemon=True)
    t_msp.start()

    # Initialize pygame (needed for surfaces)
    pygame.init()

    # Prepare display modules list
    modules = []

    # HUD
    try:
        cfg = HUD_pi.DISPLAY_CONFIG
        disp_hud = init_display(cfg)
        modules.append((HUD_pi, disp_hud, cfg["width"], cfg["height"]))
    except Exception as e:
        print("Failed to init HUD:", e)

    # MFD
    try:
        cfg = MFD_pi.DISPLAY_CONFIG
        disp_mfd = init_display(cfg)
        modules.append((MFD_pi, disp_mfd, cfg["width"], cfg["height"]))
    except Exception as e:
        print("Failed to init MFD:", e)

    # MAP
    try:
        cfg = MAP_pi.DISPLAY_CONFIG
        disp_map = init_display(cfg)
        modules.append((MAP_pi, disp_map, cfg["width"], cfg["height"]))
    except Exception as e:
        print("Failed to init MAP:", e)

    # Start display threads
    threads = []
    for mod, disp, w, h in modules:
        # Choose FPS per module: MAP runs at MAP_FPS, others at DEFAULT_FPS
        if mod is MAP_pi:
            fps = MAP_FPS
        else:
            fps = DEFAULT_FPS
        t = threading.Thread(target=display_loop, args=(mod, disp, w, h, fps), daemon=True)
        t.start()
        threads.append(t)

    # Keep main alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting")
        sys.exit(0)


if __name__ == "__main__":
    main()
