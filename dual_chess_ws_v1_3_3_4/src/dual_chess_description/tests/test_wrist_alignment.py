"""v1.3.3.2 parked wrist geometry & mirror-clearance regression (offline).

Tests source mesh, chain pose, source preservation and wrist/gripper clearance
at Home only. This is NOT collision planning or native Gazebo validation.
"""
import math
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ARM = Path(__file__).resolve().parents[1] / 'urdf/arm/arm_cad.macro.xacro'


def rot_x(a):
    return [[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]]


def rot_y(a):
    return [[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]]


def rot_z(a):
    return [[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]]


def mmul(a, b):
    return [[sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def apply(r, v):
    return [sum(r[i][j]*v[j] for j in range(3)) for i in range(3)]


def compose(state, pos, rpy):
    xyz, r = state
    shift = apply(r, pos)
    local_rot = mmul(mmul(rot_z(rpy[2]), rot_y(rpy[1])), rot_x(rpy[0]))
    return [xyz[i]+shift[i] for i in range(3)], mmul(r, local_rot)


class WristAlignmentTests(unittest.TestCase):
    def test_mount_has_parked_wrist_reference_and_original_cad_parent(self):
        root = ET.parse(ARM).getroot()
        wrist = root.find('.//joint[@name="${prefix}joint3"]')
        self.assertEqual(wrist.find('parent').get('link'), '${prefix}link2')
        self.assertEqual(wrist.find('origin').get('xyz'), '-0.240 0 0')
        self.assertEqual(wrist.find('origin').get('rpy'), '0 0 ${pi/2 + 1.0}')
        self.assertEqual(wrist.find('axis').get('xyz'), '0 0 1')

    def _arm_home(self, y, yaw):
        state = ([0, 0, 0], [[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        state = compose(state, [0, y, 0], [0, 0, yaw])
        state = compose(state, [0, 0, 0], [0, 0, math.pi/2])
        state = compose(state, [.185810249819478, .243972086655367, .126612878977615], [0, 0, 0])
        state = compose(state, [-.185810249819478, -.243972086655367, -.126612878977615], [math.pi/2, 0, .0189216137804055])
        state = compose(state, [0, .06, 0], [math.pi/2, 1.39871137927, -math.pi/2])
        state = compose(state, [0, 0, 0], [0, 0, 1.15])
        state = compose(state, [-.2, 0, 0], [-math.pi, 0, -.0823720646867807])
        state = compose(state, [0, 0, 0], [0, 0, .35])
        wrist = compose(state, [-.240, 0, 0], [0, 0, math.pi/2 + 1.0])
        tip = compose(wrist, [-.240, 0, 0], [0, 0, 0])[0]
        return wrist[0], tip

    def test_separate_parked_wrist_and_gripper_tips(self):
        wrist_blue, tip_blue = self._arm_home(-.30, math.pi/2)
        wrist_orange, tip_orange = self._arm_home(+.30, -math.pi/2)
        # Measured board play area Y[-.175,+.175] and surface Z=0.01 m.
        for start, tip, side in [(wrist_blue,tip_blue,-1),(wrist_orange,tip_orange,+1)]:
            self.assertGreater(side*start[1], .09)
            self.assertGreater(side*tip[1], .09)  # no crossing board centerline
            self.assertGreater(tip[2], .15)      # visual fingertips above CAD board
            self.assertLess(tip[2], .35)
        self.assertGreater(math.dist(tip_blue,tip_orange), .20)

    def test_visual_meshes_exist_and_are_rounded(self):
        source = ARM.read_text()
        folder = ARM.parents[2] / 'meshes/robot_arm'
        for mesh in ('temporary_wrist.stl','temporary_gripper_fixed.stl','temporary_gripper_moving.stl'):
            self.assertIn(mesh, source)
            self.assertTrue((folder/mesh).is_file())
            self.assertGreater((folder/mesh).stat().st_size, 5000)
        self.assertIn('gripper_dark',source)
        self.assertIn('${material}',source)

if __name__ == '__main__':
    unittest.main()
