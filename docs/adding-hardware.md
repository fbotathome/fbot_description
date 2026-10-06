# Adding or changing hardware

## A new sensor

1. **Model.** If there is no macro for it yet, add `urdf/sensors/<sensor>.xacro` (a macro with
   `parent`, `xyz`, `rpy`, `name`) and its meshes under `meshes/sensors/`.
2. **Place it.** Include the macro in `urdf/boris.urdf.xacro` and instantiate it on `base_link`
   or `dorso_link`. Measure the position from the base center (`base_link` is at the center of
   the base box, `base_height/2 + caster_height` above the floor).
3. **Driver.** Put the driver parameters in `config/sensors/<sensor>.yaml` and start the driver in
   `fbot_bringup/launch/sensors.launch.py` behind a `use_<sensor>` flag (add the flag to
   `boris.launch.py` as well).
4. **Frame.** The driver's `frame_id` must be exactly the URDF link name, otherwise TF cannot
   place the data (this was the case for the IMU: `bno055` vs `imu_link`).
5. Run `colcon test --packages-select fbot_description` and look at it with
   `ros2 launch fbot_description display.launch.py`.

## Moving a sensor or changing the body

v2: change the CAD in Onshape, re-export and re-run `tools/v2_from_onshape.py` (see `v2_from_onshape.md`).
v1: edit the `xyz`/`rpy` in `urdf/v1/robot.xacro` (sensors) or the dimensions in `urdf/v1/body.xacro`
(torso, arm plate). If the outline of the robot changes, redraw `footprint` in `config/robot/<v>.yaml` (Nav2
footprint, polygon in `base_footprint`, meters).

## A new base

Add `config/robot/<version>.yaml` and `urdf/<version>/robot.xacro` (copy v2, which reads every pose
from the yaml) and start with `robot_version:=<version>`. Nothing else holds base dimensions: the URDF, the ros2_control block
and the diff-drive controller all read this file. Then calibrate odometry (`calibration.md`).

## The arm

The arm is not part of this description; it has its own model and MoveIt stack.
`fbot_bringup/launch/manipulator.launch.py` (included by the task launches that manipulate)
starts it and attaches it to BORIS with one static transform `arm_mount_link -> <arm root>`
(`world` for the xArm6, `wx200/base_link` for the WidowX). The plate `arm_mount_link` is in the
URDF by default (`use_arm_mount`), at height `arm_z_position` on the torso.

- Arm pose on the plate: `mount_xyz` / `mount_rpy` arguments of `manipulator.launch.py`
  (defaults in its `ARMS` table; the xArm pose is still a TODO).
- Wrist camera: the RealSense on the xArm wrist needs a transform from the arm's end effector to
  `realsense_link` (not set up yet; measure / hand-eye calibrate, then add it to
  `manipulator.launch.py`).
