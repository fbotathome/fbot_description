<div align="center">

<img width="5526" height="719" alt="fbot_description" src="https://github.com/user-attachments/assets/187e3dbd-cea4-45d1-9aa3-75a74ff18341" />

<br>

![UBUNTU](https://img.shields.io/badge/UBUNTU-22.04-orange?style=for-the-badsge&logo=ubuntu)
![python](https://img.shields.io/badge/python-3.10-blue?style=for-the-badsge&logo=python)
![ROS2](https://img.shields.io/badge/ROS2-Humble-blue?style=for-the-badsge&logo=ros)

**ROS 2 robot description packages for BORIS and related platforms in RoboCup@Home competitions**

[Overview](#overview) • [Architecture](#architecture) • [Installation](#installation) • [Usage](#usage) • [Development](#development)

</div>

---

## Overview

This repository contains ROS 2 description packages for the BORIS robot and related platforms, including URDFs, meshes, launch files, configuration, and control setups. These packages provide the physical and simulation models, sensor integration, and control interfaces required for RoboCup@Home and other robotics competitions.

---

## Architecture

### Repository Structure

```
boris_description/         # Main robot description, URDF, launch, config
boris_head_description/   # Head and sensor description, meshes, URDF
logistic_description/     # Logistic robot variant, URDF, launch, config
sensors_description/      # Sensor integration, meshes, config, launch
shark_description/        # Shark robot variant, URDF, launch, config
```

#### Example Package Layout

```
boris_description/
├── CMakeLists.txt
├── package.xml
├── config/                # Controller configs
├── launch/                # Launch files
├── rviz/                  # RViz configs
├── urdf/                  # Xacro/URDF files
boris_head_description/
├── CMakeLists.txt
├── package.xml
├── config/                # Head controller configs
├── launch/                # Launch files
├── meshes/                # 3D models (STL/DAE)
├── urdf/                  # Head URDF
logistic_description/
├── CMakeLists.txt
├── package.xml
├── config/                # Controller configs
├── launch/                # Launch files
├── urdf/                  # Xacro/URDF files
sensors_description/
├── CMakeLists.txt
├── package.xml
├── config/                # Sensor configs (LIDAR, IMU, etc)
├── launch/                # Sensor launch files
├── meshes/                # Sensor meshes
├── urdf/                  # Sensor Xacro/URDF files
shark_description/
├── CMakeLists.txt
├── package.xml
├── config/                # Controller configs
├── launch/                # Launch files
├── ros2_control/          # Control Xacro files
├── urdf/                  # Shark Xacro/URDF files
```

---

## Installation

### Prerequisites

- ROS2 Humble
- Python 3.10+
- Ubuntu 22.04
- Dependencies listed in each `package.xml` and `requirements.txt` (if present)

### Setup

1. **Clone the repository into your ROS workspace:**
   ```bash
   cd ~/fbot_ws/src
   git clone <this-repo-url>
   ```

2. **Install dependencies:**
   ```bash
   cd ~/fbot_ws
   sudo rosdep init  # Skip if already initialized
   rosdep update
   rosdep install --from-paths src --ignore-src -r -y
   # For sensors_description:
   pip install -r src/sensors_description/requirements.txt
   ```

3. **Build the workspace:**
   ```bash
   cd ~/fbot_ws
   colcon build --packages-select boris_description boris_head_description logistic_description sensors_description shark_description
   source install/setup.bash
   ```

---

## Usage

### Launch Robot Description

Each robot and sensor package provides launch files for simulation and visualization. Example:

```bash
# Launch BORIS robot description
ros2 launch boris_description boris_description.launch.py

# Launch BORIS head controller
ros2 launch boris_head_description doris_head_controller.launch

# Launch sensors (e.g., Hokuyo, Velodyne)
ros2 launch sensors_description hokuyo.launch.py
ros2 launch sensors_description velodyne.launch.py
```

### RViz Visualization

```bash
# Open RViz with robot model
ros2 run rviz2 rviz2 -d $(ros2 pkg prefix boris_description)/share/boris_description/rviz/boris.rviz
ros2 run rviz2 rviz2 -d $(ros2 pkg prefix sensors_description)/share/sensors_description/rviz/velodyne.rviz
```

---

## Development

1. Create a feature branch (`git checkout -b feat/amazing-feature`)
2. Add or modify URDF/Xacro, meshes, configs, or launch files in the appropriate package
3. Update `package.xml` and `CMakeLists.txt` if needed
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feat/amazing-feature`)
6. Open a Pull Request

---
