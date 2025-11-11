#!/usr/bin/env python
"""
Authors:
    Original KUKA Spacenav:
        Rodrigo Perez-Dattari <r.j.perezdattari@tudelft.nl>
    Panda adaptation:
        <your name>
"""

import rospy
import numpy as np
import sensor_msgs.msg as sensor_msg
import quaternion  # numpy-quaternion

from geometry_msgs.msg import PoseStamped
from pose_transform_functions import array_quat_2_pose

# adjust this import to where your Panda class is defined
# from env.panda.panda_interface import Panda
from panda import Panda


class PandaSpacenav:
    def __init__(self):
        # Low-level Panda interface
        self.robot = Panda()

        # SpaceMouse subscriber
        rospy.Subscriber(
            "/spacenav/joy",
            sensor_msg.Joy,
            self._callback_spacenav,
            queue_size=10,
        )

        # Internal state
        self.spacenav_state = None
        self.store_data = False  # kept from original interface in case you use it

        # Control parameters
        self.control_orientation = True  # start with position-only control
        self.scale = 0.05  # same scale as original Spacenav (tune if needed)

        # Keep a fixed "downward" orientation (same as Panda.home())
        # Panda.home uses quat = np.quaternion(0, 1, 0, 0)
        self.orientation_goal_quat = np.quaternion(0, 1, 0, 0)

        # Simple workspace limits: [x_low, x_high, y_low, y_high, z_low, z_high]
        # !!! Tune these to your setup to avoid collisions !!!
        self.ee_pos_limit_xyz = [0.3, 0.8, -0.4, 0.4, 0.05, 0.5]

        # For keeping z around a comfortable constant height
        self.position_goal_z = 0.125

    # ==================== Callbacks ====================

    def _callback_spacenav(self, data):
        self.spacenav_state = data.axes
        if data.buttons[0] and data.buttons[1]:
            self.store_data = True

    # ==================== Helper methods ====================

    def _apply_workspace_limits(self, pos):
        """
        Clamp desired position into safe workspace bounds.
        pos: np.array(3,)
        """
        pos_clamped = pos.copy()
        # x
        pos_clamped[0] = max(
            self.ee_pos_limit_xyz[0],
            min(pos_clamped[0], self.ee_pos_limit_xyz[1]),
        )
        # y
        pos_clamped[1] = max(
            self.ee_pos_limit_xyz[2],
            min(pos_clamped[1], self.ee_pos_limit_xyz[3]),
        )
        # z
        pos_clamped[2] = max(
            self.ee_pos_limit_xyz[4],
            min(pos_clamped[2], self.ee_pos_limit_xyz[5]),
        )
        return pos_clamped

    # ==================== Core control loop ====================

    def run(self):
        """
        One control step:
        - read current Panda ee pose
        - read SpaceMouse state
        - compute desired ee pose
        - publish equilibrium pose
        """
        # Need Panda pose AND spacenav state
        if self.robot.curr_pos is None or self.robot.curr_ori is None:
            # Robot not ready yet
            return False
        if self.spacenav_state is None:
            # No SpaceMouse input yet
            return False

        # Current pose
        ee_position = np.array(self.robot.curr_pos).copy()  # [x, y, z]
        # Orientation stored in Panda as [w, x, y, z]
        curr_quat = np.quaternion(
            self.robot.curr_ori[0],
            self.robot.curr_ori[1],
            self.robot.curr_ori[2],
            self.robot.curr_ori[3],
        )

        # === Position control ===
        spacenav_arr = np.array(self.spacenav_state, dtype=np.float32)
        ee_delta_position = spacenav_arr[:3] * self.scale

        # Keep z around target if we don't want to directly control it
        #if not self.control_orientation:
            # Use only x,y from spacenav; z controlled towards position_goal_z
           # ee_delta_position[2] = (self.position_goal_z - ee_position[2]) / self.scale

        ee_goal_position = ee_position + ee_delta_position
        ee_goal_position = self._apply_workspace_limits(ee_goal_position)

        # === Orientation control ===
        if self.control_orientation:
            # If you want to use orientation from SpaceMouse, you can implement
            # something similar to the KUKA version using SO3 here.
            #
            # For now, let’s just keep the current orientation and you can
            # replace this block later:
            ee_goal_quat = curr_quat
        else:
            # Keep fixed downward orientation
            ee_goal_quat = self.orientation_goal_quat
	
	print("ee_goal_position: ", ee_goal_position)
        # === Publish equilibrium pose ===
        goal = array_quat_2_pose(ee_goal_position, ee_goal_quat)
        goal.header.seq = 1
        goal.header.stamp = rospy.Time.now()
        self.robot.goal_pub.publish(goal)

        return True


if __name__ == "__main__":
    rospy.init_node("panda_spacenav")
    control_frequency = 500
    rate = rospy.Rate(control_frequency)
    control = PandaSpacenav()

    rospy.sleep(0.1)  # give things a moment to connect

    while not rospy.is_shutdown():
        try:
            control.run()
        except rospy.ROSInterruptException:
            pass
        rate.sleep()

