import threading
import time
import sys
import pygame
import board
import digitalio
import busio
import numpy as np

# 모듈 임포트
import MSP_Read_pi
import HUD_pi_114
import HUD_pi_085
import MFD_pi_096
import MAP_pi_096
import INFO_pi_096

import adafruit_rgb_display.st7735 as ST7735
import adafruit_rgb_display.st7789 as ST7789

# ==========================================================
# [Setting] Select display and module
# If you enter only the display you want to use, the rest is automatically disabled
# ==========================================================
# [설정] 디스플레이와 모듈을 선택하세요
# 원하는 디스플레이만 입력하면 나머지는 자동으로 비활성화됩니다.
# ==========================================================
# Example(예시)
# {
#   "Display_2": "MFD_0.96",
#   "Display_3": "MAP_0.96",
# } 
# ==========================================================
SELECTED_DISPLAYS = {
    "Display_1": "HUD_1.14",
    "Display_2": "MAP_0.96",
    "Display_3": "MFD_0.96",
    "Display_4": "INFO_0.96",
}
# ==========================================================


# Define SPI pinmap of Raspberry Pi
DISPLAY_HARDWARE_MAP = {
    "Display_1": {"cs": board.D5,  "dc": board.D25, "rst": board.D22},
    "Display_2": {"cs": board.D6,  "dc": board.D24, "rst": board.D27},
    "Display_3": {"cs": board.D13, "dc": board.D23, "rst": board.D17},
    "Display_4": {"cs": board.D19, "dc": board.D26, "rst": board.D16}
}

# Mapping module file names to entered module names
MODULE_MAP = {
    "HUD_1.14": HUD_pi_114,
    "HUD_0.85": HUD_pi_085,
    "MFD_0.96": MFD_pi_096,
    "MAP_0.96": MAP_pi_096,
    "INFO_0.96" : INFO_pi_096
}

# Set framerate config
HIGH_FPS = 30
LOW_FPS = 15

# Init SPI bus
spi = busio.SPI(board.SCK, MOSI=board.MOSI)

# Map of driver name to constructor
DRIVER_MAP = {
    "ST7735": ST7735.ST7735R,
    "ST7789": ST7789.ST7789
}

# Initializes the appropriate display for the hardware pin 
# based on the ID and module object received from SELECTED_DISPLAYS.
def init_display(display_id, module_obj):

    hw_cfg = DISPLAY_HARDWARE_MAP[display_id]
    mod_cfg = module_obj.DISPLAY_CONFIG

    driver_name = mod_cfg.get("driver")
    constructor = DRIVER_MAP.get(driver_name)
    
    if constructor is None:
        raise RuntimeError(f"Unsupported driver: {driver_name}")

    # Set SPI pins (based on DISPLAY_HARDWARE_MAP)
    cs = digitalio.DigitalInOut(hw_cfg["cs"])
    dc = digitalio.DigitalInOut(hw_cfg["dc"])
    rst = digitalio.DigitalInOut(hw_cfg["rst"])

    # Make display configs dictionary
    display_kwargs = {
        "spi": spi,
        "cs": cs,
        "dc": dc,
        "rst": rst,
        "width": mod_cfg.get("width"),
        "height": mod_cfg.get("height"),
        "rotation": mod_cfg.get("rotation"),
        "x_offset": mod_cfg.get("x_offset"),
        "y_offset": mod_cfg.get("y_offset"),
        "baudrate": mod_cfg.get("baudrate")
    }

    # Add invert factor when driver is ST7735
    if driver_name == "ST7735":
        display_kwargs["invert"] = mod_cfg.get("invert")
    
    disp = constructor(**display_kwargs)
    
    return disp

# RGB888 to RGB565 conversion function
def rgb888_to_rgb565(raw, width, height):
    arr = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
    r = (arr[:, :, 0] >> 3).astype(np.uint16)
    g = (arr[:, :, 1] >> 2).astype(np.uint16)
    b = (arr[:, :, 2] >> 3).astype(np.uint16)
    rgb565 = (r << 11) | (g << 5) | b
    return rgb565.byteswap().tobytes()

# Get MSP data snapshot safely (Prevent data flow interruption in multi-threading environment)
def get_msp_snapshot():
    with MSP_Read_pi.data_lock:
        return dict(MSP_Read_pi.data)

# Thread target: render and draw display loop for each module
def display_loop(module, disp, width, height, fps):

    # Get pygame screen elements from each module
    module.screen = pygame.Surface((width, height))
    module.WIDTH, module.HEIGHT = width, height
    module.CENTER_X, module.CENTER_Y = width / 2, height / 2

    clock = pygame.time.Clock()

    # Render fixed components
    if hasattr(module, "render_mfd_fixed"):
        module.render_mfd_fixed()
    if hasattr(module, "render_info_fixed"):
        module.render_info_fixed()

    # Render dynamic components
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
        rssi = snap["rssi"] if snap["rssi"] is not None else 0.0
        throttle = snap["throttle"] if snap["throttle"] is not None else 0.0
        home_dist = snap["home_dist"] if snap["home_dist"] is not None else 0
        home_dir = snap["home_dir"] if snap["home_dir"] is not None else 0

        # Call rendering function by module
        if hasattr(module, "render_hud"):
            module.render_hud(pitch, roll, yaw, v_speed, alt, speed_3d, sats, course, vbat, current, home_dist, home_dir)
        elif hasattr(module, "render_mfd_dynamic"):
            module.render_mfd_dynamic(pitch, roll, yaw, v_speed, alt, speed_3d, sats, course, vbat, current, home_dist, home_dir)
        elif hasattr(module, "render_map"):
            module.render_map(yaw, v_speed, alt, lat, lon, speed_3d, sats, course, vbat, current, home_dist, home_dir)
        elif hasattr(module, "render_info_dynamic"):
            module.render_info_dynamic(vbat, current, rssi, throttle)

        if module == HUD_pi_114 or module == HUD_pi_085:    # Flip screen vertically (enable with reflect screen) 
            #flipped = flip_surface_vertical(module.screen)
            #raw = pygame.image.tostring(flipped, "RGB")
            pass
        elif module == MFD_pi_096 or module == INFO_pi_096:  # Set surface order and send to display
            module.screen.blit(module.background_surface, (0,0))    # bottom surface
            module.screen.blit(module.dynamic_surface, (0,0))
            module.screen.blit(module.fixed_surface, (0,0))         # top surface

        # Get pygame surface data
        raw = pygame.image.tostring(module.screen, "RGB")
        # Convert RGB888 to RGB565
        buf = rgb888_to_rgb565(raw, width, height)
        # Display update (block write)
        disp._block(0, 0, width - 1, height - 1, buf)

# Run
def main():

    # Start MSP reading thread
    threading.Thread(target=MSP_Read_pi.main, daemon=True).start()

    pygame.init()
    Display_thread_lists = []

    # Set all CS pins to HIGH (Prevent bus collisions)
    print("--- Deactivating all CS pins ---")
    unused_cs_pins = []
    for disp_id, pins in DISPLAY_HARDWARE_MAP.items():
        cs_pin = digitalio.DigitalInOut(pins["cs"])
        cs_pin.direction = digitalio.Direction.OUTPUT
        cs_pin.value = True  # set HIGH
        unused_cs_pins.append(cs_pin)

    print("--- Display Initialization Start ---")

    # Get displays and modules from SELECTED_DISPLAYS and start loop threads
    for disp_id, mod_key in SELECTED_DISPLAYS.items():
        # Check hardware pinmap exist
        if disp_id not in DISPLAY_HARDWARE_MAP:
            print(f"Skip: {disp_id} is not defined in Hardware Map.")
            continue
            
        # Get module objects
        module_obj = MODULE_MAP.get(mod_key)
        if module_obj is None:
            print(f"Skip: Module {mod_key} not found in Module Map.")
            continue

        # Initialize display
        try:
            disp_hw = init_display(disp_id, module_obj)
            width = module_obj.DISPLAY_CONFIG["width"]
            height = module_obj.DISPLAY_CONFIG["height"]

            # Set loop framerate
            if "HUD" in mod_key:
                fps = HIGH_FPS
            else:
                fps = LOW_FPS

            # Start display render and draw loop
            loop = threading.Thread(target=display_loop, args=(module_obj, disp_hw, width, height, fps), daemon=True)
            loop.start()
            Display_thread_lists.append(loop)
            print(f"Success: {disp_id} initialized with {mod_key}")
            
        except Exception as e:
            print(f"Failed to init {disp_id} ({mod_key}): {e}")

    print(f"--- {len(Display_thread_lists)} Displays Running ---")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()