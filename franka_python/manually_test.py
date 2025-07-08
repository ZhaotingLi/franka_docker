import rospy
import numpy as np
import time
import os

from geometry_msgs.msg import PoseStamped, Pose
from pynput.keyboard import Listener, KeyCode, Key
from pose_transform_functions import  array_quat_2_pose, list_2_quaternion, position_2_array, transform_pose
from panda import Panda

class Test(Panda):

    def __init__(self):
        rospy.init_node("learning_node")
        super(Test, self).__init__()
        self.r=rospy.Rate(20)
        self.pose = Pose()
        self.recorded_traj = None 
        self.recorded_ori=None
        self.recorded_gripper= None
        self.end=False
        self.attractor_distance_threshold=0.05 # If the attractor is larger than the treshold, the robot will wait
        self.max_gripper_force= 2

        self.gripper_close_width = 0
        self.gripper_open_width  = 0.06
        self.gripper_sensitivity= 0.03

        self.listener = Listener(on_press=self._on_press)
        self.listener.start()

    
    
    def _on_press(self, key):
        # This function runs on the background and checks if a keyboard key was pressed
        if key == Key.esc:
            self.end = True

    def execute(self):
        self.set_stiffness(1000, 1000, 1000, 30, 30, 30, 0)
        start = PoseStamped()
        curr_position = self.curr_pos
        print(f"Current position: {curr_position}")

        self.home()

        curr_position = self.curr_pos
        print(f"Current position: {curr_position} with orietation {self.curr_ori}")

        goal_orie = np.quaternion(0, 1, 0, 0)
        goal_pos = curr_position
        goal_pos[0] = goal_pos[0] + 0.05
        print(goal_pos)
        goal = array_quat_2_pose(goal_pos, goal_orie)
        goal.header.seq=1
        goal.header.stamp = rospy.Time.now()

        self.go_to_pose(goal)

        goal_pos[1] = goal_pos[1] + 0.05
        print(goal_pos)
        goal = array_quat_2_pose(goal_pos, goal_orie)
        goal.header.seq=1
        goal.header.stamp = rospy.Time.now()

        self.go_to_pose(goal)

        goal_pos[2] = goal_pos[2] + 0.05
        print(goal_pos)
        goal = array_quat_2_pose(goal_pos, goal_orie)
        goal.header.seq=1
        goal.header.stamp = rospy.Time.now()

        self.go_to_pose(goal)

        # self.time_index=0
        # while self.time_index <( self.recorded_traj.shape[1]):

        #     quat_goal = list_2_quaternion(self.recorded_ori[:, self.time_index])
        #     goal = array_quat_2_pose(self.recorded_traj[:, self.time_index], quat_goal)
        #     goal.header.seq = 1
        #     goal.header.stamp = rospy.Time.now()

                   
        #     if (self.recorded_gripper[0][self.time_index]-self.recorded_gripper[0][max([0,self.time_index-1])]) < -self.gripper_sensitivity:
        #         print("closing gripper")
        #         self.grasp_gripper(self.recorded_gripper[0][self.time_index], self.max_gripper_force)
        #         time.sleep(0.1)

        #     if (self.recorded_gripper[0][self.time_index]-self.recorded_gripper[0][max([0,self.time_index-1])]) > self.gripper_sensitivity:
        #         print("open gripper")
        #         self.move_gripper(self.recorded_gripper[0][self.time_index])
        #         time.sleep(0.1)

        #     self.goal_pub.publish(goal)

        #     # Safety feature in case somebody is touching the robot during execution
        #     goal_pos_array = position_2_array(goal.pose.position)
        #     if np.linalg.norm(self.curr_pos-goal_pos_array) <= self.attractor_distance_threshold:
        #         self.time_index=self.time_index+1
        #     self.r.sleep()