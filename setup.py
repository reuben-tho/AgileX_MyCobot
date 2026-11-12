from setuptools import setup
from glob import glob
import os

package_name = 'limo_mycobot_control'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*')),
        (os.path.join('share', package_name, 'rviz'), glob('rviz/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Project Maintainer',
    maintainer_email='maintainer@example.com',
    description='Combined LIMO + MyCobot 280 M5 slider control',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'joint_slider_bridge = limo_mycobot_control.joint_slider_bridge:main',
            'generate_combined_urdf = limo_mycobot_control.generate_combined_urdf:main',
        ],
    },
)
