# Robot versions and odometry calibration

`robot_version:=v1|v2` selects `config/robot/<version>.yaml`. That file is the only source of the
base geometry and is read by:

- `urdf/base/base.xacro` (wheel positions and sizes),
- `urdf/base/base_ros2_control.xacro` (driver serial port, max velocity),
- `fbot_bringup/launch/base.launch.py` (merges `wheel.radius` / `wheel.separation` into the
  diff-drive controller parameters).

So the model, the driver and odometry cannot disagree.

> `v2.yaml` is generated from the Onshape CAD (`tools/v2_from_onshape.py`, see `v2_from_onshape.md`):
> wheel radius 0.0984 and separation 0.344 are CAD values. Calibrate them on the robot; the
> multipliers in `config/boris_controllers.yaml` survive re-running the tool.

## What the numbers do

- **wheel.radius**: commanded speed and odometry distance both scale with it. If the real radius
  is larger than configured, the robot drives faster than commanded and `/odom` under-reports
  distance by the same ratio.
- **wheel.separation**: odometry yaw scales with `1/separation`. Too small a value makes `/odom`
  over-report rotation.

The EKF fuses IMU yaw, which hides rotation errors; nothing hides distance errors except AMCL.

## Calibration

With the robot on the floor and `ros2 launch fbot_bringup robot.launch.py` running:

1. **Distance.** Mark 2 m on the floor. Drive straight at 0.2 m/s
   (`ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}"`) and stop at
   the mark. Read the distance from `/odom`.
   `radius_new = radius_old * real_distance / odom_distance`
2. **Rotation.** Spin in place (`angular.z: 0.3`) exactly 360 degrees (use a floor mark).
   `separation_new = separation_old * odom_yaw / real_yaw`
3. Write the values in `config/robot/<version>.yaml`, rebuild, repeat until the error is a few %.

Fine adjustments without touching the geometry: `wheel_separation_multiplier`,
`left_wheel_radius_multiplier`, `right_wheel_radius_multiplier` in `config/boris_controllers.yaml`.
