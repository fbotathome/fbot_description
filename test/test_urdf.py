"""Model checks for boris.urdf.xacro (run with `colcon test --packages-select fbot_description`).

For every combination of base_version / use_neck / use_sick / use_arm_mount it checks that:
  - xacro expands and the result is a single tree rooted at base_footprint
  - every ros2_control joint exists in the URDF (and vice versa for the wheels)
  - the wheel joints sit at +-separation/2 and at height wheel radius, as in config/base/<v>.yaml
  - every mesh referenced with package://fbot_description/ exists in the installed package
"""
import itertools
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET

import pytest
import xacro
import yaml
from ament_index_python.packages import get_package_share_directory

SHARE = get_package_share_directory('fbot_description')
XACRO = os.path.join(SHARE, 'urdf', 'boris.urdf.xacro')
VERSIONS = sorted(f[:-5] for f in os.listdir(os.path.join(SHARE, 'config', 'base')) if f.endswith('.yaml'))
BOOL = ('true', 'false')
CASES = list(itertools.product(VERSIONS, BOOL, BOOL, BOOL))


def expand(base_version, use_neck, use_sick, use_arm_mount):
    doc = xacro.process_file(XACRO, mappings={
        'base_version': base_version, 'use_neck': use_neck,
        'use_sick': use_sick, 'use_arm_mount': use_arm_mount,
    })
    return doc.toxml()


@pytest.mark.parametrize('base_version,use_neck,use_sick,use_arm_mount', CASES)
def test_model(base_version, use_neck, use_sick, use_arm_mount, tmp_path):
    urdf = expand(base_version, use_neck, use_sick, use_arm_mount)
    root = ET.fromstring(urdf)

    links = {l.get('name') for l in root.findall('link')}
    joints = {j.get('name'): j for j in root.findall('joint')}
    children = {j.find('child').get('link') for j in joints.values()}
    for j in joints.values():
        assert j.find('parent').get('link') in links, j.get('name')
        assert j.find('child').get('link') in links, j.get('name')
    assert links - children == {'base_footprint'}, 'model must be a single tree rooted at base_footprint'

    # optional parts follow their flags
    assert ('camera_link' in links) == (use_neck == 'true')
    assert ('sick_mount_link' in links) == (use_sick == 'true')
    assert ('arm_mount_link' in links) == (use_arm_mount == 'true')

    # ros2_control <-> URDF joints
    rc_joints = {j.get('name') for rc in root.findall('ros2_control') for j in rc.findall('joint')}
    assert rc_joints == {'left_wheel_joint', 'right_wheel_joint'}
    assert rc_joints <= set(joints), 'ros2_control joints must exist in the URDF'

    # wheel geometry == config/base/<version>.yaml
    with open(os.path.join(SHARE, 'config', 'base', f'{base_version}.yaml')) as f:
        cfg = yaml.safe_load(f)
    for name, sign in (('left_wheel_joint', 1), ('right_wheel_joint', -1)):
        x, y, z = (float(v) for v in joints[name].find('origin').get('xyz').split())
        assert y == pytest.approx(sign * cfg['wheel']['separation'] / 2)
    base_z = float(joints['base_link_joint'].find('origin').get('xyz').split()[2])
    assert base_z + z == pytest.approx(cfg['wheel']['radius']), 'wheel axle must be at wheel radius height'

    # meshes exist
    for mesh in root.iter('mesh'):
        uri = mesh.get('filename')
        if uri.startswith('package://fbot_description/'):
            assert os.path.isfile(os.path.join(SHARE, uri[len('package://fbot_description/'):])), uri

    # urdfdom parser, when available
    if shutil.which('check_urdf'):
        path = tmp_path / 'boris.urdf'
        path.write_text(urdf)
        subprocess.run(['check_urdf', str(path)], check=True, capture_output=True)
