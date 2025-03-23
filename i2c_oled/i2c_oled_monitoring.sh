#!/bin/bash

# Monitoring | OLED I2C [128x32] @ Radxa Rock 5C Lite
# Author: https://github.com/c0m4r
# License: Public Domain

# Vars
CMD="./i2c_oled_monitoring.py"

# Run in loop
while true ; do

  # Metrics / Values
  IP=$(ip a s | grep inet\ | grep global | awk '{print $2}' | cut -f1 -d\/ | head -n 1)
  TEMP=$(sensors | grep C | awk '{print $2}' | sort | tail -n 1)
  LAVG=$(cat /proc/loadavg | awk '{print $1, $2, $3}')
  MEM_AVA=$(cat /proc/meminfo  | grep ^MemAvailable | awk '{print $2}' | awk '{print int($1 / 1024)}')
  ETH_STATE=$(ip link show end1 | grep -o "state [A-Z]*" | awk '{print $2}')
  WLAN_STATE=$(ip link show wlan0 | grep -o "state [A-Z]*" | awk '{print $2}')

  ${CMD} "IP ADDRESS" "${IP}" 12 ; sleep 5
  ${CMD} "TEMPERATURE" "${TEMP}" 18 ; sleep 5
  ${CMD} "LOAD AVERAGE" "${LAVG}" 14 ; sleep 5
  ${CMD} "FREE MEMORY" "${MEM_AVA} MB" 18 ; sleep 5

  if [[ "$ETH_STATE" == "UP" ]]; then
    ${CMD} "ETHERNET" "iface end1 UP" 16 ; sleep 5
  elif [[ "$WLAN_STATE" == "UP" ]]; then
    ${CMD} "WIFI" "iface wlan0 UP" 16 ; sleep 5
  fi

done
