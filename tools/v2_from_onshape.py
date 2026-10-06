#!/usr/bin/env python3
"""Build the BORIS v2 model data from an Onshape URDF export.

Reads the URDF + STL meshes written by Onshape's "Export URDF" (assembly of the whole
robot) and produces, for fbot_description:

  meshes/v2/*.stl          one decimated visual mesh per functional link
  config/robot/v2.yaml     base / wheel / body / sensor / neck / arm-mount poses + footprint
                           (the `driver` section is kept from the existing file)

Re-run it after every new export; it is deterministic. Dev-only dependencies:

  python3 -m venv ~/.venvs/fbot_cad && ~/.venvs/fbot_cad/bin/pip install trimesh fast-simplification pyyaml
  ~/.venvs/fbot_cad/bin/python tools/v2_from_onshape.py ~/boris_v2_cad/Assembly_urdf_stl/assembly_urdf

Conventions of the export (BORIS v2, checked by hand):
  - CAD frame: z up, robot FRONT = CAD -y, robot LEFT = CAD +x.
  - The two drive-wheel disks are fused into the base part (part_1); they are found by
    fitting circles to its vertices.
  - The neck is exported posed; the neutral pose (Femto level, facing forward) is
    recovered from the Femto housing frame (femto_bolt_allcatpart_19).
"""
import argparse
import os
import sys
import xml.etree.ElementTree as ET

import numpy as np
import trimesh
import yaml

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MESH_URI = 'package://fbot_description/meshes/v2/'

# functional links -> CAD parts (link names in the export)
GROUPS = {
    'base': ['part_1', 'suporte_hokuyo', 'suporte_hokuyo_1', 'part_8'],
    'hokuyo_front': ['urg_04lx_ug01'],
    'hokuyo_back': ['urg_04lx_ug01_1'],
    'neck_base': ['part_1_1', 'xl430_body_1'],
    'neck_pan': ['xl430_horn_1', 'xl430_iddler_1', 'part_5', 'f4_bracket', 'part_4', 'part_4_1',
                 'xl430_horn', 'xl430_iddler'],
    'neck_tilt': ['xl430_body', 'part_1_2', 'sup_femto_bolt'],   # + every femto_bolt_* part
}
FACES = {'base': 6000, 'hokuyo': 1500, 'neck_base': 1500, 'neck_pan': 2500, 'neck_tilt': 6000}
TORSO, SICK, ARM_BASE, FEMTO_HOUSING = 'part_2', 'nr1109_lm01_1985', '1305xarm6_p01_95_1', 'femto_bolt_allcatpart_19'
PAN_JOINT, TILT_JOINTS = 'revolute_1', ('revolute_2__1_', 'revolute_1__1__loop_closure')

# CAD -> robot axes: x_robot = -y_cad, y_robot = x_cad, z_robot = z_cad
R_CAD = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])


# ---------------------------------------------------------------- URDF helpers
def rpy_to_matrix(r, p, y):
    cr, sr, cp, sp, cy, sy = np.cos(r), np.sin(r), np.cos(p), np.sin(p), np.cos(y), np.sin(y)
    return np.array([[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
                     [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
                     [-sp, cp * sr, cp * cr]])


def origin_matrix(o):
    xyz = [float(v) for v in (o.get('xyz', '0 0 0') if o is not None else '0 0 0').split()]
    rpy = [float(v) for v in (o.get('rpy', '0 0 0') if o is not None else '0 0 0').split()]
    m = np.eye(4)
    m[:3, :3] = rpy_to_matrix(*rpy)
    m[:3, 3] = xyz
    return m


def rot(axis, angle):
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(angle) * k + (1 - np.cos(angle)) * k @ k


class Export:
    def __init__(self, root_dir):
        self.dir = root_dir
        urdf = os.path.join(root_dir, 'urdf', 'assembly_urdf.urdf')
        self.xml = ET.parse(urdf).getroot()
        self.links = {l.get('name'): l for l in self.xml.findall('link')}
        self.joints = {j.get('name'): j for j in self.xml.findall('joint')}
        self.parent_joint = {j.find('child').get('link'): j for j in self.joints.values()}
        self._world = {}

    def world(self, link):
        if link not in self._world:
            j = self.parent_joint.get(link)
            self._world[link] = np.eye(4) if j is None else \
                self.world(j.find('parent').get('link')) @ origin_matrix(j.find('origin'))
        return self._world[link]

    def joint_world(self, name):
        j = self.joints[name]
        m = self.world(j.find('parent').get('link')) @ origin_matrix(j.find('origin'))
        axis = m[:3, :3] @ np.array([float(v) for v in j.find('axis').get('xyz').split()])
        return m[:3, 3], axis

    def mesh(self, links):
        """All visuals of `links`, merged, in the CAD frame."""
        parts = []
        for name in links:
            for v in self.links[name].findall('visual'):
                fname = v.find('geometry/mesh').get('filename').split('/')[-1]
                m = trimesh.load(os.path.join(self.dir, 'meshes', fname), force='mesh')
                m.apply_transform(self.world(name) @ origin_matrix(v.find('origin')))
                parts.append(m)
        return trimesh.util.concatenate(parts)


# ---------------------------------------------------------------- geometry
def fit_circle(p):
    a = np.c_[2 * p, np.ones(len(p))]
    cy, cz, c = np.linalg.lstsq(a, (p ** 2).sum(1), rcond=None)[0]
    r = np.sqrt(c + cy ** 2 + cz ** 2)
    return np.array([cy, cz]), r, np.abs(np.hypot(*(p - [cy, cz]).T) - r).max()


def find_wheels(base_mesh):
    """Circular disk faces (axis along CAD x) inside the base solid."""
    v = np.unique(np.round(base_mesh.vertices, 6), axis=0)
    faces = []
    for x in np.unique(np.round(v[:, 0], 4)):
        p = v[np.abs(v[:, 0] - x) < 2e-4][:, 1:]
        if len(p) < 16:
            continue
        c, r, err = fit_circle(p)
        if err < 1e-4 and 0.03 < r < 0.2:
            faces.append((x, c, r))
    if len(faces) != 4:
        sys.exit(f'expected 4 wheel disk faces in the base part, found {len(faces)}')
    xs = sorted(f[0] for f in faces)
    radius = float(np.mean([f[2] for f in faces]))
    center_yz = np.mean([f[1] for f in faces], axis=0)
    width = float(xs[1] - xs[0])
    separation = float((xs[3] + xs[2]) / 2 - (xs[1] + xs[0]) / 2)
    return radius, width, separation, center_yz


def to_robot(points, origin_cad):
    return (R_CAD @ (np.asarray(points) - origin_cad).T).T


def mesh_to_robot(mesh, origin_cad):
    m = mesh.copy()
    t = np.eye(4)
    t[:3, :3] = R_CAD
    t[:3, 3] = -R_CAD @ origin_cad
    m.apply_transform(t)
    return m


def bbox(mesh):
    lo, hi = mesh.bounds
    return lo, hi, (lo + hi) / 2, hi - lo


def _cross2(a, b):
    return a[0] * b[1] - a[1] * b[0]


def convex_hull_2d(points):
    p = sorted(map(tuple, np.round(points, 4)))
    if len(p) < 3:
        return p
    def half(seq):
        out = []
        for q in seq:
            while len(out) >= 2 and _cross2(np.subtract(out[-1], out[-2]), np.subtract(q, out[-2])) <= 0:
                out.pop()
            out.append(q)
        return out
    lower, upper = half(p), half(reversed(p))
    return lower[:-1] + upper[:-1]


KEEP_FACES = 2000   # connected pieces this simple are kept untouched (e.g. the base hull, ~1.2k faces)


def _reduce(piece, target):
    """Decimate one connected piece; CAD pieces that stop decimating early (non-manifold
    detail) are replaced by their convex hull, which is enough for a visual."""
    out = piece.simplify_quadric_decimation(face_count=target, aggression=7)
    if len(out.faces) > 1.5 * target:
        out = piece.convex_hull
        if len(out.faces) > target:
            out = out.simplify_quadric_decimation(face_count=target, aggression=7)
    return out


def simplify(mesh, faces):
    """Reduce `mesh` to about `faces` triangles PIECE BY PIECE: decimating the merged mesh
    lets a few detailed parts (brackets, screws) eat the budget and collapse a simple
    large part (the base hull) to nothing."""
    if len(mesh.faces) <= faces:
        return mesh
    pieces = [p for p in mesh.split(only_watertight=False) if len(p.faces) >= 4]
    simple = [p for p in pieces if len(p.faces) <= KEEP_FACES]
    detailed = [p for p in pieces if len(p.faces) > KEEP_FACES]
    budget = max(faces - sum(len(p.faces) for p in simple), 200 * len(detailed))
    total = sum(len(p.faces) for p in detailed)
    reduced = [_reduce(p, max(200, int(budget * len(p.faces) / total))) for p in detailed]
    return trimesh.util.concatenate(simple + reduced)


def save_mesh(mesh, name, faces, offset, rotation=None):
    """Express `mesh` in a frame at `offset` (robot axes, optionally rotated by `rotation`),
    decimate, write binary STL."""
    m = mesh.copy()
    m.apply_translation(-np.asarray(offset))
    if rotation is not None:
        t = np.eye(4)
        t[:3, :3] = np.asarray(rotation).T
        m.apply_transform(t)
    m.merge_vertices()
    m = simplify(m, faces)
    path = os.path.join(PKG, 'meshes', 'v2', f'{name}.stl')
    m.export(path)
    return MESH_URI + f'{name}.stl', len(m.faces), os.path.getsize(path)


def r6(v):
    return [round(float(x), 6) for x in v]


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('export_dir', help='folder containing urdf/ and meshes/ of the Onshape export')
    args = ap.parse_args()
    cad = Export(os.path.expanduser(args.export_dir))
    os.makedirs(os.path.join(PKG, 'meshes', 'v2'), exist_ok=True)
    report = []

    # ---- wheels define base_footprint: floor point under the axle centre
    base_cad = cad.mesh(['part_1'])
    radius, width, separation, axle_yz = find_wheels(base_cad)
    origin = np.array([0.0, axle_yz[0], axle_yz[1] - radius])
    report.append(f'wheels: radius {radius:.4f}  width {width:.4f}  separation {separation:.4f}  '
                  f'axle at CAD y={axle_yz[0]:+.4f} z={axle_yz[1]:+.4f}')

    # ---- base hull (box collision) and base_link (= hull box centre)
    hull = mesh_to_robot(base_cad, origin)
    lo, hi, c, size = bbox(hull)
    base_link = np.array([c[0], 0.0, c[2]])
    caster_height = float(lo[2])
    report.append(f'base hull: length {size[0]:.4f} width {size[1]:.4f} height {size[2]:.4f}  '
                  f'centre x {c[0]:+.4f}  bottom {lo[2]:+.4f} (negative = below wheel contact!)')
    base_visual = mesh_to_robot(cad.mesh(GROUPS['base']), origin)
    base_mesh = save_mesh(base_visual, 'base', FACES['base'], base_link)

    # ---- torso: dorso_link at the bottom centre of the torso box (base_footprint frame)
    lo_t, hi_t, c_t, size_t = bbox(mesh_to_robot(cad.mesh([TORSO]), origin))
    dorso = np.array([c_t[0], c_t[1], lo_t[2]])

    # ---- Hokuyos: frame on the head axis, middle of the (narrow) head band; mounted upside down
    sensors = {}
    for key, name, yaw in (('hokuyo_ground', 'hokuyo_front', 0.0), ('hokuyo_back', 'hokuyo_back', np.pi)):
        m = mesh_to_robot(cad.mesh(GROUPS[name]), origin)
        lo_h, hi_h, c_h, _ = bbox(m)
        v = m.vertices
        zs = np.linspace(lo_h[2], hi_h[2], 40)
        half = [np.max(np.abs(v[np.abs(v[:, 2] - z) < 0.002][:, :2] - c_h[:2])) if np.any(np.abs(v[:, 2] - z) < 0.002) else 0
                for z in zs]
        head = [z for z, h in zip(zs, half) if 0 < h < 0.0215]   # head is narrower than the 50 mm body
        z_scan = float(np.mean(head)) if head else float(c_h[2])
        frame = np.array([c_h[0], c_h[1], z_scan])
        uri, nf, nb = save_mesh(m, name, FACES['hokuyo'], frame, rotation=rpy_to_matrix(np.pi, 0.0, yaw))
        report.append(f'{key}: {nf} faces, {nb / 1e3:.0f} kB')
        sensors[key] = {'xyz': r6(frame - base_link), 'rpy': r6([np.pi, 0.0, yaw]), 'mesh': uri}
        report.append(f'{key}: scan frame {frame.round(4)} (floor frame), {nf} faces')

    # ---- Sick: align the CAD box with the repo's Sick macro mesh (mount frame)
    sick_ref = trimesh.load(os.path.join(PKG, 'meshes', 'sensors', 'sick-lms1xx.stl'), force='mesh')
    lo_ref, _, c_ref, size_ref = bbox(sick_ref)
    lo_s, _, c_s, size_s = bbox(mesh_to_robot(cad.mesh([SICK]), origin))
    # same bottom and same xy centre (the repo mesh is a slightly different LMS1xx model)
    mount = np.array([c_s[0] - c_ref[0], c_s[1] - c_ref[1], lo_s[2] - lo_ref[2]])
    sensors['sick'] = {'xyz': r6(mount - base_link), 'rpy': [0.0, 0.0, 0.0]}
    report.append(f'sick: CAD box {size_s.round(4)} vs macro mesh {size_ref.round(4)} (aligned by bottom + centre)')

    # ---- IMU: not in the CAD -> same pose relative to base_link as v1 (TODO: measure)
    sensors['imu'] = {'xyz': r6([0.0, 0.06, size[2] / 2 - 0.05]), 'rpy': r6([np.pi, 0.0, -np.pi / 2]),
                      'todo': 'not in the CAD; v1 pose relative to base_link'}

    # ---- arm mount: bottom centre of the xArm base disc
    lo_a, _, c_a, _ = bbox(mesh_to_robot(cad.mesh([ARM_BASE]), origin))
    arm_mount = np.array([c_a[0], c_a[1], lo_a[2]])

    # ---- neck: recover the neutral pose (Femto level and forward) ---------------------
    femto_parts = [n for n in cad.links if n.startswith('femto_bolt')]
    pan_p, _ = cad.joint_world(PAN_JOINT)
    tilt_pts = [cad.joint_world(j)[0] for j in TILT_JOINTS]
    tilt_p = np.mean(tilt_pts, axis=0)
    housing = cad.world(FEMTO_HOUSING)[:3, :3]      # x = camera width axis, z = optical axis
    width_axis, optical_axis = housing[:, 0], housing[:, 2]
    # un-pan: width axis must become lateral (CAD x); keep the camera in front of the pan axis
    theta = -np.arctan2(width_axis[1], width_axis[0])
    femto_c = cad.mesh(femto_parts).vertices.mean(0)
    for t in (theta, theta + np.pi):
        if (rot([0, 0, 1], t) @ (femto_c - pan_p))[1] < 0:   # in front = CAD -y
            theta = t
            break
    r_pan = rot([0, 0, 1], theta)
    tilt_p0 = pan_p + r_pan @ (tilt_p - pan_p)
    tilt_axis0 = r_pan @ width_axis
    optical0 = r_pan @ optical_axis
    if optical0[1] > 0:                              # must look forward (CAD -y)
        optical0 = -optical0
    # un-tilt: rotate about the (now lateral) tilt axis until the optical axis is level
    level = np.array([optical0[0], optical0[1], 0.0])
    level /= np.linalg.norm(level)
    phi = np.arctan2(np.dot(np.cross(optical0, level), tilt_axis0), np.dot(optical0, level))
    r_tilt = rot(tilt_axis0, phi)
    elevation = np.degrees(np.arcsin(optical0[2]))
    report.append(f'neck: exported pan {np.degrees(-theta):+.1f} deg; Femto looked '
                  f'{"up" if elevation > 0 else "down"} {abs(elevation):.1f} deg -> levelled')

    def neutral(mesh, tilt):
        m = mesh.copy()
        m.vertices = pan_p + (r_pan @ (m.vertices - pan_p).T).T
        if tilt:
            m.vertices = tilt_p0 + (r_tilt @ (m.vertices - tilt_p0).T).T
        return m

    pan_r = to_robot(pan_p, origin)
    tilt_r = to_robot(tilt_p0, origin)
    neck_base = mesh_to_robot(cad.mesh(GROUPS['neck_base']), origin)
    neck_pan = mesh_to_robot(neutral(cad.mesh(GROUPS['neck_pan']), False), origin)
    neck_tilt = mesh_to_robot(neutral(cad.mesh(GROUPS['neck_tilt'] + femto_parts), True), origin)
    femto_r = mesh_to_robot(neutral(cad.mesh(femto_parts), True), origin)
    _, _, femto_center, femto_size = bbox(femto_r)
    neck = {
        'base': {'mesh': save_mesh(neck_base, 'neck_base', FACES['neck_base'], dorso)[0]},
        'pan': {'xyz': r6(pan_r - dorso),
                'mesh': save_mesh(neck_pan, 'neck_pan', FACES['neck_pan'], pan_r)[0]},
        'tilt': {'xyz': r6(tilt_r - pan_r),
                 'mesh': save_mesh(neck_tilt, 'neck_tilt', FACES['neck_tilt'], tilt_r)[0]},
        'camera': {'xyz': r6(femto_center - tilt_r)},
    }
    report.append(f'femto (neutral): centre {femto_center.round(4)} size {femto_size.round(4)} (expect ~0.04 x 0.115 x 0.065)')

    # ---- footprint: convex hull of the base, torso and sensors (floor projection)
    corners = []
    for m in (hull, mesh_to_robot(cad.mesh([TORSO]), origin), mesh_to_robot(cad.mesh([SICK]), origin),
              mesh_to_robot(cad.mesh(GROUPS['hokuyo_front']), origin), mesh_to_robot(cad.mesh(GROUPS['hokuyo_back']), origin)):
        lo_m, hi_m = m.bounds
        corners += [(x, y) for x in (lo_m[0], hi_m[0]) for y in (lo_m[1], hi_m[1])]
    footprint = convex_hull_2d(np.array(corners))
    report.append(f'footprint: {len(footprint)} points, x [{min(p[0] for p in footprint):+.3f}, {max(p[0] for p in footprint):+.3f}] '
                  f'y [{min(p[1] for p in footprint):+.3f}, {max(p[1] for p in footprint):+.3f}]')

    # ---- write config/robot/v2.yaml (keep the hand-edited driver section)
    out = os.path.join(PKG, 'config', 'robot', 'v2.yaml')
    driver = {'device': '/dev/ttySHARK', 'max_velocity': 1.0}
    if os.path.isfile(out):
        with open(out) as f:
            driver = (yaml.safe_load(f) or {}).get('driver', driver)
    data = {
        'base': {'length': round(float(size[0]), 6), 'width': round(float(size[1]), 6),
                 'height': round(float(size[2]), 6), 'center_x': round(float(base_link[0]), 6),
                 'visual_mesh': base_mesh[0]},
        'wheel': {'radius': round(radius, 6), 'width': round(width, 6),
                  'separation': round(separation, 6), 'x_offset': 0.0},
        'caster_height': round(caster_height, 6),
        'driver': driver,
        'footprint': str([[round(float(x), 3), round(float(y), 3)] for x, y in footprint]),
        'body': {
            'dorso': {'length': round(float(size_t[0]), 6), 'width': round(float(size_t[1]), 6),
                      'height': round(float(size_t[2]), 6), 'xyz': r6(dorso - base_link)},
            'arm_mount': {'xyz': r6(arm_mount - base_link), 'rpy': [0.0, 0.0, 0.0]},
        },
        'sensors': sensors,
        'neck': neck,
    }
    header = ('# BORIS v2 robot geometry. GENERATED by tools/v2_from_onshape.py from the Onshape\n'
              '# URDF export - re-run the tool instead of editing by hand (only `driver` is kept).\n'
              '# Frames: base_footprint = floor under the wheel axle centre, x forward, y left.\n'
              '# All xyz are relative to base_link unless stated (neck: dorso_link / parent link).\n'
              '# wheel.radius / wheel.separation are CAD values: calibrate odometry (docs/calibration.md).\n')
    with open(out, 'w') as f:
        f.write(header)
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=None, width=120)

    sizes = sum(os.path.getsize(os.path.join(PKG, 'meshes', 'v2', n)) for n in os.listdir(os.path.join(PKG, 'meshes', 'v2')))
    report.append(f'meshes/v2: {len(os.listdir(os.path.join(PKG, "meshes", "v2")))} files, {sizes / 1e6:.2f} MB')
    print('\n'.join(report))
    print(f'wrote {os.path.relpath(out, PKG)}')


if __name__ == '__main__':
    main()
