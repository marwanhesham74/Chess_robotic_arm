"""Portable checks for the candidate CAD Xacro/ROS launch integration.
These tests intentionally do NOT claim to execute native ROS Xacro or Gazebo.
"""
import re
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

HERE=Path(__file__).resolve().parent
SRC=HERE.parents[1]
DESC=HERE.parent
NS={'x':'http://www.ros.org/wiki/xacro'}


class CADIntegrationTests(unittest.TestCase):
    def test_all_xml_sources_parse(self):
        for p in [*SRC.rglob('*.xacro'), *SRC.rglob('package.xml'), *SRC.rglob('*.sdf')]:
            with self.subTest(path=str(p.relative_to(SRC))):
                ET.parse(p)

    def test_cad_is_canonical_top_entrypoint(self):
        path=DESC/'urdf/dual_chess.urdf.xacro'
        tree=ET.parse(path).getroot()
        self.assertEqual(tree.get('name'), 'dual_chess')
        includes=[n.get('filename') for n in tree.findall('x:include',NS)]
        self.assertTrue(any(x.endswith('/arm_cad.macro.xacro') for x in includes))
        self.assertTrue(any(x.endswith('/arm_cad.gazebo.xacro') for x in includes))
        self.assertFalse(any(x.endswith('/arm.macro.xacro') for x in includes))
        self.assertEqual(len(tree.findall('.//x:cad_chess_arm',NS)),2)
        self.assertEqual({x.get('prefix') for x in tree.findall('.//x:cad_chess_arm',NS)}, {'robot1_','robot2_'})
        for name in ['sim_gazebo','robot1_enabled','robot2_enabled','use_meshes']:
            self.assertIsNotNone(tree.find(f"x:arg[@name='{name}']",NS))

    def test_three_actuated_joints_and_two_reference_joints_per_arm(self):
        root=ET.parse(DESC/'urdf/arm/arm_cad.macro.xacro').getroot()
        arm=root.find("x:macro[@name='cad_chess_arm']",NS)
        self.assertIsNotNone(arm)
        joints=arm.findall('joint')
        self.assertEqual([(j.get('name'),j.get('type')) for j in joints], [
            ('${prefix}base_yaw_joint','continuous'),('${prefix}base_mount_fixed','fixed'),
            ('${prefix}joint0','fixed'),('${prefix}joint1','continuous'),('${prefix}joint2','continuous')])
        links={x.get('name') for x in arm.findall('link')}
        self.assertEqual(links, {'${prefix}base_yaw_link','${prefix}base_link','${prefix}link0',
                                 '${prefix}link1','${prefix}link2'})
        for joint in joints:
            self.assertIn(joint.find('child').get('link'),links)
            parent=joint.find('parent').get('link')
            self.assertTrue(parent in links or parent=='${parent}')
        for frame in ['${prefix}base_link','${prefix}link0']:
            node=next(x for x in arm.findall('link') if x.get('name')==frame)
            self.assertEqual(len(node.findall('inertial')+node.findall('visual')+node.findall('collision')),0)

    def test_cad_stl_and_nonduplicated_mass(self):
        root=ET.parse(DESC/'urdf/arm/arm_cad.macro.xacro').getroot()
        macro=root.find("x:macro[@name='cad_chess_arm']",NS)
        meshes=[n.get('filename') for n in macro.findall('.//mesh')]
        expected={f'package://dual_chess_description/meshes/robot_arm/link{x}.STL' for x in (0,1,2)}
        self.assertEqual(set(meshes),expected)
        self.assertEqual(len(meshes),3)
        for name in meshes:
            rel=name.split('package://dual_chess_description/')[1]
            self.assertGreater((DESC/rel).stat().st_size,1000)
        self.assertFalse((DESC/'meshes/robot_arm/base_link.STL').exists())
        masses=[float(x.find('mass').get('value')) for x in macro.findall('.//inertial')]
        self.assertEqual(len(masses),3)
        self.assertAlmostEqual(sum(masses), 0.870562202400842, places=9)
        for inertia in macro.findall('.//inertia'):
            d={key:float(inertia.get(key)) for key in ('ixx','iyy','izz','ixy','ixz','iyz')}
            m1=d['ixx']; m2=d['ixx']*d['iyy']-d['ixy']**2
            m3=d['ixx']*(d['iyy']*d['izz']-d['iyz']**2)-d['ixy']*(d['ixy']*d['izz']-d['iyz']*d['ixz'])+d['ixz']*(d['ixy']*d['iyz']-d['iyy']*d['ixz'])
            self.assertTrue(m1>0 and m2>0 and m3>0)

    def test_v131_home_targets_match_verified_cad_controller(self):
        """Regression: HOME targets change only position-controller commands."""
        gz = ET.parse(DESC/'urdf/arm/arm_cad.gazebo.xacro').getroot()
        props = {n.get('name'): n.get('value') for n in gz.findall('x:property', NS)}
        self.assertEqual(props['cad_home_base_yaw'], '${pi/2}')
        self.assertEqual(props['cad_home_shoulder'], '1.15')
        self.assertEqual(props['cad_home_elbow'], '0.35')
        self.assertEqual(props['cad_sim_velocity_limit'], '0.4')
        hold = gz.find("x:macro[@name='cad_hold_joint']", NS)
        self.assertEqual(hold.get('params'), 'joint topic home_position')
        plugin = hold.find('gazebo/plugin')
        self.assertEqual(plugin.findtext('initial_position'), '${home_position}')
        self.assertEqual(plugin.findtext('use_velocity_commands'), 'true')
        self.assertEqual(plugin.findtext('cmd_max'), '${cad_sim_velocity_limit}')
        self.assertEqual(plugin.findtext('cmd_min'), '-${cad_sim_velocity_limit}')
        arm = gz.find("x:macro[@name='cad_chess_arm_gz']", NS)
        commands = arm.findall('x:cad_hold_joint', NS)
        self.assertEqual(len(commands), 3)
        self.assertEqual([(n.get('joint'), n.get('home_position')) for n in commands], [
            ('${prefix}base_yaw_joint', '${cad_home_base_yaw}'),
            ('${prefix}joint1', '${cad_home_shoulder}'),
            ('${prefix}joint2', '${cad_home_elbow}')])
        # IMPORTANT: no home assumption should alter the original CAD joint origins.
        cad = (DESC/'urdf/arm/arm_cad.macro.xacro').read_text()
        self.assertNotIn('cad_home_', cad)

    def test_matching_gazebo_plugins_and_six_bridge_channels(self):
        gz=ET.parse(DESC/'urdf/arm/arm_cad.gazebo.xacro').getroot()
        macro=gz.find("x:macro[@name='cad_chess_arm_gz']",NS)
        self.assertEqual(len(macro.findall('x:cad_hold_joint',NS)),3)
        names=[n.get('joint') for n in macro.findall('x:cad_hold_joint',NS)]
        self.assertEqual(names,['${prefix}base_yaw_joint','${prefix}joint1','${prefix}joint2'])
        bridge=(SRC/'dual_chess_gazebo/config/bridge.yaml').read_text()
        matches=re.findall(r'ros_topic_name: "([^"]+)/cmd_pos"',bridge)
        expected={f'/{robot}/{joint}' for robot in ('robot1','robot2')
                  for joint in ('base_yaw_joint','joint1','joint2')}
        self.assertEqual(set(matches),expected)
        self.assertEqual(len(matches),6)
        self.assertIn('/world/chess_world/model/dual_chess/joint_state',bridge)
        self.assertIn('/clock',bridge)

    def test_normal_ros_launch_and_chess_logic_retained(self):
        launch=(SRC/'dual_chess_bringup/launch/simulation.launch.py').read_text()
        self.assertIn('gazebo.launch.py',launch)
        self.assertIn('chess_brain.launch.py',launch)
        self.assertIn('chess_auto_coordinator',launch)
        self.assertIn("DeclareLaunchArgument('auto_play_enabled', default_value='false'",launch)
        gzlaunch=(SRC/'dual_chess_gazebo/launch/gazebo.launch.py').read_text()
        self.assertIn("'dual_chess.urdf.xacro'",gzlaunch)
        self.assertIn("'config', 'bridge.yaml'",gzlaunch)
        self.assertIn("'robot_description'",gzlaunch)


if __name__=='__main__':
    unittest.main()
