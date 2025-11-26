#!/bin/bash
export ROS_DOMAIN_ID=99
source /opt/ros/humble/setup.bash
source install/setup.bash
exec python3 install/wifi_scanner_node/lib/python3.10/site-packages/wifi_scanner_node/wifi_scanner.py "$@"
