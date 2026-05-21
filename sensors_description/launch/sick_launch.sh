#!/bin/bash
export ROS_DOMAIN_ID=77

source /opt/ros/humble/setup.bash

source /home/fbot/fbot_ws/install/setup.bash

ros2 launch sensors_description sick_lms_1xx.launch.py