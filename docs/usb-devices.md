# USB devices and udev rules

All the robot's serial devices are on one powered 7-port USB hub (Realtek `0bda:5411`, two cascaded
4-port chips) at USB path `1-4`. udev gives each one a fixed name, which the configs use instead
of `ttyUSB*` / `ttyACM*`.

| Device | Hub port | USB path | Name | Identified by | Used in |
|---|---|---|---|---|---|
| Shark (base motor board) | 1 | `1-4.1` | `/dev/ttySHARK` | port | `config/robot/v1.yaml`, `config/robot/v2.yaml` (`device`) |
| IMU (BNO055) | 3 | `1-4.3` | `/dev/ttyIMU` | port | `imu_port` arg of `fbot_bringup/sensors.launch.py` |
| Hokuyo front (ground) | 5 | `1-4.4.2` | `/dev/sensors/hokuyo_H1309411` | laser ID | `config/sensors/urg_ground.yaml` |
| Hokuyo rear | 7 | `1-4.4.4` | `/dev/sensors/hokuyo_H1309421` | laser ID | `config/sensors/urg_back.yaml` |

Hub ports 1-3 are `1-4.1`..`1-4.3`; ports 4-7 are on the second chip, `1-4.4.1`..`1-4.4.4`.
Both chips are self-powered and multi-TT, so it makes no difference which port a device uses
(power or bandwidth). Mapping verified on the robot on 2026-11-10.

## Shark and IMU: by port

`/etc/udev/rules.d/90-shark-mb.rules`:

```
SUBSYSTEM=="tty", KERNELS=="1-4.1", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", SYMLINK+="ttySHARK", GROUP="dialout", MODE="0660"
SUBSYSTEM=="tty", KERNELS=="1-4.3", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", SYMLINK+="ttyIMU", GROUP="dialout", MODE="0660"
```

Both use a cloned FT232R (`0403:6001`) with the **same** serial number, `A50285BI` (a known
counterfeit-chip serial), so they cannot be told apart by serial: **keep the Shark on port 1 and
the IMU on port 3**. Swapping them swaps the names silently. Do not add a rule by serial (an old
`91-shark-serial.rules` did this and pointed `ttySHARK` at the IMU).

## Hokuyos: by laser ID, any port

`/etc/udev/rules.d/99-sensors.rules`:

```
KERNEL=="ttyACM[0-9]*", SUBSYSTEMS=="usb", ATTRS{idVendor}=="15d1", ATTRS{idProduct}=="0000", MODE="0666", GROUP="dialout", PROGRAM="/usr/bin/env LD_LIBRARY_PATH=/opt/ros/humble/lib /opt/ros/humble/lib/urg_node/getID %N q", SYMLINK+="sensors/hokuyo_%c"
```

The rule reads the ID from the laser itself, so the name follows the laser, not the port. A
replaced laser gets its own ID: update `serial_port` in the yaml, not the rule.
Read a laser's ID by hand:
`LD_LIBRARY_PATH=/opt/ros/humble/lib /opt/ros/humble/lib/urg_node/getID /dev/ttyACM0 q`

## Checking or moving devices

```
ls -l /dev/ttySHARK /dev/ttyIMU /dev/sensors/      # current links
udevadm info -q path -n /dev/ttyUSB0               # USB path of a device (e.g. .../1-4/1-4.3/...)
udevadm info -a -n /dev/ttyUSB0 | grep -E 'KERNELS|idVendor|idProduct|serial'
```

To find which laser or port is which, unplug one device and see which link disappears. After
editing a rule:
`sudo udevadm control --reload && sudo udevadm trigger --subsystem-match=tty`
