"""Portable v1.3.2 board-CAD regression tests: no ROS, numpy, or trimesh needed.
Native Xacro, URDF, Gazebo, RViz, collision, and mesh rendering still need Jazzy.
"""
from pathlib import Path
import struct
import unittest
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
DESC = HERE.parent
SRC = DESC.parent
X = '{http://www.ros.org/wiki/xacro}'
BOARD = DESC/'meshes/chess_board/Board_1_original.STL'
PARAMS = DESC/'urdf/board/board_params_cad.xacro'


def numeric_board_properties():
    root = ET.parse(PARAMS).getroot()
    raw = {p.attrib['name']: p.attrib['value'] for p in root.findall(X+'property')}
    env = {}
    for key, v in raw.items():
        if v.startswith('${') and v.endswith('}'):
            env[key] = eval(v[2:-1], {'__builtins__': {}}, env)
        else:
            env[key] = float(v)
    return env


def stl_bounds():
    b = BOARD.read_bytes()
    count = struct.unpack_from('<I', b, 80)[0]
    if len(b) != 84+50*count:
        raise ValueError('invalid binary STL length')
    low = [float('inf')]*3; high=[float('-inf')]*3
    for i in range(count):
        # skip normal vector, read 3 vertices; no numpy dependency
        xyz = struct.unpack_from('<9f', b, 84+i*50+12)
        for j in range(3):
            for k in (0,3,6):
                low[j] = min(low[j],xyz[k+j])
                high[j] = max(high[j],xyz[k+j])
    return count,low,high


class CADBoardTests(unittest.TestCase):
    def test_mesh_is_original_and_binary(self):
        self.assertTrue(BOARD.exists())
        self.assertGreater(BOARD.stat().st_size, 100_000)
        n, lo, hi = stl_bounds()
        self.assertEqual(n, 4612)
        for a,b in zip(lo,[0,0,0]):
            self.assertAlmostEqual(a,b,delta=1e-4)
        for a,b in zip(hi,[400,20.18920517,400]):
            self.assertAlmostEqual(a,b,delta=1e-4)

    def test_dimensions_and_real_square_pitch(self):
        p = numeric_board_properties()
        self.assertAlmostEqual(p['board_size'], .4)
        self.assertAlmostEqual(p['board_play_size'], .35)
        self.assertAlmostEqual(p['board_square'], .04375)
        self.assertAlmostEqual(p['board_rim_width'], .025)
        self.assertAlmostEqual(p['board_thickness'], .02018920517, places=8)
        self.assertAlmostEqual(p['board_play_surface_height'], .01)
        self.assertAlmostEqual(p['robot_base_offset'], .30)
        self.assertFalse((DESC/'urdf/board/board_params_placeholder.xacro').exists())

    def test_mesh_scale_and_frame_relationships(self):
        root=ET.parse(DESC/'urdf/board/board.macro.xacro').getroot()
        macro=root.find(f'{X}macro[@name="chess_board"]')
        self.assertIsNotNone(macro)
        vis=macro.find('link[@name="board_link"]/visual')
        self.assertEqual(vis.find('geometry/mesh').get('filename'),
                         'package://dual_chess_description/meshes/chess_board/Board_1_original.STL')
        self.assertEqual(vis.find('geometry/mesh').get('scale'),'0.001 0.001 0.001')
        self.assertEqual(vis.find('origin').get('rpy'),'${pi/2} 0 0')
        self.assertEqual(vis.find('origin').get('xyz'),
                         '${-board_size/2} ${board_size/2} ${-board_thickness/2}')
        j=macro.find('joint[@name="board_joint"]')
        self.assertEqual(j.find('origin').get('xyz'), '0 0 ${board_thickness/2}')
        surf=macro.find('joint[@name="board_surface_joint"]')
        self.assertEqual(surf.find('origin').get('xyz'),
                         '0 0 ${board_play_surface_height-board_thickness/2}')
        for corner,sign in [('a1','-'),('h8','')]:
            joint=macro.find(f'joint[@name="board_{corner}_joint"]')
            coord=('-3.5*board_square' if corner=='a1' else '3.5*board_square')
            self.assertEqual(joint.find('origin').get('xyz'), f'${{{coord}}} ${{{coord}}} 0')

    def test_transformed_bounds_playing_surface_and_square_centres(self):
        p=numeric_board_properties(); _,low,high=stl_bounds()
        # Rx(+90 deg), then xy-centering; this reproduces the Xacro transform.
        transformed=[]
        for x in (low[0],high[0]):
            for y in (low[1],high[1]):
                for z in (low[2],high[2]):
                    transformed.append((.001*x-p['board_size']/2,
                                        p['board_size']/2-.001*z,
                                        .001*y))
        for i,expected_lo,expected_hi in [(0,-.2,.2),(1,-.2,.2),(2,0,p['board_thickness'])]:
            self.assertAlmostEqual(min(a[i] for a in transformed), expected_lo, places=7)
            self.assertAlmostEqual(max(a[i] for a in transformed), expected_hi, places=7)
        self.assertAlmostEqual(p['board_play_surface_height'],.010)
        # Physical grid spans [25,375] mm from either mesh edge.
        self.assertAlmostEqual(3.5*p['board_square'],.153125)
        self.assertAlmostEqual(.2-(25+.5*43.75)*.001,.153125)

    def test_preserves_previous_arm_home_and_interface(self):
        top=(DESC/'urdf/dual_chess.urdf.xacro').read_text()
        self.assertIn('arm_cad.gazebo.xacro',top)
        self.assertIn('chess_board parent="world"',top)
        gz=(DESC/'urdf/arm/arm_cad.gazebo.xacro').read_text()
        for snippet in ('name="cad_home_base_yaw" value="${pi/2}"',
                        'name="cad_home_shoulder" value="1.15"',
                        'name="cad_home_elbow" value="0.35"'):
            self.assertIn(snippet, gz)
        bridge=(SRC/'dual_chess_gazebo/config/bridge.yaml').read_text()
        import re
        self.assertEqual(len(re.findall(r'ros_topic_name: \"[^\"]+/cmd_pos\"', bridge)), 10)
        launch=(SRC/'dual_chess_bringup/launch/simulation.launch.py').read_text()
        self.assertIn('chess_brain.launch.py',launch)
        self.assertIn('chess_auto_coordinator',launch)

    def test_checkerboard_overlay_has_64_squares_and_materials(self):
        root = ET.parse(DESC/'urdf/board/board.macro.xacro').getroot()
        macro = root.find(f'{X}macro[@name="chess_board"]')
        sq_links = [l for l in macro.findall('link') if l.get('name','').startswith('board_square_')]
        sq_joints = [j for j in macro.findall('joint') if j.get('name','').startswith('board_square_')]
        self.assertEqual(len(sq_links), 64)
        self.assertEqual(len(sq_joints), 64)
        self.assertEqual(len(set(l.get('name') for l in sq_links)), 64)
        self.assertEqual(len(set(j.get('name') for j in sq_joints)), 64)
        self.assertEqual({l.find('visual/material').get('name') for l in sq_links},
                         {'square_light','square_dark'})
        for j in sq_joints:
            self.assertEqual(j.get('type'), 'fixed')
            self.assertEqual(j.find('parent').get('link'), 'board_surface')
            name = j.get('name')[len('board_square_'):-len('_joint')]
            self.assertEqual(j.find('child').get('link'),f'board_square_{name}')
        a1 = macro.find('link[@name="board_square_a1"]')
        h1 = macro.find('link[@name="board_square_h1"]')
        h8 = macro.find('link[@name="board_square_h8"]')
        self.assertEqual(a1.find('visual/material').get('name'), 'square_dark')
        self.assertEqual(h1.find('visual/material').get('name'), 'square_light')
        self.assertEqual(h8.find('visual/material').get('name'), 'square_dark')
        self.assertEqual(len(macro.find('link[@name="board_link"]').findall('visual')),1)

    def test_urdf_sources_xml_parse(self):
        for p in DESC.rglob('*.xacro'):
            with self.subTest(file=p.name):
                ET.parse(p)

if __name__=='__main__':
    unittest.main()
