# Adding or changing hardware

## A new sensor

1. **Model.** If there is no macro for it yet, add `urdf/sensors/<sensor>.xacro` (a macro with
   `parent`, `xyz`, `rpy`, `name`) and its meshes under `meshes/sensors/`.
2. **Place it.** Include the macro in `urdf/boris.urdf.xacro` and instantiate it on `base_link`
   or `dorso_link`. Measure the position from the base center (`base_link` is at the center of
   the base box, `base_height/2 + caster_height` above the floor).
3. **Driver.** Put the driver parameters in `config/sensors/<sensor>.yaml` and start the driver in
   `fbot_bringup/launch/sensors.launch.py` behind a `use_<sensor>` flag (add the flag to
   `robot.launch.py` as well).
4. **Frame.** The driver's `frame_id` must be exactly the URDF link name, otherwise TF cannot
   place the data (this was the case for the IMU: `bno055` vs `imu_link`).
5. Run `colcon test --packages-select fbot_description` and look at it with
   `ros2 launch fbot_description display.launch.py`.

## Moving a sensor or changing the body

Edit the `xyz`/`rpy` in `urdf/boris.urdf.xacro` (sensors) or the dimensions in `urdf/body.xacro`
(torso, arm plate). If the outline of the robot changes, redraw `config/footprint.yaml` (Nav2
footprint, polygon in `base_footprint`, meters).

## A new base

Add `config/base/<version>.yaml` (copy `v1.yaml`, keep the keys) and start with
`base_version:=<version>`. Nothing else holds base dimensions: the URDF, the ros2_control block
and the diff-drive controller all read this file. Then calibrate odometry (`calibration.md`).

## The arm

The arm is not part of the description. `robot.launch.py use_arm:=true` adds the empty mounting
plate (`arm_mount_link`, height `arm_z_position`) and starts `fbot_bringup/launch/arm.launch.py`,
which attaches the arm's own model with a static transform.
