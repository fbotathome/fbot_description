# legacy/ (not built)

Previous description packages, kept for reference only. colcon does not look for
packages below another package, so nothing in here is built or installed.

| Folder | Replaced by |
|---|---|
| `boris_description/` | `urdf/boris.urdf.xacro` + `fbot_bringup/launch/robot.launch.py` |
| `shark_description/` | `urdf/base/` + `config/base/<version>.yaml` |
| `sensors_description/` | `urdf/sensors/`, `meshes/sensors/`, `config/sensors/`; driver launches -> `fbot_bringup/launch/sensors.launch.py` (Sick: `fbot_bringup/launch/sick.launch.py`) |
| `logistic_description/` | not replaced (logistic robot variant, Velodyne) |

The former `boris_head_description` became `urdf/neck/neck.xacro` + `meshes/face/`.

To resurrect something, copy the file you need into the package (do not move this
folder back): the paths inside still use the old package names
(`$(find shark_description)`, `package://sensors_description/...`).
