from setuptools import setup

package_name = "chess_brain_handover"

setup(
    name=package_name,
    version="1.0.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", ["launch/chess_brain.launch.py"]),
    ],
    install_requires=["setuptools", "chess>=1.10,<2"],
    zip_safe=True,
    maintainer="Dual Robotic Arm Chess Team",
    maintainer_email="noreply@example.com",
    description="Chess logic and ROS 2 JSON handover bridge for dual robotic-arm chess",
    license="MIT",
    entry_points={
        "console_scripts": [
            "chess_brain_node = chess_brain_handover.ros_node:main",
            "chess_selfplay = chess_brain_handover.selfplay:main",
        ]
    },
)
