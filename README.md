# AgileX LIMO + MyCobot 280 M5 — combined ROS 2 slider control
Step 4 — Install the required dependencies
Copy:
sudo apt update

sudo apt install -y \
python3-pip \
python3-colcon-common-extensions \
ros-foxy-rviz2 \
ros-foxy-joint-state-publisher-gui \
ros-foxy-tf-transformations \
ros-foxy-tf2-geometry-msgs \
ros-foxy-rqt-robot-steering


Install Python libraries:
pip3 install --user transforms3d pymycobot packaging


Step 5 — Apply the Foxy compatibility patch and build
First, check the driver header:
grep -n "tf2_geometry_msgs" \
~/ros2_ws/src/limo_ros2/limo_base/include/limo_base/limo_driver.h


If it shows tf2_geometry_msgs.hpp, run:
sed -i 's/tf2_geometry_msgs.hpp/tf2_geometry_msgs.h/g' \
~/ros2_ws/src/limo_ros2/limo_base/include/limo_base/limo_driver.h


Now build:
cd ~/ros2_ws

source /opt/ros/foxy/setup.bash

rm -rf build/limo_base install/limo_base

colcon build --symlink-install \
--packages-select limo_msgs limo_description limo_base


This builds the main LIMO message, description and driver packages.

Compatibility note: AgileX's currently published repository README describes Humble, so the Foxy patch above is based on your supplied setup notes, not a guarantee that every current upstream file supports Foxy. 
GitHub

Step 6 — Source and open RViz
After a successful build:
source ~/ros2_ws/install/setup.bash


Now launch the LIMO model:
ros2 launch limo_description display_models_diff.launch.py


Expected result
RViz should open and display the LIMO robot.
This workspace package brings the mobile base and the 6-DOF arm into one RViz robot model. The same `joint_state_publisher_gui` slider window exposes nine controls:

| Slider | Meaning | Units |
|---|---|---|
| `base_x_joint` | LIMO target X position in the wheel-odometry frame | metres |
| `base_y_joint` | LIMO target Y position in the wheel-odometry frame | metres |
| `base_yaw_joint` | LIMO target heading | radians |
| `joint2_to_joint1` | MyCobot J1 | radians |
| `joint3_to_joint2` | MyCobot J2 | radians |
| `joint4_to_joint3` | MyCobot J3 | radians |
| `joint5_to_joint4` | MyCobot J4 | radians |
| `joint6_to_joint5` | MyCobot J5 | radians |
| `joint6output_to_joint6` | MyCobot J6 | radians |

The arm geometry comes from Elephant Robotics' official `mycobot_description` package. The LIMO chassis in this package is an **approximate visualization model**, not the manufacturer's dimensionally accurate LIMO CAD. The combined URDF is assembled at launch by `description_builder.py`; `generate_combined_urdf` can export it as a normal `.urdf` file.

## Target hardware / ROS version

This bundle targets **Ubuntu 22.04 + ROS 2 Humble**, and assumes:

- AgileX LIMO chassis using the `limo_ros2` Humble driver.
- Elephant Robotics **MyCobot 280 M5** (USB serial, normally `/dev/ttyUSB0` or `/dev/ttyACM0`, 115200 baud).
- The LIMO is configured for differential-drive motion. The controller converts an absolute odometry-frame X/Y/yaw target into bounded `/cmd_vel` commands; it does not command lateral strafing.

Your notes also mention `mycobot_280_jn` and `/dev/ttyTHS1` at 1,000,000 baud. Those are for the **Jetson Nano / 280-JN** variant, not the 280 M5. Do not use the M5 defaults on a JN arm. Your notes also mix ROS 2 Foxy and Humble; install and build one distribution consistently. This package is written for Humble.

## 1. Install ROS dependencies

```bash
sudo apt update
sudo apt install -y \
  ros-humble-desktop \
  ros-humble-robot-state-publisher \
  ros-humble-joint-state-publisher-gui \
  ros-humble-rviz2 \
  ros-humble-xacro \
  python3-colcon-common-extensions \
  python3-pip \
  git

python3 -m pip install --user pymycobot packaging
```

If Ubuntu blocks user-level pip installs due to its externally-managed Python policy, use a virtual environment that can import ROS Python packages, or use the OS/vendor-supported installation method for `pymycobot` rather than forcing a system-wide pip install.

Add your user to the serial-device group, then log out and back in:

```bash
sudo usermod -a -G dialout "$USER"
```

## 2. Download the vendor ROS packages

Use the Humble branches for both projects. Do not combine the Foxy source tree with the Humble binaries.

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src

git clone -b humble --depth 1 https://github.com/elephantrobotics/mycobot_ros2.git
git clone -b humble --depth 1 https://github.com/agilexrobotics/limo_ros2.git
```

The MyCobot repository supplies `mycobot_description` and the official 280 M5 meshes. The LIMO repository supplies `limo_base` and `limo_msgs`.

Copy this package folder into the workspace:

```bash
cp -r /path/to/limo_mycobot_control ~/ros2_ws/src/
```

Replace `/path/to/limo_mycobot_control` with the folder where you extracted this bundle.

Build the dependencies and this package:

```bash
cd ~/ros2_ws
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-up-to limo_mycobot_control limo_base mycobot_description
source ~/ros2_ws/install/setup.bash
```

If `rosdep` reports unrelated optional packages from the full upstream repositories, install the missing dependencies it names or build only the packages required by your installation. The launch files in this bundle require `limo_base`, `mycobot_description`, `robot_state_publisher`, `joint_state_publisher_gui`, and `rviz2`.

## 3. Check the hardware connections

For the MyCobot M5:

```bash
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```

Use the port that appears when the arm is connected. Typical M5 configuration is 115200 baud. The JN variant uses a different port/baud combination; see the model-specific Elephant Robotics documentation before changing this setting.

For LIMO, make sure it is powered and that its driver can start. The Humble driver is normally launched with:

```bash
ros2 launch limo_base limo_base.launch.py
```

The documented odometry and velocity interfaces are `/wheel/odom` (`nav_msgs/msg/Odometry`) and `/cmd_vel` (`geometry_msgs/msg/Twist`). Check them before operating:

```bash
ros2 topic info /wheel/odom
ros2 topic info /cmd_vel
ros2 topic echo /wheel/odom --once
```

## 4. Start combined hardware control

Open a terminal, source Humble and the workspace, then run:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch limo_mycobot_control hardware.launch.py port:=/dev/ttyUSB0
```

Use `port:=/dev/ttyACM0` if that is the serial device detected on your computer.

By default this launch starts the LIMO chassis driver too. If you already started `limo_base.launch.py` in another terminal, use:

```bash
ros2 launch limo_mycobot_control hardware.launch.py port:=/dev/ttyUSB0 start_limo_driver:=false
```

You should see RViz with the combined robot and a joint slider GUI. Drag one arm joint slider at a time initially. The bridge reads the real arm angles and wheel odometry, sends only joints that the operator changes, and publishes measured joint states back to RViz. The slider GUI is a command panel (its initial slider values may not match the arm pose); RViz shows the measured arm/base state. Moving a slider sends that joint to the slider value.

### LIMO position sliders

The base sliders are **absolute target positions in the LIMO odometry frame**. For example, moving `base_x_joint` to `0.30` requests a target 30 cm forward of the odometry origin. The base controller uses low, bounded velocities (defaults: 0.08 m/s and 0.35 rad/s maximum). `base_y_joint` requests a world-frame Y offset; since the assumed chassis is differential drive, the LIMO turns and drives to reach it. The robot stops when it is within the configured position and heading tolerances.

To lower the base speed further:

```bash
ros2 launch limo_mycobot_control hardware.launch.py \
  port:=/dev/ttyUSB0 max_linear_speed:=0.04 max_angular_speed:=0.20 arm_speed:=15
```

### Arm sliders

The bridge converts the six model joint angles from radians to degrees and calls `MyCobot280.send_angle(joint_id, angle, speed)`. Manufacturer 280-series angle limits are applied to the generated sliders and checked again before a command is sent. The default arm speed is 20%.

## 5. Display-only mode (no motors commanded)

Use this to inspect the assembled URDF and move the RViz model without connecting to the hardware:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch limo_mycobot_control display.launch.py
```

This is the safest first launch to check the arm/base mounting position visually.

## 6. Export the combined URDF

After building and sourcing the workspace:

```bash
ros2 run limo_mycobot_control generate_combined_urdf --output ~/ros2_ws/limo_mycobot280.urdf
```

The generated file references mesh assets using `package://mycobot_description/...`, so the `mycobot_description` package must remain installed in the ROS environment where RViz loads the file.

The mount transform can be adjusted in either launch file:

```bash
ros2 launch limo_mycobot_control display.launch.py \
  arm_mount_x:=0.01 arm_mount_y:=0.00 arm_mount_z:=0.215 arm_mount_yaw:=0.0
```

`arm_mount_x` and `arm_mount_y` are relative to the visual top-plate centre; `arm_mount_z` is the height of the arm base above the odometry/floor origin. The current defaults are estimates only. Measure the real plate and update these values before using RViz for collision/clearance decisions.

## 7. Important safety notes

1. **First use display-only mode.** Check that the arm is upright, the base size looks plausible, the mount location matches the physical platform, and no links overlap.
2. Before enabling hardware, put the robot on a clear, level floor; keep the arm's full range clear; have a person at the physical emergency stop; and use a low arm speed and base speed.
3. The hardware bridge intentionally ignores the slider GUI's initial zero state. It only commands an arm joint after that slider is changed. It starts the base target from the first measured odometry pose and only activates after a base slider is changed.
4. Do not run Elephant Robotics' `slider_control.launch.py` at the same time as this package; both would try to control the same arm serial port. Also do not run another teleop/Nav2 publisher to `/cmd_vel` at the same time as this manual base slider controller.
5. The base visual is approximate, and the default arm mounting transform is not certified. Verify physical mounting dimensions and stability. A mounted arm changes the robot's centre of gravity and safe operating envelope.
6. Your notes' calibration snippet calls `set_servo_calibration()` on all six joints. Calibration changes should only be performed according to the exact model's vendor procedure; this bundle never calibrates automatically.
7. If `/wheel/odom` or `/cmd_vel` is namespaced/renamed on your platform, pass `odom_topic:=...` and `cmd_vel_topic:=...` at launch. The LIMO controller is a simple proportional position controller, not a navigation stack or safety-rated motion controller.

## 8. Troubleshooting

- **Arm not detected:** verify `port`, 115200 baud, arm power/USB, firmware and `dialout` permissions. Test with the vendor's `pymycobot` examples before using the slider bridge.
- **No LIMO movement:** check that `/wheel/odom` is publishing, that the chassis driver is running, and that `/cmd_vel` reaches the LIMO. Confirm the chassis is in differential-drive mode.
- **Robot model missing:** confirm `mycobot_description` is installed and that its 280 M5 meshes are present under `share/mycobot_description/urdf/mycobot_280_m5/`.
- **RViz fixed-frame error:** this configuration uses `world` as its fixed frame. Select `world` in RViz Global Options if loading another RViz config.
- **Slider GUI missing:** install `ros-humble-joint-state-publisher-gui`. The upstream MyCobot ROS 2 README also documents a Humble-specific GUI workaround if its slider window fails to render.

## References used

- AgileX LIMO ROS 2 (Humble) repository: https://github.com/agilexrobotics/limo_ros2
- AgileX LIMO ROS 2 Humble documentation: https://github.com/agilexrobotics/limo_ros2_doc/blob/master/LIMO-ROS2-humble%28EN%29.md
- Elephant Robotics MyCobot ROS 2 repository (Humble branch): https://github.com/elephantrobotics/mycobot_ros2
- Elephant Robotics MyCobot 280 M5 slider-control guide: https://docs.elephantrobotics.com/docs/mycobot-m5-en/12-ApplicationBaseROS/12.2-ROS2/12.2.4-rivzIntroductionAndUse/myCobot-280.html
- Elephant Robotics `pymycobot` MyCobot 280 API: https://github.com/elephantrobotics/pymycobot/blob/main/docs/MyCobot_280_en.md
