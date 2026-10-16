"""Static controller regression checks (NOT Gazebo runtime proof)."""
from pathlib import Path
from xml.etree import ElementTree as ET
import unittest

DESC = Path(__file__).resolve().parents[1]
NS = {'x':'http://www.ros.org/wiki/xacro'}

class GripperControllerRegression(unittest.TestCase):
    def setUp(self):
        gz = ET.parse(DESC/'urdf/arm/arm_cad.gazebo.xacro').getroot()
        self.props = {e.get('name'):e.get('value') for e in gz.findall('x:property', NS)}
        self.main = gz.find("x:macro[@name='cad_hold_joint']", NS).find('gazebo/plugin')
        self.grip = gz.find("x:macro[@name='cad_hold_gripper_joint']", NS).find('gazebo/plugin')
        self.arm = ET.parse(DESC/'urdf/arm/arm_cad.macro.xacro').getroot().find("x:macro[@name='cad_chess_arm']", NS)

    def test_arm_position_controllers_untouched(self):
        self.assertEqual(self.main.findtext('use_velocity_commands'), 'true')
        self.assertEqual(self.main.findtext('cmd_max'), '${cad_sim_velocity_limit}')
        self.assertEqual(self.main.findtext('initial_position'), '${home_position}')

    def test_prismatic_gripper_uses_force_mode_with_bounded_integral(self):
        self.assertEqual(self.grip.findtext('use_velocity_commands'), 'false')
        self.assertEqual(self.grip.findtext('i_gain'), '${cad_sim_gripper_pid_i}')
        self.assertEqual(self.grip.findtext('i_max'), '${cad_sim_gripper_integral_clamp}')
        self.assertEqual(self.grip.findtext('i_min'), '-${cad_sim_gripper_integral_clamp}')
        ki=float(self.props['cad_sim_gripper_pid_i'])
        limit=float(self.props['cad_sim_gripper_integral_clamp'])
        self.assertGreater(ki,0)
        self.assertLessEqual(limit, float(self.props['cad_sim_gripper_force_limit']))
        self.assertGreater(limit,0)
        self.assertEqual(self.grip.findtext('initial_position'), '0.0')
        for k in ('cad_sim_gripper_pid_p','cad_sim_gripper_pid_d','cad_sim_gripper_force_limit'):
            self.assertGreater(float(self.props[k]),0)
        self.assertEqual(self.grip.findtext('p_gain'), '${cad_sim_gripper_pid_p}')
        self.assertEqual(self.grip.findtext('d_gain'), '${cad_sim_gripper_pid_d}')
        self.assertEqual(self.grip.findtext('cmd_max'), '${cad_sim_gripper_force_limit}')
        self.assertEqual(self.grip.findtext('cmd_min'), '-${cad_sim_gripper_force_limit}')

    def test_moving_finger_collisions_clear_of_palm_along_full_travel(self):
        parent = self.arm.find("link[@name='${prefix}link3']")
        palm = parent.find("collision[@name='gripper_palm_collision']")
        mount = self.arm.find("joint[@name='${prefix}gripper_finger_joint']")
        slide = self.arm.find("link[@name='${prefix}gripper_finger_link']/collision[@name='rounded_moving_finger_collision']")
        box = lambda el: [float(v) for v in el.find('geometry/box').get('size').split()]
        center = lambda el: [float(v) for v in el.find('origin').get('xyz').split()]
        pc,ps=center(palm),box(palm)
        jx=center(mount)[0]
        fc,fs=center(slide),box(slide)
        # Distal moving collider remains outside the palm along X, for all Y positions.
        self.assertLess(jx+fc[0]+fs[0]/2,pc[0]-ps[0]/2)
        fixed=parent.find("collision[@name='fixed_finger_collision']")
        xc,xs=center(fixed),box(fixed)
        self.assertLess(xc[0]+xs[0]/2,pc[0]-ps[0]/2)
        self.assertEqual(mount.find('axis').get('xyz'),'0 1 0')
        limit=mount.find('limit')
        self.assertEqual((float(limit.get('lower')),float(limit.get('upper'))),(0.0,.045))

if __name__ == '__main__': unittest.main()
