0.git clone some files: 

git clone --recursive https://github.com/frankaemika/libfranka 

git clone --recursive https://github.com/frankaemika/franka_ros  

cd franka_ros/  

git clone https://github.com/franzesegiovanni/franka_human_friendly_controllers.git 

0.1 write the dockerfile, copy the above documents and  

1. [Error, boost_sml] 42.56 Errors << franka_gazebo:cmake /catkin_ws/logs/franka_gazebo/build.cmake.000.log 42.56 CMake Error at /opt/ros/noetic/share/catkin/cmake/catkinConfig.cmake:83 (find_package): 42.56 Could not find a package configuration file provided by "boost_sml" with 

1.1[solution] fixed by installing the missing dependences: sudo apt-get install ros-${ROS_DISTRO}-boost-sml 

https://github.com/PickNikRobotics/boost_sml 

2.go the libfranka directory, and use an older version of it 

1998  cd src/libfranka/ 

1999  git fetch --all --tags 

2000  git checkout 0.13.3 

 

 

[franka ros dockerfile] 

sudo docker build -t franka_robot_docker:v1 -f dockerfile_franka . 

sudo docker run -it --net=host --env="NVIDIA_DRIVER_CAPABILITIES=all" --env="DISPLAY" --env="QT_X11_NO_MITSHM=1" --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" --privileged -v /dev:/dev franka_robot_docker:v1 bash 

Inside the container, you can run some examples listed here: https://frankarobotics.github.io/docs/franka_ros.html#franka-gazebo  
