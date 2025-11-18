#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on July 6 2022

@author: Giovanni Franzese, Cognitive Robotics, TU Delft
Run this node in a terminal. 
Remember to run the spacenav launch file 
$ roslaunch spacenav_node classic.launch 
and to install the space nav before with 
$ sudo apt install spacenavd
$ sudo apt install ros-indigo-spacenav-node
"""

import rospy
import numpy as np
import quaternion # pip install numpy-quaternion
from quaternion import from_euler_angles
from sensor_msgs.msg import JointState
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Float32MultiArray, Float32
from sensor_msgs.msg import Joy
from pynput.keyboard import Listener, KeyCode
# from scipy.spatial.transform import Rotation
from panda import Panda
import threading

def get_quaternion_from_euler(roll, pitch, yaw):
  """
  Convert an Euler angle to a quaternion.
   
  Input
    :param roll: The roll (rotation around x-axis) angle in radians.
    :param pitch: The pitch (rotation around y-axis) angle in radians.
    :param yaw: The yaw (rotation around z-axis) angle in radians.
 
  Output
    :return qx, qy, qz, qw: The orientation in quaternion [x,y,z,w] format
  """
  qx = np.sin(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) - np.cos(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
  qy = np.cos(roll/2) * np.sin(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.cos(pitch/2) * np.sin(yaw/2)
  qz = np.cos(roll/2) * np.cos(pitch/2) * np.sin(yaw/2) - np.sin(roll/2) * np.sin(pitch/2) * np.cos(yaw/2)
  qw = np.cos(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
 
  return [ qw ,qx, qy, qz]

class Teleoperation(Panda):
    def __init__(self):
        rospy.init_node('Teleoperation', anonymous=True)
        super(Teleoperation, self).__init__()
        self.control_freq=rospy.Rate(100)
        self.offset = [0, 0, 0, 0, 0, 0]
        # self.offset_gripper = [0, 0]
        self.offset_gripper = 0.0
        self.curr_pos = None
        self.joint_pos = None
        self.joy_sub=rospy.Subscriber("/spacenav/joy", Joy, self.spacenav_callback)

        self.pos_scale = 0.0025
        self.ori_scale = 0.0025
        # TODO Range of gripper is 
        self.gripper_scale = 0.01 

        # self.pos_sub=rospy.Subscriber("/cartesian_pose", PoseStamped, self.ee_pos_callback)
        # self.goal_pub = rospy.Publisher('/equilibrium_pose', PoseStamped, queue_size=0)  
        # TODO not sure why this needs to be reinitialize again here as a real value
        self.curr_pos = np.array([0.5, 0, 0.5])
        self.curr_ori = np.array([1, 0, 0, 0])
        # self.curr_grip_width = 0.0

         # Starting the listener
         # NEW: keyboard-based world-Z rotation
        self.rot_command = 0          # -1, 0, +1
        self.rot_step = 0.01          # radians per control step

        self.hand_command = 0
        listener_thread = threading.Thread(target=self.start_listener)
        listener_thread.start()
    
    def start_listener(self):
        # This function will run the listener in the background
        with Listener(on_press=self.key_press, on_release=self.key_release) as listener:
            listener.join()

        rospy.sleep(1)

    def key_press(self, k):
        if hasattr(k, 'char'):  # Check if the key has 'char' attribute
            ch = k.char.lower()
            print(f'alphanumeric key {ch} pressed')
            if ch == 'o':
                self.hand_command = 1
                self.send_fixed_commands = False
                self.reduce_velocity = False
            elif ch == 'c':
                self.hand_command = -1
            # NEW: rotation commands
            elif ch == 'r':      # rotate +z in world
                self.rot_command = 1
            elif ch == 't':      # rotate -z in world
                self.rot_command = -1

    def key_release(self, k):
        if hasattr(k, 'char'):
            ch = k.char.lower()
            if ch in ('o', 'c'):
                self.hand_command = 0
            # NEW: stop rotating when R/T is released
            if ch in ('r', 't'):
                self.rot_command = 0

    def spacenav_callback(self, data):
        self.offset[0]= self.pos_scale*data.axes[0]
        self.offset[1]= self.pos_scale*data.axes[1]
        self.offset[2]= self.pos_scale*data.axes[2]
        self.offset[3]= self.ori_scale*data.axes[3]
        self.offset[4]= self.ori_scale*data.axes[4] 
        self.offset[5]= self.ori_scale*data.axes[5]

        self.offset_gripper = self.gripper_scale * self.hand_command
       
  
    def spacenav(self):
        # robot = rtb.models.DH.Panda()
        # local_pos = curr_pos.reshape(1, 3)
        # x_new = local_pos[0][0]
        # y_new = local_pos[0][1]
        # z_new = local_pos[0][2]
        # joint=self.curr_orijoint_pos[0:7].reshape(1, -1)
        # fw_pose = robot.fkine(joint)
        # goal_ori = fw_pose.R
        # rot = Rotation.from_quat(self.curr_ori)
        # goal_ori_eul = rot.as_euler('xyz')
        goal = PoseStamped()
        goal.header.seq = 1
        goal.header.stamp = rospy.Time.now()
        goal.header.frame_id = "map"

        goal.pose.position.x =  self.curr_pos[0]
        goal.pose.position.y =  self.curr_pos[1]
        goal.pose.position.z =  self.curr_pos[2]
            #print("quat", quat) 
        goal.pose.orientation.w = self.curr_ori[0]    
        goal.pose.orientation.x = self.curr_ori[1] 
        goal.pose.orientation.y = self.curr_ori[2] 
        goal.pose.orientation.z = self.curr_ori[3] 
        self.goal_pub.publish(goal)  
        quat_goal=np.quaternion(self.curr_ori[0],self.curr_ori[1],self.curr_ori[2],self.curr_ori[3])

        goal_grip = self.curr_grip_width   

        while not rospy.is_shutdown(): 
            
            # Update position values 
            goal.pose.position.x = goal.pose.position.x + self.offset[0]
            goal.pose.position.y = goal.pose.position.y + self.offset[1]
            goal.pose.position.z = goal.pose.position.z + self.offset[2]
            #alpha_beta_gamma=np.array([self.offset[3], self.offset[4], self.offset[5]])
            #q_delta=from_euler_angles(alpha_beta_gamma) 
            q_delta_array=get_quaternion_from_euler(self.offset[3], self.offset[4], self.offset[5])
            q_delta=np.quaternion(q_delta_array[0],q_delta_array[1],q_delta_array[2],q_delta_array[3]) 
            quat_goal=q_delta*quat_goal

            # NEW: keyboard-based rotation around WORLD z-axis
            if self.rot_command != 0:
                yaw = self.rot_command * self.rot_step  # + or - about world z
                print("yaw: ", yaw)
                qz_array = get_quaternion_from_euler(0.0, 0.0, yaw)
                qz_delta = np.quaternion(qz_array[0], qz_array[1], qz_array[2], qz_array[3])
                quat_goal = qz_delta * quat_goal        # left-multiply = world-frame z-rot

            # Update orientation values 
            goal.pose.orientation.w = quat_goal.w   
            goal.pose.orientation.x = quat_goal.x
            goal.pose.orientation.y = quat_goal.y
            goal.pose.orientation.z = quat_goal.z
             
            # Update gripper values 

            goal_grip = goal_grip + self.offset_gripper
            goal_grip = np.maximum(np.minimum(goal_grip, 0.1), -0.02)
            self.offset_gripper = 0.0
            print("New gripper goal = ", goal_grip)
    
            self.goal_pub.publish(goal)            
            self.move_gripper(goal_grip)
        
            self.control_freq.sleep()
        
    
#%%    
if __name__ == '__main__':
    rospy.init_node('Teleoperation', anonymous=True)

#%%
    teleoperation=Teleoperation()
    rospy.sleep(2)
    teleoperation.spacenav()
