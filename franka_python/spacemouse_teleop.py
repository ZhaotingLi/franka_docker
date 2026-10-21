#!/usr/bin/env python3
"""Teleoperate a Franka Panda directly with a 3Dconnexion SpaceMouse.

The script reads ``pyspacemouse`` in-process, so the separate
``spacemouse_single.py`` ROS bridge is not needed. Cartesian velocity commands
are integrated into equilibrium-pose goals for the controller used by
the Franka.

Controls:
    Move/push/pull the cap: translate the end effector.
    Twist/tilt the cap: rotate the end effector in the world frame.
    Button 0: close the gripper by one step.
    Button 1: open the gripper by one step.
    Both buttons: re-synchronise the goal with the measured robot pose.

Run this only after the Franka Cartesian impedance controller is active:

    python3 env/franka/spacemouse_teleop.py
"""

import argparse
import math
import sys
import time
from typing import Sequence, Tuple

import numpy as np
import quaternion  # noqa: F401 - registers np.quaternion
import rospy
from franka_gripper.msg import MoveActionGoal
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import JointState

try:
    import pyspacemouse
except ImportError:
    pyspacemouse = None


DEFAULT_WORKSPACE = (0.30, 0.80, -0.40, 0.40, 0.05, 0.80)


def make_pose(position: np.ndarray, orientation: np.quaternion) -> PoseStamped:
    """Build the Cartesian equilibrium-pose message used by the controller."""
    pose = PoseStamped()
    pose.pose.position.x = position[0]
    pose.pose.position.y = position[1]
    pose.pose.position.z = position[2]
    pose.pose.orientation.w = orientation.w
    pose.pose.orientation.x = orientation.x
    pose.pose.orientation.y = orientation.y
    pose.pose.orientation.z = orientation.z
    return pose


class FrankaRobotInterface:
    """Minimal ROS interface needed by this standalone teleoperation script."""

    def __init__(self):
        self.K_pos = 1000
        self.K_ori = 25
        self.K_ns = 10

        self.curr_pos = None
        self.curr_ori = None
        self.curr_grip_width = 0.08
        self.gripper_width = self.curr_grip_width

        self.goal_pub = rospy.Publisher("/equilibrium_pose", PoseStamped, queue_size=1)
        self.move_pub = rospy.Publisher(
            "/franka_gripper/move/goal", MoveActionGoal, queue_size=1
        )
        self.pose_sub = rospy.Subscriber(
            "/cartesian_pose", PoseStamped, self._pose_callback, queue_size=1
        )
        self.joint_sub = rospy.Subscriber(
            "/joint_states", JointState, self._joint_state_callback, queue_size=1
        )

        self.move_command = MoveActionGoal()
        self.move_command.goal.speed = 1.0

    def _pose_callback(self, message: PoseStamped) -> None:
        self.curr_pos = np.array(
            (
                message.pose.position.x,
                message.pose.position.y,
                message.pose.position.z,
            ),
            dtype=float,
        )
        self.curr_ori = np.array(
            (
                message.pose.orientation.w,
                message.pose.orientation.x,
                message.pose.orientation.y,
                message.pose.orientation.z,
            ),
            dtype=float,
        )

    def _joint_state_callback(self, message: JointState) -> None:
        if len(message.position) >= 9:
            self.gripper_width = float(message.position[7] + message.position[8])

    def move_gripper(self, width: float) -> None:
        self.move_command.goal.width = width
        self.move_pub.publish(self.move_command)

    def set_stiffness(
        self,
        k_t1: float,
        k_t2: float,
        k_t3: float,
        k_r1: float,
        k_r2: float,
        k_r3: float,
        k_ns: float,
    ) -> None:
        # Imported lazily because stiffness configuration is optional.
        import dynamic_reconfigure.client

        client = dynamic_reconfigure.client.Client(
            "/dynamic_reconfigure_compliance_param_node",
            config_callback=None,
            timeout=60.0,
        )
        client.update_configuration(
            {
                "translational_stiffness_X": k_t1,
                "translational_stiffness_Y": k_t2,
                "translational_stiffness_Z": k_t3,
                "rotational_stiffness_X": k_r1,
                "rotational_stiffness_Y": k_r2,
                "rotational_stiffness_Z": k_r3,
                "nullspace_stiffness": k_ns,
            }
        )


def apply_deadzone(values: Sequence[float], deadzone: float) -> np.ndarray:
    """Apply a continuous per-axis deadzone and keep the result in [-1, 1]."""
    values = np.clip(np.asarray(values, dtype=float), -1.0, 1.0)
    magnitude = np.abs(values)
    scaled = np.maximum(magnitude - deadzone, 0.0) / (1.0 - deadzone)
    return np.sign(values) * scaled


def spacemouse_commands(state, deadzone: float) -> Tuple[np.ndarray, np.ndarray]:
    """Convert a pyspacemouse state to Franka world-frame velocity commands.

    This is the effective axis/sign mapping used by
    tools/pyspacemouse_to_ros/spacemouse_single.py.
    """
    linear = (-state.y, state.x, state.z)
    angular = (-state.roll, -state.pitch, -state.yaw)
    return apply_deadzone(linear, deadzone), apply_deadzone(angular, deadzone)


def quaternion_from_rotation_vector(rotation_vector: np.ndarray) -> np.quaternion:
    """Create a unit quaternion from an axis-angle rotation vector."""
    angle = float(np.linalg.norm(rotation_vector))
    if angle < 1e-12:
        return np.quaternion(1.0, 0.0, 0.0, 0.0)

    xyz = rotation_vector * (math.sin(0.5 * angle) / angle)
    return np.quaternion(math.cos(0.5 * angle), xyz[0], xyz[1], xyz[2])


def normalized_quaternion(value: np.quaternion) -> np.quaternion:
    norm = math.sqrt(
        value.w * value.w + value.x * value.x + value.y * value.y + value.z * value.z
    )
    if norm < 1e-12:
        raise ValueError("Cannot normalize a zero quaternion.")
    return np.quaternion(value.w / norm, value.x / norm, value.y / norm, value.z / norm)


def limit_orientation_distance(
    measured: np.quaternion,
    target: np.quaternion,
    max_angle: float,
) -> np.quaternion:
    """Limit target to ``max_angle`` radians from measured using SLERP."""
    measured_array = np.array(
        (measured.w, measured.x, measured.y, measured.z), dtype=float
    )
    target_array = np.array((target.w, target.x, target.y, target.z), dtype=float)
    dot = float(np.dot(measured_array, target_array))
    if dot < 0.0:
        target_array *= -1.0
        dot *= -1.0

    dot = float(np.clip(dot, -1.0, 1.0))
    angle = 2.0 * math.acos(dot)
    if angle <= max_angle:
        return target

    fraction = max_angle / angle
    half_angle = math.acos(dot)
    if half_angle < 1e-8:
        result = measured_array + fraction * (target_array - measured_array)
    else:
        denominator = math.sin(half_angle)
        result = (
            math.sin((1.0 - fraction) * half_angle) / denominator * measured_array
            + math.sin(fraction * half_angle) / denominator * target_array
        )
    return normalized_quaternion(
        np.quaternion(result[0], result[1], result[2], result[3])
    )


class FrankaSpaceMouseTeleop:
    """Integrate SpaceMouse input and publish bounded Franka pose goals."""

    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.robot = FrankaRobotInterface()

        x_min, x_max, y_min, y_max, z_min, z_max = args.workspace
        self.workspace_min = np.array((x_min, y_min, z_min), dtype=float)
        self.workspace_max = np.array((x_max, y_max, z_max), dtype=float)
        if np.any(self.workspace_min >= self.workspace_max):
            raise ValueError("Each workspace minimum must be smaller than its maximum.")

        self.target_position = None
        self.target_orientation = None
        self.gripper_width = None
        self.previous_buttons = (0, 0)

    def wait_for_robot_pose(self) -> None:
        deadline = time.monotonic() + self.args.pose_timeout
        rate = rospy.Rate(50)
        while not rospy.is_shutdown():
            if self.robot.curr_pos is not None and self.robot.curr_ori is not None:
                return
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    "No /cartesian_pose message received within "
                    f"{self.args.pose_timeout:.1f} seconds."
                )
            rate.sleep()
        raise RuntimeError("ROS shut down before a Franka pose was received.")

    def synchronize_target(self) -> None:
        """Set the target to the latest measured pose without causing a jump."""
        self.target_position = np.asarray(self.robot.curr_pos, dtype=float).copy()
        orientation = np.asarray(self.robot.curr_ori, dtype=float)
        self.target_orientation = normalized_quaternion(
            np.quaternion(
                orientation[0], orientation[1], orientation[2], orientation[3]
            )
        )

    def initialize(self) -> None:
        self.wait_for_robot_pose()
        self.synchronize_target()

        if np.any(self.target_position < self.workspace_min) or np.any(
            self.target_position > self.workspace_max
        ):
            raise RuntimeError(
                f"Current pose {self.target_position.tolist()} is outside workspace "
                f"{self.args.workspace}. Adjust --workspace before teleoperating."
            )

        measured_width = getattr(
            self.robot, "gripper_width", self.robot.curr_grip_width
        )
        self.gripper_width = float(
            np.clip(measured_width, self.args.gripper_min, self.args.gripper_max)
        )

        if self.args.set_stiffness:
            self.robot.set_stiffness(
                self.robot.K_pos,
                self.robot.K_pos,
                self.robot.K_pos,
                self.robot.K_ori,
                self.robot.K_ori,
                self.robot.K_ori,
                self.robot.K_ns,
            )

        self.publish_target()

    def publish_target(self) -> None:
        goal = make_pose(self.target_position, self.target_orientation)
        goal.header.stamp = rospy.Time.now()
        self.robot.goal_pub.publish(goal)

    def update_gripper(self, buttons: Sequence[int]) -> None:
        padded = tuple(int(value) for value in buttons[:2])
        padded += (0,) * (2 - len(padded))

        both_pressed = padded[0] and padded[1]
        both_were_pressed = self.previous_buttons[0] and self.previous_buttons[1]
        if both_pressed:
            if not both_were_pressed:
                self.synchronize_target()
                rospy.loginfo("Pose goal re-synchronised with the robot.")
        elif padded[0] and not self.previous_buttons[0]:
            self.gripper_width = max(
                self.args.gripper_min,
                self.gripper_width - self.args.gripper_step,
            )
            self.robot.move_gripper(self.gripper_width)
            rospy.loginfo("Gripper width command: %.3f m", self.gripper_width)
        elif padded[1] and not self.previous_buttons[1]:
            self.gripper_width = min(
                self.args.gripper_max,
                self.gripper_width + self.args.gripper_step,
            )
            self.robot.move_gripper(self.gripper_width)
            rospy.loginfo("Gripper width command: %.3f m", self.gripper_width)

        self.previous_buttons = padded

    def update_target(
        self,
        linear_command: np.ndarray,
        angular_command: np.ndarray,
        dt: float,
    ) -> None:
        proposed_position = (
            self.target_position + linear_command * self.args.linear_speed * dt
        )
        proposed_position = np.clip(
            proposed_position, self.workspace_min, self.workspace_max
        )

        # Keep the impedance attractor close to the measured pose if the robot
        # cannot keep up with the operator.
        measured_position = np.asarray(self.robot.curr_pos, dtype=float)
        attractor_delta = proposed_position - measured_position
        attractor_distance = float(np.linalg.norm(attractor_delta))
        if attractor_distance > self.args.max_attractor_distance:
            attractor_delta *= self.args.max_attractor_distance / attractor_distance
            proposed_position = measured_position + attractor_delta
        self.target_position = proposed_position

        if not self.args.translation_only:
            rotation_vector = angular_command * self.args.angular_speed * dt
            delta_orientation = quaternion_from_rotation_vector(rotation_vector)
            # Left multiplication makes the SpaceMouse rotations world-frame.
            proposed_orientation = normalized_quaternion(
                delta_orientation * self.target_orientation
            )
            measured_orientation_array = np.asarray(self.robot.curr_ori, dtype=float)
            measured_orientation = normalized_quaternion(
                np.quaternion(
                    measured_orientation_array[0],
                    measured_orientation_array[1],
                    measured_orientation_array[2],
                    measured_orientation_array[3],
                )
            )
            self.target_orientation = limit_orientation_distance(
                measured_orientation,
                proposed_orientation,
                self.args.max_attractor_angle,
            )

    # def run(self) -> None:
    #     self.initialize()
    #     rospy.loginfo(
    #         "SpaceMouse teleoperation ready: %.3f m/s, %.3f rad/s, %.1f Hz.",
    #         self.args.linear_speed,
    #         self.args.angular_speed,
    #         self.args.rate,
    #     )
    #     rospy.loginfo(
    #         "Button 0 closes, button 1 opens, and both buttons re-sync the pose."
    #     )

    #     rate = rospy.Rate(self.args.rate)
    #     max_dt = 2.0 / self.args.rate
    #     last_time = time.monotonic()

    #     with pyspacemouse.open() as device:
    #         rospy.loginfo("SpaceMouse opened.")
    #         while not rospy.is_shutdown():
    #             state = device.read()
    #             now = time.monotonic()
    #             dt = min(max(now - last_time, 0.0), max_dt)
    #             last_time = now

    #             if state is None:
    #                 linear_command = np.zeros(3)
    #                 angular_command = np.zeros(3)
    #             else:
    #                 linear_command, angular_command = spacemouse_commands(
    #                     state, self.args.deadzone
    #                 )
    #                 self.update_gripper(state.buttons)

    #             self.update_target(linear_command, angular_command, dt)
    #             self.publish_target()
    #             rate.sleep()

    
    def run(self) -> None:
        self.initialize()
        rospy.loginfo(
            "SpaceMouse teleoperation ready: %.3f m/s, %.3f rad/s, %.1f Hz.",
            self.args.linear_speed,
            self.args.angular_speed,
            self.args.rate,
        )
        rospy.loginfo(
            "Button 0 closes, button 1 opens, and both buttons re-sync the pose."
        )

        rate = rospy.Rate(self.args.rate)
        max_dt = 2.0 / self.args.rate
        last_time = time.monotonic()

        device = pyspacemouse.open()
        if not device:
            raise RuntimeError("Could not open SpaceMouse.")

        rospy.loginfo("SpaceMouse opened.")

        while not rospy.is_shutdown():
            state = pyspacemouse.read()

            now = time.monotonic()
            dt = min(max(now - last_time, 0.0), max_dt)
            last_time = now

            if state is None:
                linear_command = np.zeros(3)
                angular_command = np.zeros(3)
            else:
                linear_command, angular_command = spacemouse_commands(
                    state, self.args.deadzone
                )
                self.update_gripper(state.buttons)

            self.update_target(linear_command, angular_command, dt)
            self.publish_target()
            rate.sleep()

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Teleoperate the Franka Cartesian impedance controller "
        "directly with pyspacemouse."
    )
    parser.add_argument(
        "--linear-speed",
        type=float,
        default=0.12,
        help="Maximum Cartesian speed in m/s (default: 0.08).",
    )
    parser.add_argument(
        "--angular-speed",
        type=float,
        default=0.60,
        help="Maximum angular speed in rad/s (default: 0.60).",
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=200.0,
        help="Control-loop rate in Hz (default: 50).",
    )
    parser.add_argument(
        "--deadzone",
        type=float,
        default=0.05,
        help="Per-axis SpaceMouse deadzone in [0, 1) (default: 0.05).",
    )
    parser.add_argument(
        "--workspace",
        type=float,
        nargs=6,
        metavar=("X_MIN", "X_MAX", "Y_MIN", "Y_MAX", "Z_MIN", "Z_MAX"),
        default=DEFAULT_WORKSPACE,
        help="Cartesian workspace bounds in metres.",
    )
    parser.add_argument(
        "--max-attractor-distance",
        type=float,
        default=0.05,
        help="Maximum goal distance from the measured pose in m (default: 0.05).",
    )
    parser.add_argument(
        "--max-attractor-angle",
        type=float,
        default=0.35,
        help="Maximum goal angle from the measured pose in rad (default: 0.35).",
    )
    parser.add_argument(
        "--gripper-step",
        type=float,
        default=0.01,
        help="Width change per button press in m (default: 0.01).",
    )
    parser.add_argument("--gripper-min", type=float, default=0.0)
    parser.add_argument("--gripper-max", type=float, default=0.08)
    parser.add_argument(
        "--pose-timeout",
        type=float,
        default=10.0,
        help="Seconds to wait for /cartesian_pose (default: 10).",
    )
    parser.add_argument(
        "--translation-only",
        action="store_true",
        help="Ignore SpaceMouse rotation input and hold the initial orientation.",
    )
    parser.add_argument(
        "--set-stiffness",
        action="store_true",
        help="Apply the script's default stiffness values before teleoperating.",
    )

    args = parser.parse_args(rospy.myargv(argv=sys.argv)[1:])
    if args.linear_speed <= 0.0 or args.angular_speed <= 0.0:
        parser.error("Speeds must be positive.")
    if args.rate <= 0.0:
        parser.error("--rate must be positive.")
    if not 0.0 <= args.deadzone < 1.0:
        parser.error("--deadzone must be in [0, 1).")
    if args.max_attractor_distance <= 0.0:
        parser.error("--max-attractor-distance must be positive.")
    if not 0.0 < args.max_attractor_angle <= math.pi:
        parser.error("--max-attractor-angle must be in (0, pi].")
    if args.gripper_step <= 0.0:
        parser.error("--gripper-step must be positive.")
    if not 0.0 <= args.gripper_min < args.gripper_max:
        parser.error("Gripper limits must satisfy 0 <= min < max.")
    if args.pose_timeout <= 0.0:
        parser.error("--pose-timeout must be positive.")
    return args


def main() -> int:
    if pyspacemouse is None:
        print(
            "pyspacemouse is not installed. Install it with "
            "`python3 -m pip install pyspacemouse`.",
            file=sys.stderr,
        )
        return 2

    args = parse_args()
    rospy.init_node("franka_spacemouse_teleop")

    try:
        FrankaSpaceMouseTeleop(args).run()
    except (RuntimeError, ValueError) as error:
        rospy.logerr("%s", error)
        return 1
    except Exception as error:
        rospy.logerr(
            "SpaceMouse teleoperation failed: %s. Check device access/udev rules.",
            error,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
