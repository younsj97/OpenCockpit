import serial
import struct
import time
import math
import threading

data_lock = threading.Lock()

# ---------------------------- Base Configuration ----------------------------------------

# Set serial port and baudrate
PORT = "/dev/ttyS0"
BAUDRATE = 115200

# Frequencies of MSP requests and Display output
FAST_HZ = 30   # ATTITUDE MSP Frequency
SLOW_HZ = 15   # Others MSP Frequency
OUT_HZ  = 30   # Print Frequency

FAST_DT = 1.0 / FAST_HZ
SLOW_DT = 1.0 / SLOW_HZ
OUT_DT  = 1.0 / OUT_HZ

# MSP IDs (INAV)
MSP_ATTITUDE   = 108
MSP_ALTITUDE   = 109
MSP_RAW_GPS    = 106
MSP_ANALOG     = 110
MSP_COMP_GPS   = 107
MSP_CURRENT    = 23

# ---------------------------- MSP Communication Functions ----------------------------------------

# MSP checksum function
def msp_checksum(data):
    c = 0
    for b in data:
        c ^= b
    return c

# MSP request function
def send_msp_request(ser, cmd):
    frame = bytearray(b"$M<")
    frame.append(0)
    frame.append(cmd)
    frame.append(msp_checksum(frame[3:5]))
    ser.write(frame)

# MSP response reading function
def read_msp_response(ser):
    # Header
    if ser.read(1) != b"$":
        return None
    if ser.read(1) != b"M":
        return None
    if ser.read(1) != b">":
        return None

    size_b = ser.read(1)
    if len(size_b) != 1:
        return None
    size = size_b[0]

    cmd_b = ser.read(1)
    if len(cmd_b) != 1:
        return None
    cmd = cmd_b[0]

    payload = ser.read(size)
    if len(payload) != size:
        return None

    chk_b = ser.read(1)
    if len(chk_b) != 1:
        return None
    checksum = chk_b[0]

    if msp_checksum(bytes([size, cmd]) + payload) != checksum:
        return None

    return cmd, payload



# ---------------------------------------- MSP Data Parsers ----------------------------------------

def parse_attitude(p):
    roll, pitch, yaw = struct.unpack("<hhh", p[:6])
    return roll/10.0, pitch/10.0, yaw

def parse_altitude(p):
    alt_cm, vario_cm_s, _ = struct.unpack("<ihh", p[:8])
    return alt_cm/100.0, vario_cm_s/100.0

def parse_gps(p):
    fix, sats, lat, lon, alt, speed, course = struct.unpack("<BBiiiHH", p[:18])
    if fix == 0:
        return {
            "lat": None, "lon": None,
            "speed": None, "sats": sats,
            "course": None
        }
    return {
        "lat": lat / 1e7 if fix >= 2 else None,
        "lon": lon / 1e7 if fix >= 2 else None,
        "speed": speed / 100.0 if fix >= 2 else None,
        "sats": sats, "course": course
    }

def parse_analog(p):
    if len(p) < 3:
        return None, None
    vbat_raw, current_raw = struct.unpack("<BH", p[:3])
    vbat = vbat_raw / 10.0          # V
    current = current_raw / 100.0   # A
    return vbat, current

def parse_home(p):
    dist, direction = struct.unpack("<Hh", p[:4])
    return dist, direction


# ---------------------------------------- Main ----------------------------------------

data = {
        "roll": None, "pitch": None, "yaw": None,
        "alt": None, "v_speed": None,
        "lat": None, "lon": None,
        "speed": None, "sats": None, "course": None,
        "vbat": None, "current": None,
        "home_dist": None, "home_dir": None,
        "speed_3d": None
    }

def main():
    ser = serial.Serial(PORT, BAUDRATE, timeout=0.01)
    time.sleep(0.5)

    print("MSP read and output started.")

    t_fast = t_slow = t_out = time.time()

    while True:
        now = time.time()

        # MSP Requests_Fast Frequency
        if now - t_fast >= FAST_DT:
            send_msp_request(ser, MSP_ATTITUDE)
            t_fast = now

        # MSP Requests_Slow Frequency
        if now - t_slow >= SLOW_DT:
            send_msp_request(ser, MSP_ALTITUDE)
            send_msp_request(ser, MSP_RAW_GPS)
            send_msp_request(ser, MSP_ANALOG)
            send_msp_request(ser, MSP_CURRENT)
            send_msp_request(ser, MSP_COMP_GPS)
            t_slow = now

        # Read Responses
        read_until = now + 0.005
        while time.time() < read_until:
            resp = read_msp_response(ser)
            if not resp:
                continue

            cmd, p = resp

            if cmd == MSP_ATTITUDE:
                roll, pitch, yaw = parse_attitude(p)
                with data_lock:
                    data["roll"] = roll
                    data["pitch"] = pitch
                    data["yaw"] = yaw

            elif cmd == MSP_ALTITUDE:
                with data_lock:
                    data["alt"], data["v_speed"] = parse_altitude(p)

            elif cmd == MSP_RAW_GPS:
                with data_lock:
                    data.update(parse_gps(p))

            elif cmd == MSP_ANALOG:
                with data_lock:
                    data["vbat"], data["current"] = parse_analog(p)

            elif cmd == MSP_COMP_GPS:
                with data_lock:
                    data["home_dist"], data["home_dir"] = parse_home(p)

        # Data Output
        if now - t_out >= OUT_DT:
            t_out = now
            
            # 3D Speed Calculation
            if data["speed"] is not None and data["v_speed"] is not None:
                spd_3d = math.sqrt(data["speed"]**2 + data["v_speed"]**2)
            else:
                spd_3d = None

            with data_lock:
                data["speed_3d"] = spd_3d

            print(
                #f"t_fast:{t_fast:.2f}, t_slow:{t_slow:.2f}, t_out:{t_out:.2f} | "
                f"ROLL:{data['roll']} deg "
                f"PITCH:{data['pitch']} deg "
                f"YAW:{data['yaw']} deg | "
                f"ALT:{data['alt']} m  "
                f"V_SPD:{data['v_speed']} m/s | "
                f"3D_SPD:{data['speed_3d']} m/s | "
                f"LAT:{data['lat']}  "
                f"LON:{data['lon']}  "
                f"GPS_SPD:{data['speed']} m/s  "
                f"SATS:{data['sats']}  "
                f"COURSE:{data['course']}° | "
                f"VBAT:{data['vbat']} V  "
                f"CURRENT:{data['current']} A | "
                f"HOME:{data['home_dist']} m  "
                f"{data['home_dir']}°"
            )

        time.sleep(0.005)


# Execute at develop environment
if __name__ == "__main__":
    main()