#!/bin/bash

# Monitoring | OLED I2C [128x32] @ Radxa Rock 5C Lite
# Author: https://github.com/c0m4r
# License: Public Domain

# Vars
CMD="./i2c_oled_monitoring.py"
INTERVAL=5 # sleep time between metrics

# Run in loop
while true ; do

  # Metrics / Values
  TIME=$(date +%H:%M:%S)
  IP=$(ip a s | grep inet\ | grep global | awk '{print $2}' | cut -f1 -d\/ | head -n 1)
  CPU_USAGE=$(LC_ALL=c top -b -d 0.5 -n 2 | grep \%Cpu | tail -n 1 | grep -oE "[0-9]{1,3}.[0-9] id" | awk '{print 100 - $1}')
  TEMP=$(sensors | grep C | awk '{print $2}' | sort | tail -n 1)
  LAVG=$(cat /proc/loadavg | awk '{print $1, $2, $3}')
  MEM_AVA=$(cat /proc/meminfo  | grep ^MemAvailable | awk '{print $2}' | awk '{print int($1 / 1024)}')
  ETH_STATE=$(ip link show end1 | grep -o "state [A-Z]*" | awk '{print $2}')
  WLAN_STATE=$(ip link show wlan0 | grep -o "state [A-Z]*" | awk '{print $2}')

  ${CMD} "TIME" "${TIME}" 18 ; sleep ${INTERVAL}
  ${CMD} "IP ADDRESS" "${IP}" 12 ; sleep ${INTERVAL}
  ${CMD} "TEMPERATURE" "${TEMP}" 18 ; sleep ${INTERVAL}
  ${CMD} "LOAD AVERAGE" "${LAVG}" 14 ; sleep ${INTERVAL}
  ${CMD} "CPU USAGE" "${CPU_USAGE}%" 18 ; sleep ${INTERVAL}
  ${CMD} "FREE MEMORY" "${MEM_AVA} MB" 18 ; sleep ${INTERVAL}

  if [[ "$ETH_STATE" == "UP" ]]; then
    ${CMD} "ETHERNET" "iface end1 UP" 16 ; sleep ${INTERVAL}
  elif [[ "$WLAN_STATE" == "UP" ]]; then
    ${CMD} "WIFI" "iface wlan0 UP" 16 ; sleep ${INTERVAL}
  fi

done
