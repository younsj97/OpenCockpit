import HUD_pi
import MSP_Read_pi

import threading
import time

def start_MSP_reading():
    msp_thread = threading.Thread(target=MSP_Read_pi.main, daemon=True)
    msp_thread.start()

# MSP 읽기 시작
start_MSP_reading()
time.sleep(2)

# HUD 메인 루프
HUD_pi.main(MSP_Read_pi.data)