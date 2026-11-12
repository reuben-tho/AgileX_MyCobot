# LIMO + MyCobot 280 M5 — ROS 2 Foxy package

This package combines an AgileX LIMO mobile base and an Elephant Robotics MyCobot 280 M5 arm in one robot description. It provides:

- A combined URDF generated from the package's LIMO base model and the vendor's MyCobot 280 M5 URDF/meshes.
- RViz and `joint_state_publisher_gui` sliders for six arm joints and three base target coordinates (X, Y, yaw).
- A Python bridge that sends arm joint targets through `pymycobot` and drives the LIMO toward a base target using odometry and `/cmd_vel`.
- A display-only launch for checking the robot model before powering any motors.

## Target environment

- Ubuntu 20.04
- ROS 2 Foxy
- Elephant Robotics MyCobot 280 M5 (not the 280-JN / Jetson Nano variant)
- AgileX LIMO with its ROS 2 Foxy-compatible driver

**Do not use the previous Humble setup commands with this Foxy workspace.** ROS 2 Foxy is end-of-life, so package availability and compatibility depend on the Ubuntu 20.04 installation you already have. Do not mix `/opt/ros/foxy` with Humble packages.

The MyCobot ROS 2 repository explicitly lists Ubuntu 20.04 / ROS 2 Foxy and provides a `foxy` branch. Its 280 M5 model is located at `mycobot_description/urdf/mycobot_280_m5/mycobot_280_m5.urdf`.

## 1. Create the workspace

```bash
source /opt/ros/foxy/setup.bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws
```

Optional sanity check:

```bash
echo "$ROS_DISTRO"   # should print: foxy
python3 --version     # Ubuntu 20.04 normally uses Python 3.8
```

## 2. Install ROS and Python dependencies

If Foxy is already installed, do not reinstall it. Install the packages used by this project:

```bash
sudo apt update
sudo apt install -y \
  python3-colcon-common-extensions \
  python3-rosdep \
  python3-pip \
  python3-vcstool \
  git \
  ros-foxy-robot-state-publisher \
  ros-foxy-joint-state-publisher-gui \
  ros-foxy-rviz2 \
  ros-foxy-xacro \
  ros-foxy-tf2-geometry-msgs \
  ros-foxy-tf-transformations \
  ros-foxy-rqt-robot-steering

python3 -m pip install --user pymycobot packaging
```

Initialize rosdep once (if it was already initialized, the first command may report that; that is okay):

```bash
sudo rosdep init 2>/dev/null || true
rosdep update
```

Give your account permission to access USB serial devices, then log out and back in:

```bash
sudo usermod -a -G dialout "$USER"
```

## 3. Download vendor packages using Foxy sources

### MyCobot description

```bash
cd ~/ros2_ws/src
git clone -b foxy --depth 1 --filter=blob:none --sparse \
  https://github.com/elephantrobotics/mycobot_ros2.git
cd mycobot_ros2
git sparse-checkout set mycobot_description
```

### LIMO ROS 2 driver

```bash
cd ~/ros2_ws/src
git clone -b foxy --depth 1 \
  https://github.com/agilexrobotics/limo_ros2.git
```

If the LIMO repository reports that the `foxy` branch is unavailable, stop and check the branch/source supplied for your particular LIMO hardware. Do not substitute the Humble branch into a Foxy installation.

## 4. Add this combined-control package

Extract `limo_mycobot_control_foxy.zip`, then copy the `limo_mycobot_control` folder into `~/ros2_ws/src/`.

The resulting layout should look like:

```text
~/ros2_ws/src/
├── limo_mycobot_control/
│   ├── launch/
│   ├── limo_mycobot_control/
│   ├── urdf/
│   ├── rviz/
│   ├── package.xml
│   └── setup.py
├── limo_ros2/
│   ├── limo_base/
│   └── limo_msgs/
└── mycobot_ros2/
    └── mycobot_description/
```

## 5. Foxy compatibility patch for some LIMO driver checkouts

Your supplied setup notes mention a Foxy compiler compatibility change in:

`~/ros2_ws/src/limo_ros2/limo_base/include/limo_base/limo_driver.h`

Only if that file contains the include `tf2_geometry_msgs.hpp`, change it to the Foxy header name shown in your notes:

```bash
LIMO_HEADER=~/ros2_ws/src/limo_ros2/limo_base/include/limo_base/limo_driver.h
if [ -f "$LIMO_HEADER" ] && grep -q 'tf2_geometry_msgs.hpp' "$LIMO_HEADER"; then
  sed -i 's/tf2_geometry_msgs.hpp/tf2_geometry_msgs.h/g' "$LIMO_HEADER"
fi
```

Do not run this patch if the file is missing or the include is already different. The required source patch can vary with the LIMO driver revision.

## 6. Build

```bash
cd ~/ros2_ws
source /opt/ros/foxy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install \
  --packages-up-to limo_mycobot_control limo_base mycobot_description
```

Then source the workspace:

```bash
source ~/ros2_ws/install/setup.bash
```

If colcon says a package name is unknown, check the package names actually present under `src` with:

```bash
colcon list
```

Do not proceed to the hardware launch until the build completes successfully.

## 7. First run: display only, no motor commands

```bash
source /opt/ros/foxy/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch limo_mycobot_control display.launch.py
```

This starts the combined robot description, the joint slider GUI and RViz. It is the recommended first check. The six arm sliders are joint angles. The three base sliders are odometry-frame X, Y and yaw targets.

The arm mount transform and LIMO visual are estimated starting values. Measure the real mounting plate and update the mount arguments before relying on the display for collision or clearance decisions.

## 8. Check LIMO topics before hardware control

Start the LIMO base driver using the launch file available in your Foxy checkout. In the common ROS 2 layout this is:

```bash
ros2 launch limo_base limo_base.launch.py
```

In another terminal, inspect the actual topics:

```bash
ros2 topic list | grep -E 'odom|cmd_vel'
```

This bridge defaults to `/wheel/odom` and `/cmd_vel`. If your driver publishes odometry under another name (for example `/odom`), pass that topic as the `odom_topic` launch argument. Confirm the message is `nav_msgs/msg/Odometry` before using the base sliders:

```bash
ros2 topic info /wheel/odom
ros2 topic echo /wheel/odom --once
```

If your LIMO setup uses a combined bringup launch such as `limo_bringup/limo_start.launch.py`, use that instead and set `start_limo_driver:=false` in the combined hardware launch to avoid starting a second base driver.

## 9. Hardware launch

Verify the MyCobot serial port:

```bash
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```

For the MyCobot 280 M5 the bridge defaults to 115200 baud. Use the device detected on your computer (commonly `/dev/ttyUSB0` or `/dev/ttyACM0`). The 280-JN has different connection assumptions; do not use these M5 defaults for a JN arm.

When the display-only model and topics have been checked, launch at low speed:

```bash
source /opt/ros/foxy/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch limo_mycobot_control hardware.launch.py \
  port:=/dev/ttyUSB0 arm_speed:=15 \
  max_linear_speed:=0.04 max_angular_speed:=0.20
```

If the LIMO base driver is already running in another terminal:

```bash
ros2 launch limo_mycobot_control hardware.launch.py \
  port:=/dev/ttyUSB0 arm_speed:=15 \
  max_linear_speed:=0.04 max_angular_speed:=0.20 \
  start_limo_driver:=false
```

Change `port:=/dev/ttyUSB0` to `port:=/dev/ttyACM0` if that is the detected arm port. If the LIMO odometry topic differs, add for example `odom_topic:=/odom`.

## 10. Behaviour and safety

- The arm bridge sends only joints changed by the operator and reads the arm's measured angles back for RViz.
- The LIMO base sliders set target X, Y and yaw in the odometry frame. The bridge uses bounded `/cmd_vel` commands to approach the target; this is a simple proportional controller, not Nav2 or a safety-rated controller.
- Start by changing only one arm slider a small amount. Test the chassis separately at very low speed on a clear, level floor.
- Keep the arm's entire movement envelope clear and have access to the physical emergency stop.
- Do not run another arm controller (including Elephant Robotics' `slider_control` launch) on the same serial port at the same time.
- Do not run a second teleop/Nav2 controller publishing to the same `/cmd_vel` while using the base sliders.
- The initial base mesh is an approximate visual model, and the arm mount values must be measured on the actual robot.
- No servo calibration is executed automatically. Follow the vendor's exact model-specific procedure for any calibration.

## References

- Elephant Robotics MyCobot ROS 2 repository (Foxy branch): https://github.com/elephantrobotics/mycobot_ros2
- AgileX LIMO ROS 2 repository: https://github.com/agilexrobotics/limo_ros2
- AgileX LIMO ROS 2 Foxy notes from the project setup: see the provided project notes and the Foxy-compatible driver checkout.
