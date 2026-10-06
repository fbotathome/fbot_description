# BORIS v2 from the Onshape CAD

The v2 model (`robot_version:=v2`) is generated from Onshape's **Export URDF** of the whole
robot assembly. The export itself is too heavy and too detailed to use directly (52 links,
550k-vertex parts, the neck exported posed, mates split into prismatic chains, no real
masses), so `tools/v2_from_onshape.py` reduces it to a basic model for navigation, sensors
and actuators:

| Output | Content |
|---|---|
| `config/robot/v2.yaml` | wheels, base box, torso, sensor / neck / arm-mount poses, Nav2 footprint |
| `meshes/v2/*.stl` | one decimated visual mesh per functional link (~1 MB in total) |

Collisions are boxes / cylinders. The xArm is not taken from the CAD: `manipulator.launch.py`
attaches the xArm's own model (`xarm_description`) to `arm_mount_link`.

## Regenerate after a CAD change

```bash
# one-time: tools for the converter (not needed at runtime)
python3 -m venv ~/.venvs/fbot_cad
~/.venvs/fbot_cad/bin/pip install trimesh fast-simplification scipy networkx pyyaml

# 1. Onshape: assembly -> Export -> URDF, mesh format STL. Unzip OUTSIDE the repo, e.g. ~/boris_v2_cad/
# 2. run the converter (from the fbot_description folder)
~/.venvs/fbot_cad/bin/python tools/v2_from_onshape.py ~/boris_v2_cad/Assembly_urdf_stl/assembly_urdf
# 3. check
colcon build --packages-select fbot_description && colcon test --packages-select fbot_description
ros2 launch fbot_description display.launch.py robot_version:=v2
```

The tool prints a report (wheel size, sensor frames, how much the neck was un-posed, mesh
sizes) and keeps the hand-edited `driver` section of `v2.yaml`. Never commit the raw export.

## What the tool assumes about the export

- CAD frame: z up, robot **front = CAD -Y**, robot left = CAD +X.
- The drive wheels are the two disks fused into the base part (`part_1`); they are found by
  fitting circles to its vertices (radius, width, separation, axle position).
- `base_footprint` = floor point under the axle centre (wheel contact), x forward.
- `base_link` = centre of the base hull box; the base mesh and the collision box use it.
- Hokuyo frames: on the URG head axis, in the middle of the narrow head band (scan plane),
  mounted upside down like v1 (`rpy = pi 0 0`, back one also yawed `pi`).
- Sick: the repo's LMS1xx macro is aligned with the CAD box (bottom and centre); its mesh is a
  slightly different LMS1xx model, so the scan-plane height is approximate (a few mm).
- Neck: the export is posed. The neutral pose is rebuilt from the Femto housing frame: pan so
  the camera width is lateral and the camera is in front of the pan axis, tilt so the camera up axis is vertical (Femto Bolt: 115 W x 40 H x 65 D, housing z = up), i.e. the optical
  axis is level. Joints are `head_pan_joint` / `head_tilt_joint` (same as v1).
- Part names are listed at the top of the tool (`GROUPS`, `TORSO`, `SICK`, ...). If Onshape
  renames a part, update them there.

## Before the next export (improves the result, not required)

- Neck: plain revolute mates for pan and tilt at the **neutral** pose (camera level, forward);
  fasten the Femto slider and the "parallel" mate; remove the loop-closure mate.
- Exclude the xArm instance; keep a mate connector at its base.
- Add the IMU, the casters and the wrist RealSense.
- Assign materials to the main parts if real masses are wanted.

## Open items (v2, 2026-10)

- **Casters below the wheels:** the base part has two small circular bodies (front and back,
  probably casters) reaching 1.5 cm below the drive-wheel contact. On a flat floor either the
  wheels would hang or the CAD caster height is wrong. The model takes the floor at the wheel
  contact (`caster_height` < 0 in `v2.yaml`).
- **IMU:** not in the CAD; `sensors.imu` reuses the v1 pose relative to `base_link` (`todo` key).
- **Neck zero:** the neutral pose must match `neck_controller`'s 180-degree motor position;
  check the camera direction in RViz with the real neck.
- **Femto driver frame:** `femtobolt_link` is at the centre of the Femto housing (identity);
  measure / calibrate the offset to the Orbbec device frame.
- **Wrist RealSense:** not modelled; needs a transform from the xArm end effector.
- **Wheels:** radius 0.0984 m, separation 0.344 m are CAD values; calibrate odometry
  (`calibration.md`).
