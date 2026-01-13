#!/bin/bash

# Select one mode
# Default : Block wifi / Debug at home : Unblock wifi
sudo rfkill block wifi
#sudo rfkill unblock wifi

sleep 1

# Select one mode
# main.py : Read and display real MSP data of Flight Controller / main_demo.py : Generate virtual MSP data to display demo
sudo python3 /boot/firmware/OpenCockpit/main.py &
#sudo python3 /boot/firmware/OpenCockpit/main_demo.py &