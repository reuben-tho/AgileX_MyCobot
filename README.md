# AgileX_MyCobot
Step 1 — Create your workspace
Open your Ubuntu terminal and run:
source /opt/ros/foxy/setup.bash

mkdir -p ~/ros2_ws/src

cd ~/ros2_ws


Step 2 — Download the robot packages
For the MyCobot:
cd ~/ros2_ws/src

git clone -b foxy --depth 1 --filter=blob:none --sparse \
https://github.com/elephantrobotics/mycobot_ros2.git

cd mycobot_ros2

git sparse-checkout set mycobot_description


For the LIMO:
cd ~/ros2_ws/src

git clone -b foxy --depth 1 \
https://github.com/agilexrobotics/limo_ros2.git


The LIMO driver may require the Foxy compatibility patch described in your original notes.
Step 3 — Put my package into the workspace
Extract the Foxy ZIP into:
~/ros2_ws/src/


Your folder structure should look like:
ros2_ws/
└── src/
    ├── limo_mycobot_control/
    ├── limo_ros2/
    └── mycobot_ros2/
        └── mycobot_description/
How the controls work
The package provides nine sliders in the ROS joint slider GUI, with the robot model displayed in RViz:
Sliders	Function
Base X, Y, yaw	Set the LIMO's target position and heading
Joints 1–6	Move the six MyCobot arm joints

The LIMO controller uses wheel odometry and sends bounded velocity commands. Its documented interfaces are /wheel/odom and /cmd_vel. 
GitHub


The arm bridge reads the actual joint angles and sends the changed joint target to the MyCobot. The joint names are taken from the official 280 M5 robot description. 
GitHub+1


One clarification: the sliders appear in the standard joint_state_publisher_gui window beside RViz; they are not a custom panel embedded inside RViz.
Installation and first run
The package targets Ubuntu 22.04 + ROS 2 Humble. The official MyCobot ROS 2 repository has a Humble branch, and the LIMO driver documentation provides the Humble base setup. 
GitHub+1


After extracting the ZIP, place the limo_mycobot_control folder inside ~/ros2_ws/src, install the vendor packages and dependencies, then build:
cd ~/ros2_ws
source /opt/ros/humble/setup.bash

rosdep install --from-paths src --ignore-src -r -y

colcon build --symlink-install \
  --packages-up-to limo_mycobot_control limo_base mycobot_description

source install/setup.bash


First inspect the combined robot without connecting to motors:
ros2 launch limo_mycobot_control display.launch.py


Then launch hardware control:
ros2 launch limo_mycobot_control hardware.launch.py port:=/dev/ttyUSB0


Use /dev/ttyACM0 instead if that is the serial device detected for your arm. The standard 280 M5 connection uses 115200 baud. 
GitBook

Important before operating
- The LIMO chassis model in the package is an approximate visual model, not the manufacturer's exact CAD.
- The arm mounting position is an estimated starting point. Measure the real mounting plate and adjust the mount parameters before relying on the visualization.
- Start with display-only mode. For hardware tests, use low speeds, keep the arm's movement area clear, and have access to the physical emergency stop.
- Your notes mix the 280-JN and 280 M5 variants. This package is for the 280 M5, not the JN version.
- I verified the Python syntax, base URDF parsing, description-builder assembly with a test model, and ZIP integrity. I could not run a ROS build or test the physical hardware in this environment.
The package README contains the complete commands, configuration options, troubleshooting notes and safety instructions. The most useful next check is to compare the actual arm mounting position and USB device name against the package defaults before the first hardware launch.
