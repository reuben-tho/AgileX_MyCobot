"""Bridge joint_state_publisher_gui sliders to a MyCobot 280 M5 and AgileX LIMO.

Input : /joint_states_cmd (sensor_msgs/JointState) from the slider GUI
Output: /joint_states     (measured arm angles + measured LIMO odometry pose)
Base  : /wheel/odom -> closed-loop /cmd_vel controller
Arm   : pymycobot MyCobot280.send_angle() joint-by-joint
"""
from __future__ import annotations

import math
import time
from typing import Dict, Optional, Tuple

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist


ARM_JOINTS = [
    "joint2_to_joint1",       # MyCobot J1
    "joint3_to_joint2",       # MyCobot J2
    "joint4_to_joint3",       # MyCobot J3
    "joint5_to_joint4",       # MyCobot J4
    "joint6_to_joint5",       # MyCobot J5
    "joint6output_to_joint6", # MyCobot J6
]
BASE_JOINTS = ["base_x_joint", "base_y_joint", "base_yaw_joint"]
# Manufacturer API ranges for the MyCobot 280 series, in degrees.
ARM_LIMITS_DEG = [(-168.0, 168.0), (-135.0, 135.0), (-150.0, 150.0),
                  (-145.0, 145.0), (-155.0, 160.0), (-180.0, 180.0)]


def wrap_angle(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))


def quaternion_to_yaw(x: float, y: float, z: float, w: float) -> float:
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


class JointSliderBridge(Node):
    def __init__(self) -> None:
        super().__init__("limo_mycobot_joint_slider_bridge")

        self.declare_parameter("port", "/dev/ttyUSB0")
        self.declare_parameter("baud", 115200)
        self.declare_parameter("arm_speed", 20)
        self.declare_parameter("arm_enabled", True)
        self.declare_parameter("base_enabled", True)
        self.declare_parameter("odom_topic", "/wheel/odom")
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("max_linear_speed", 0.08)
        self.declare_parameter("max_angular_speed", 0.35)
        self.declare_parameter("xy_tolerance", 0.035)
        self.declare_parameter("yaw_tolerance", 0.05)
        self.declare_parameter("odom_timeout", 0.60)

        self.port = str(self.get_parameter("port").value)
        self.baud = int(self.get_parameter("baud").value)
        self.arm_speed = max(1, min(100, int(self.get_parameter("arm_speed").value)))
        self.arm_enabled = bool(self.get_parameter("arm_enabled").value)
        self.base_enabled = bool(self.get_parameter("base_enabled").value)
        self.odom_topic = str(self.get_parameter("odom_topic").value)
        self.cmd_vel_topic = str(self.get_parameter("cmd_vel_topic").value)
        self.max_linear_speed = float(self.get_parameter("max_linear_speed").value)
        self.max_angular_speed = float(self.get_parameter("max_angular_speed").value)
        self.xy_tolerance = float(self.get_parameter("xy_tolerance").value)
        self.yaw_tolerance = float(self.get_parameter("yaw_tolerance").value)
        self.odom_timeout = float(self.get_parameter("odom_timeout").value)

        self.mc = None
        self.arm_angles_deg = [0.0] * 6
        self.arm_targets_deg = [0.0] * 6
        self.pending_arm_ids = set()
        self.last_arm_send_time = 0.0
        self.arm_feedback_ok = False

        self.odom_pose: Optional[Tuple[float, float, float]] = None
        self.last_odom_monotonic = 0.0
        self.base_target: Optional[Tuple[float, float, float]] = None
        self.pending_base_changes: Dict[str, float] = {}
        # Sliders start at zero. Pre-seeding avoids dropping the first real
        # user adjustment on systems where the GUI does not publish an initial sample.
        self.last_slider_values: Optional[Dict[str, float]] = {name: 0.0 for name in (BASE_JOINTS + ARM_JOINTS)}

        self.joint_pub = self.create_publisher(JointState, "/joint_states", 10)
        self.cmd_pub = self.create_publisher(Twist, self.cmd_vel_topic, 10)
        self.slider_sub = self.create_subscription(
            JointState, "/joint_states_cmd", self.slider_callback, 10
        )
        self.odom_sub = self.create_subscription(
            Odometry, self.odom_topic, self.odom_callback, 10
        )

        if self.arm_enabled:
            self._connect_arm()
        else:
            self.get_logger().info("Arm hardware disabled; arm feedback will remain at zero.")

        self.timer = self.create_timer(0.10, self.control_and_publish)
        self.get_logger().info(
            "Bridge ready. Slider input: /joint_states_cmd; robot state output: /joint_states; "
            f"LIMO odometry: {self.odom_topic}; base command: {self.cmd_vel_topic}."
        )

    def _connect_arm(self) -> None:
        try:
            try:
                from pymycobot.mycobot280 import MyCobot280
            except ImportError:
                from pymycobot import MyCobot280
            self.mc = MyCobot280(self.port, self.baud)
            time.sleep(0.6)
            angles = None
            for attempt in range(5):
                angles = self.mc.get_angles()
                if isinstance(angles, (list, tuple)) and len(angles) == 6:
                    break
                self.get_logger().warning(
                    f"Waiting for valid MyCobot feedback ({attempt + 1}/5)..."
                )
                time.sleep(0.4)
            if isinstance(angles, (list, tuple)) and len(angles) == 6:
                self.arm_angles_deg = [float(v) for v in angles]
                self.arm_targets_deg = list(self.arm_angles_deg)
                self.arm_feedback_ok = True
                self.get_logger().info(
                    f"Connected to MyCobot 280 on {self.port} at {self.baud} baud. "
                    f"Feedback angles: {[round(v, 1) for v in self.arm_angles_deg]}"
                )
            else:
                self.get_logger().warning(
                    "Serial port opened but get_angles() did not return six angles. "
                    "Arm motion is inhibited until valid feedback is available."
                )
                self.mc = None
        except Exception as exc:  # keep the LIMO side usable if only the arm fails
            self.mc = None
            self.get_logger().error(f"Could not connect to MyCobot at {self.port}: {exc}")
            self.get_logger().error(
                "Check port/baud, USB cable, power, firmware and dialout permissions."
            )

    def slider_callback(self, msg: JointState) -> None:
        values = {name: float(pos) for name, pos in zip(msg.name, msg.position)}
        # Arm: update only joints actually moved by the operator. The hardware
        # command timer sends at most one pending joint command per 100 ms tick.
        if self.arm_enabled and self.mc is not None:
            for idx, joint_name in enumerate(ARM_JOINTS):
                if joint_name not in values:
                    continue
                old = self.last_slider_values.get(joint_name, values[joint_name])
                if abs(values[joint_name] - old) < math.radians(0.35):
                    continue
                target_deg = math.degrees(values[joint_name])
                low, high = ARM_LIMITS_DEG[idx]
                if not (low <= target_deg <= high):
                    self.get_logger().warning(
                        f"Rejected J{idx + 1} target {target_deg:.1f} deg; "
                        f"allowed range is {low:.0f}..{high:.0f} deg."
                    )
                    continue
                self.arm_targets_deg[idx] = target_deg
                self.pending_arm_ids.add(idx)

        # Base: sliders are target odometry x/y/yaw. Start from current odometry
        # on the first intentional change, then update only axes moved by user.
        base_changes: Dict[str, float] = {}
        thresholds = {"base_x_joint": 0.002, "base_y_joint": 0.002,
                      "base_yaw_joint": math.radians(0.5)}
        for joint_name in BASE_JOINTS:
            if joint_name not in values:
                continue
            old = self.last_slider_values.get(joint_name, values[joint_name])
            if abs(values[joint_name] - old) >= thresholds[joint_name]:
                base_changes[joint_name] = values[joint_name]

        if base_changes:
            if self.odom_pose is None:
                self.pending_base_changes.update(base_changes)
                self.get_logger().warning(
                    "Base slider changed before odometry arrived; target will be applied "
                    "when /wheel/odom is available."
                )
            else:
                self._apply_base_changes(base_changes)

        self.last_slider_values.update(values)

    def _apply_base_changes(self, changes: Dict[str, float]) -> None:
        if self.base_target is None:
            self.base_target = self.odom_pose
        assert self.base_target is not None
        tx, ty, tyaw = self.base_target
        if "base_x_joint" in changes:
            tx = changes["base_x_joint"]
        if "base_y_joint" in changes:
            ty = changes["base_y_joint"]
        if "base_yaw_joint" in changes:
            tyaw = changes["base_yaw_joint"]
        self.base_target = (tx, ty, tyaw)
        self.get_logger().info(
            f"New LIMO target (odom frame): x={tx:.2f} m, y={ty:.2f} m, "
            f"yaw={math.degrees(tyaw):.1f} deg"
        )

    def odom_callback(self, msg: Odometry) -> None:
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        self.odom_pose = (float(p.x), float(p.y), quaternion_to_yaw(q.x, q.y, q.z, q.w))
        self.last_odom_monotonic = time.monotonic()
        if self.pending_base_changes:
            self._apply_base_changes(self.pending_base_changes)
            self.pending_base_changes.clear()

    def _send_pending_arm_command(self) -> None:
        if self.mc is None or not self.pending_arm_ids:
            return
        now = time.monotonic()
        if now - self.last_arm_send_time < 0.095:
            return
        # Lowest joint ID first, then the next pending one on a later timer tick.
        idx = min(self.pending_arm_ids)
        target = self.arm_targets_deg[idx]
        try:
            result = self.mc.send_angle(idx + 1, target, self.arm_speed)
            if result not in (None, 1):
                self.get_logger().warning(f"MyCobot returned {result!r} for J{idx + 1}")
            self.pending_arm_ids.discard(idx)
            self.last_arm_send_time = now
        except Exception as exc:
            self.get_logger().error(f"Failed to send J{idx + 1} command: {exc}")
            self.pending_arm_ids.discard(idx)

    def _read_arm_feedback(self) -> None:
        if self.mc is None:
            return
        try:
            angles = self.mc.get_angles()
            if isinstance(angles, (list, tuple)) and len(angles) == 6:
                self.arm_angles_deg = [float(v) for v in angles]
                self.arm_feedback_ok = True
        except Exception as exc:
            self.get_logger().warning(f"MyCobot feedback read failed: {exc}")

    def _base_velocity_command(self) -> Twist:
        command = Twist()
        if not self.base_enabled or self.base_target is None or self.odom_pose is None:
            return command
        if time.monotonic() - self.last_odom_monotonic > self.odom_timeout:
            return command

        x, y, yaw = self.odom_pose
        tx, ty, tyaw = self.base_target
        dx, dy = tx - x, ty - y
        distance = math.hypot(dx, dy)

        if distance > self.xy_tolerance:
            desired_heading = math.atan2(dy, dx)
            heading_error = wrap_angle(desired_heading - yaw)
            # Turn in place for large heading errors rather than driving sideways.
            if abs(heading_error) > 1.15:
                linear = 0.0
                angular = 1.4 * heading_error
            else:
                linear = min(self.max_linear_speed, 0.65 * distance) * max(
                    0.0, math.cos(heading_error)
                )
                angular = 1.8 * heading_error
        else:
            yaw_error = wrap_angle(tyaw - yaw)
            if abs(yaw_error) > self.yaw_tolerance:
                linear = 0.0
                angular = 1.6 * yaw_error
            else:
                linear = 0.0
                angular = 0.0

        command.linear.x = max(-self.max_linear_speed, min(self.max_linear_speed, linear))
        command.angular.z = max(-self.max_angular_speed, min(self.max_angular_speed, angular))
        return command

    def control_and_publish(self) -> None:
        self._send_pending_arm_command()
        self._read_arm_feedback()

        cmd = self._base_velocity_command()
        if self.base_enabled:
            self.cmd_pub.publish(cmd)

        now_msg = self.get_clock().now().to_msg()
        joint_state = JointState()
        joint_state.header.stamp = now_msg
        joint_state.name = BASE_JOINTS + ARM_JOINTS
        if self.odom_pose is None:
            joint_state.position = [0.0, 0.0, 0.0]
        else:
            joint_state.position = [self.odom_pose[0], self.odom_pose[1], self.odom_pose[2]]
        joint_state.position += [math.radians(v) for v in self.arm_angles_deg]
        self.joint_pub.publish(joint_state)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = JointSliderBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Always request a zero chassis velocity on shutdown.
        try:
            node.cmd_pub.publish(Twist())
        except Exception:
            pass
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
