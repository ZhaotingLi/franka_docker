### 0.git clone some files: 

cd franka_docker/src/

git clone --recursive https://github.com/frankaemika/libfranka 

git clone --recursive https://github.com/frankaemika/franka_ros  

#cd franka_ros/  

git clone https://github.com/franzesegiovanni/franka_human_friendly_controllers.git 

cd src/libfranka/ 

git fetch --all --tags 

git checkout 0.13.3 
 

 [To do] check the version of libfranka on pandas (for fr3, version>=0.15)
 

### build franka ros dockerfile 

cd /home/zhaoting/ros_docker_packages/franka_docker
sudo docker build -t franka_robot_docker:v2 -f dockerfile_franka . 


### Run franka-ros docker container
sudo docker run -it --net=host --env="NVIDIA_DRIVER_CAPABILITIES=all" --env="DISPLAY" --env="QT_X11_NO_MITSHM=1" --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" --privileged -v /dev:/dev franka_robot_docker:v2 bash 

Inside the container, you can run some examples listed here: https://frankarobotics.github.io/docs/franka_ros.html#franka-gazebo  

####Possible issues

0.1 write the dockerfile, copy the above documents and  

1. [Error, boost_sml] 42.56 Errors << franka_gazebo:cmake /catkin_ws/logs/franka_gazebo/build.cmake.000.log 42.56 CMake Error at /opt/ros/noetic/share/catkin/cmake/catkinConfig.cmake:83 (find_package): 42.56 Could not find a package configuration file provided by "boost_sml" with 

1.1[solution] fixed by installing the missing dependences: sudo apt-get install ros-${ROS_DISTRO}-boost-sml 

https://github.com/PickNikRobotics/boost_sml 

2.go the libfranka directory, and use an older version of it 

1998  cd src/libfranka/ 

1999  git fetch --all --tags 

2000  git checkout 0.13.3 



xhost +local:docker
#### INside the docker container


export ROS_MASTER_URI=http://172.16.0.1:11311
export ROS_IP=172.16.0.68
export ROS_HOSTNAME=172.16.0.68

conda run -n conda-env-CLIC --no-capture-output python main-kuka-cleaned.py --config-name train_CLIC_Diffusion_image_Ta8 hydra.run.dir='outputs/${experiment_id}' GENERAL.Ta_executed=4

conda run -n conda-env-CLIC --no-capture-output python env/realsense_Image_receiver.py

### One example of controlling the robot 

python3 python_franka/main_manually.py  


### space mouse
ls -l /dev/input/by-id/
sudo lsof /dev/input/event23
spacenavd -v -d &
roslaunch spacenav_node classic.launch

### Realsense
roslaunch realsense2_camera rs_camera.launch  # use this command this find the serial number of each camera
roslaunch realsense2_camera rs_multiple_devices.launch serial_no_camera1:=045322075902 serial_no_camera2:=825312073923
 
sudo rm /var/log/uvcdynctrl-udev.log  ### remove cache
 


#### Docker build BD-COACH 
cd /home/zhaoting/TUD_Projects/BD-COACH/Files
sudo docker build -t bd-coach-image-franka -f dockerfile_CLIC_franka .

### Docker run BD-COACH with GPU
sudo docker run -it --gpus=all --net=host --env="NVIDIA_DRIVER_CAPABILITIES=all" --env="DISPLAY" --env="QT_X11_NO_MITSHM=1" --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" bd-coach-image-franka bash 

### Delete non-used docker images
sudo docker container prune 
sudo docker image prune
sudo docker images -a | grep none | awk '{ print $3; }' | sudo xargs docker rmi –force

sudo docker system df    # check the docker memory usage
sudo docker builder prune # remove unused cache

 ### Copy files from docker into local
sudo docker ps
sudo docker cp d2eff0e71dc6:app/saved_data/kuka-push-BD-COACH-1027-1505  /home/zhaoting/Documents 

sudo docker cp d5aa1c6eb768:app/outputs/ ~/outputs_franka/outputs/
sudo chmod -R a+w ~/outputs_franka/

sudo docker cp a1e084003c2b:app/outputs_docker/Camera\ 2_screenshot_27.11.2025.png ~/outputs_franka/outputs/
sudo chmod -R a+w ~/outputs_franka/

sudo docker cp f2b81da43982:/catkin_ros1_ws/src/relaxed_ik_ros1/relaxed_ik_core/trajectory_buffer_self_play0.hdf5 ~/outputs/

sudo docker cp e3df53de2978:/catkin_ros1_ws/src/relaxed_ik_ros1/relaxed_ik_core/saved_data/ ~/outputs/
sudo docker cp 5f4108b5428d:/catkin_ros1_ws/src/relaxed_ik_ros1/relaxed_ik_core/results/ /home/zhaoting/Documents/results

sudo chmod a+w <file_name>  # change the file permissions
sudo chmod -R a+w saved_data/
sudo chmod -R a+w ~/outputs_franka/