import HUD_114
import HUD_085
import MFD_096
import MAP_096
import MSP_Read

import threading
import time

def start_MSP_reading():
    msp_thread = threading.Thread(target=MSP_Read.main, daemon=True)
    msp_thread.start()

# MSP 읽기 시작
start_MSP_reading()
time.sleep(1)

# HUD 1.14인치 메인 루프
HUD_114.main(MSP_Read.data)

# HUD 0.85인치 메인 루프
#HUD_085.main(MSP_Read.data)

# MFD 0.96인치 메인 루프
#MFD_096.main(MSP_Read.data)

# MAP 0.96인치 메인 루프
#MAP_096.main(MSP_Read.data)