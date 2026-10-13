"""ROS 2 package build with an isolated, pinned python-chess dependency.

python-chess is pure Python. Colcon uses setuptools ``develop`` for a symlink
build and ``build_py`` for a regular build. Both paths provision the pinned
library *inside this package*, without system pip, PYTHONPATH exports, or sudo.
The first build can require an Internet connection if no matching local copy
is available. ROS/Gazebo/Stockfish are system prerequisites (see root README).
"""

from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.develop import develop

PACKAGE = 'chess_brain_handover'
VERSION = '1.11.2'
ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / PACKAGE / '_vendor'
CHESS = VENDOR / 'chess'


def _version_ok(chess_dir):
    """Avoid picking up wrong versions, partial installations, or stubs."""
    init_file = chess_dir / '__init__.py'
    engine = chess_dir / 'engine.py'
    if not init_file.is_file() or not engine.is_file():
        return False
    import re
    match = re.search(r'^__version__\s*=\s*[\'\"]([^\'\"]+)',
                      init_file.read_text(encoding='utf-8'), re.M)
    return bool(match and match.group(1) == VERSION)


def _local_candidates():
    """Offline fallback for developers who already ran the previous v1.1 setup."""
    venvs = [os.environ.get('CHESS_ROS2_VENV'),
             str(Path.home() / '.venvs' / 'chess_ros2')]
    for venv in filter(None, venvs):
        yield Path(venv) / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages' / 'chess'
    for entry in sys.path:
        if entry:
            yield Path(entry) / 'chess'


def _ensure_chess():
    if _version_ok(CHESS):
        return
    VENDOR.mkdir(parents=True, exist_ok=True)
    for source in _local_candidates():
        if _version_ok(source):
            print(f'[chess_brain_handover] Bundling python-chess {VERSION} from {source}')
            if CHESS.exists():
                shutil.rmtree(CHESS)
            shutil.copytree(source, CHESS, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            return

    print(f'[chess_brain_handover] Installing python-chess {VERSION} into package at build time...', flush=True)
    with tempfile.TemporaryDirectory(prefix='chess_build_dep_') as temporary:
        cmd = [sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check',
               '--no-deps', '--target', temporary, f'chess=={VERSION}']
        try:
            subprocess.run(cmd, check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise RuntimeError(
                f'Cannot provision python-chess=={VERSION}. '
                'Install python3-pip and ensure network access on the FIRST build, '
                'or pre-install the same version in ~/.venvs/chess_ros2. '
                'No system packages were modified.'
            ) from exc
        downloaded = Path(temporary) / 'chess'
        if not _version_ok(downloaded):
            raise RuntimeError('Downloaded python-chess files failed version/contents verification')
        if CHESS.exists():
            shutil.rmtree(CHESS)
        shutil.copytree(downloaded, CHESS, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))


class BuildWithChess(build_py):
    def run(self):
        _ensure_chess()
        super().run()
        # An ordinary `colcon build` (not symlink) must carry the vendored files
        # into the actual installed Python package, not just leave them in src.
        destination = Path(self.build_lib) / PACKAGE / '_vendor' / 'chess'
        shutil.copytree(CHESS, destination, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))


class DevelopWithChess(develop):
    def run(self):
        _ensure_chess()
        super().run()


setup(
    name=PACKAGE,
    version='1.0.0',
    packages=[PACKAGE],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + PACKAGE]),
        ('share/' + PACKAGE, ['package.xml']),
        ('share/' + PACKAGE + '/launch', ['launch/chess_brain.launch.py']),
    ],
    # Not an external runtime requirement: pinned chess files are placed in
    # _vendor by the build commands above. System packages use rosdep/apt.
    install_requires=['setuptools'],
    cmdclass={'build_py': BuildWithChess, 'develop': DevelopWithChess},
    zip_safe=False,
    maintainer='Dual Robotic Arm Chess Team',
    maintainer_email='noreply@example.com',
    description='Stockfish-backed chess logic + ROS 2 bridge, with isolated python-chess',
    license='MIT',
    entry_points={'console_scripts': [
        'chess_brain_node = chess_brain_handover.ros_node:main',
        'chess_selfplay = chess_brain_handover.selfplay:main',
    ]},
)
