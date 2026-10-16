"""v1.3.3 CAD extension contract checks (source structure only; not a Gazebo runtime test)."""
from pathlib import Path
from xml.etree import ElementTree as ET
import unittest

DESC = Path(__file__).resolve().parents[1]
SRC = DESC.parent
X = {'x':'http://www.ros.org/wiki/xacro'}


class TemporaryGripper(unittest.TestCase):
    def setUp(self):
        self.doc=ET.parse(DESC/'urdf/arm/arm_cad.macro.xacro').getroot()
        self.arm=self.doc.find('x:macro',X)
        self.gz=ET.parse(DESC/'urdf/arm/arm_cad.gazebo.xacro').getroot()

    def test_cad_original_joints_still_present(self):
        self.assertEqual([j.get('name') for j in self.arm.findall('joint')][:5],
                         ['${prefix}base_yaw_joint','${prefix}base_mount_fixed',
                          '${prefix}joint0','${prefix}joint1','${prefix}joint2'])

    def test_new_actuated_joints_do_not_use_fixed_motor_parent(self):
        j3=self.arm.find("joint[@name='${prefix}joint3']")
        self.assertEqual(j3.get('type'),'revolute')
        self.assertEqual(j3.find('parent').get('link'),'${prefix}link2')
        self.assertEqual(j3.find('child').get('link'),'${prefix}link3')
        self.assertEqual(j3.find('origin').get('xyz'),'-0.240 0 0')
        gf=self.arm.find("joint[@name='${prefix}gripper_finger_joint']")
        self.assertEqual(gf.get('type'),'prismatic')
        self.assertEqual(gf.find('parent').get('link'),'${prefix}link3')
        self.assertEqual(gf.find('child').get('link'),'${prefix}gripper_finger_link')
        self.assertEqual(gf.find('axis').get('xyz'),'0 1 0')
        self.assertIsNone(self.arm.find("link[@name='${prefix}base_motor_stator_link']"))

    def test_new_dynamic_links_have_valid_positive_inertials(self):
        for name in ('link3','gripper_finger_link'):
            link=self.arm.find(f"link[@name='${{prefix}}{name}']")
            inertial=link.find('inertial')
            self.assertGreater(float(inertial.find('mass').get('value')), 0)
            inertia=inertial.find('inertia')
            for axis in ('ixx','iyy','izz'):
                self.assertGreater(float(inertia.get(axis)),0)
            self.assertIsNotNone(link.find('visual'))
            self.assertIsNotNone(link.find('collision'))

    def test_gripper_has_valid_open_close_range(self):
        gr=self.arm.find("joint[@name='${prefix}gripper_finger_joint']")
        limit=gr.find('limit')
        self.assertEqual(float(limit.get('lower')), 0)
        self.assertGreaterEqual(float(limit.get('upper')), .04)
        self.assertLessEqual(float(limit.get('upper')), .05)
        tcp=self.arm.find("joint[@name='${prefix}tool0_fixed']")
        self.assertEqual(tcp.find('parent').get('link'), '${prefix}link3')
        self.assertEqual(tcp.find('child').get('link'), '${prefix}tool0')

    def test_no_changes_to_board_squares_and_markers(self):
        board=ET.parse(DESC/'urdf/board/board.macro.xacro').getroot()
        self.assertIsNotNone(board.find("x:macro[@name='chess_board']",X))
        self.assertIn('square_dark',(DESC/'urdf/common/materials.xacro').read_text())

    def test_gripper_velocity_controller_is_separate(self):
        m=self.gz.find("x:macro[@name='cad_hold_gripper_joint']",X)
        self.assertIsNotNone(m)
        self.assertEqual(m.find('gazebo/plugin/initial_position').text,'0.0')
        cmd=self.gz.find("x:macro[@name='cad_chess_arm_gz']",X)
        self.assertEqual(len(cmd.findall('x:cad_hold_gripper_joint',X)),1)


if __name__=='__main__': unittest.main()
