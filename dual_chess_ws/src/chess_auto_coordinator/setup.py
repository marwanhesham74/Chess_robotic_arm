from setuptools import setup

package_name = 'chess_auto_coordinator'
setup(
    name=package_name, version='0.1.0', packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'], zip_safe=True,
    maintainer='Dual Chess Integration Team',
    maintainer_email='noreply@example.com',
    description='Passive-by-default ROS 2 high-level chess auto game coordinator',
    license='MIT',
    entry_points={'console_scripts': [
        'auto_game_coordinator = chess_auto_coordinator.coordinator_node:main',
    ]},
)
