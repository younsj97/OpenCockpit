import HUD
import MFD
import MAP
import MSP_Read

import threading
import time

def start_MSP_reading():
    msp_thread = threading.Thread(target=MSP_Read.main, daemon=True)
    msp_thread.start()

# MSP 읽기 시작
start_MSP_reading()
time.sleep(1)

# HUD 메인 루프
#HUD.main(MSP_Read.data)
hud_thread = threading.Thread(target=HUD.main, args=(MSP_Read.data,), daemon=True)
hud_thread.start()

# MFD 메인 루프
#MFD.main(MSP_Read.data)
mfd_thread = threading.Thread(target=MFD.main, args=(MSP_Read.data,), daemon=True)
mfd_thread.start()

# MAP 메인 루프
#MAP.main(MSP_Read.data)
MAP.main(MSP_Read.data)
map_thread = threading.Thread(target=MAP.main, args=(MSP_Read.data,), daemon=True)