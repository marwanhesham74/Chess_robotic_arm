#!/usr/bin/env python3
"""Structural sanity check for an expanded URDF (read from a file or stdin).

Usage:
  xacro $(ros2 pkg prefix --share dual_chess_description)/urdf/dual_chess.urdf.xacro | \
      ros2 run dual_chess_description check_urdf_structure.py
  ros2 run dual_chess_description check_urdf_structure.py /tmp/dual_chess.urdf

Checks: unique link/joint names, every joint parent/child exists, exactly one root link,
every link reachable from the root (one connected tree, no cycles / multiple parents),
revolute joints have limits, and prints the tree. Exit code 0 = OK, 1 = problems found.
This complements (does not replace) `check_urdf` from urdfdom.
"""
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict


def main() -> int:
    data = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
    robot = ET.fromstring(data)
    errors = []

    links = [l.get('name') for l in robot.findall('link')]
    joints = robot.findall('joint')
    jnames = [j.get('name') for j in joints]

    for kind, names in (('link', links), ('joint', jnames)):
        for n, c in Counter(names).items():
            if c > 1:
                errors.append(f'duplicate {kind} name: {n}')
    clash = set(links) & set(jnames)
    if clash:
        errors.append(f'name used for both a link and a joint: {sorted(clash)}')

    children = defaultdict(list)
    has_parent = {}
    for j in joints:
        p = j.find('parent').get('link')
        c = j.find('child').get('link')
        jn = j.get('name')
        if p not in links:
            errors.append(f'joint {jn}: parent link {p} does not exist')
        if c not in links:
            errors.append(f'joint {jn}: child link {c} does not exist')
        if c in has_parent:
            errors.append(f'link {c} has more than one parent joint ({has_parent[c]}, {jn})')
        has_parent[c] = jn
        children[p].append((jn, c, j.get('type')))
        if j.get('type') in ('revolute', 'prismatic'):
            lim = j.find('limit')
            if lim is None:
                errors.append(f'joint {jn}: {j.get("type")} joint without <limit>')
            elif j.get('type') == 'revolute' and float(lim.get('lower')) >= float(lim.get('upper')):
                errors.append(f'joint {jn}: lower >= upper')

    roots = [l for l in links if l not in has_parent]
    if len(roots) != 1:
        errors.append(f'expected exactly 1 root link, found {roots}')

    seen = set()

    def walk(link, depth=0):
        seen.add(link)
        for jn, c, t in children.get(link, []):
            print('  ' * depth + f'{link} --[{jn}:{t}]--> {c}')
            if c in seen:
                errors.append(f'cycle at {c}')
                continue
            walk(c, depth + 1)

    if roots:
        print(f'root: {roots[0]}')
        walk(roots[0])
    unreachable = set(links) - seen
    if unreachable:
        errors.append(f'links not connected to the root: {sorted(unreachable)}')

    print(f'\nlinks={len(links)} joints={len(jnames)} '
          f'movable={sum(1 for j in joints if j.get("type") != "fixed")}')
    if errors:
        print('\nFAILED:')
        for e in errors:
            print('  -', e)
        return 1
    print('OK: structure valid')
    return 0


if __name__ == '__main__':
    sys.exit(main())
