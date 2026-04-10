# franka_docker

`franka_docker` is a Dockerized ROS Noetic workspace for building and running Franka software with the packages already included in this repository.

It is also intended to serve as a base image for a CDP container, where ROS-Python commands are sent to a Franka ROS controller running in this environment.

It is meant to help you:

- build `libfranka` and `franka_ros` inside a container
- launch a controller that can connect to a real Franka robot through FCI
- run the included Python helper scripts for simple robot commands

## What Is In This Repo

- `dockerfile_franka`: Docker image definition
- `src/libfranka`: Franka C++ library source
- `src/franka_ros`: ROS integration for Franka
- `src/franka_human_friendly_controllers`: custom controllers used in this workspace
- `franka_python`: Python scripts that publish commands to the controller

The Docker build copies the checked-in sources directly from this repository, so you do not need to clone those dependencies again before building.

## Prerequisites

Before using this repo, make sure you have:

- Docker installed on the host
- a host machine that can reach the robot over the network
- Franka FCI enabled on the robot
- X11 forwarding available if you want to use `rviz` or `rqt_reconfigure`
- the base image `turtlebot3_base:latest` available locally, because [`dockerfile_franka`](/home/zhaoting/ros_docker_packages/franka_docker/dockerfile_franka) starts from that image

If your setup does not have `turtlebot3_base:latest`, update [`dockerfile_franka`](/home/zhaoting/ros_docker_packages/franka_docker/dockerfile_franka) to use a suitable ROS Noetic base image or build that base image first.

## What The Docker Image Builds

The image defined in [`dockerfile_franka`](/home/zhaoting/ros_docker_packages/franka_docker/dockerfile_franka) does the following:

- builds `libfranka` from `src/libfranka`
- creates `/catkin_ws` and builds `franka_ros`
- includes `franka_human_friendly_controllers` in the workspace
- installs useful runtime packages such as `spacenav` and `realsense2_camera`
- copies the Python helper scripts into `/catkin_ws/python_franka`

## Build The Docker Image

From the repository root:

```bash
cd /home/zhaoting/ros_docker_packages/franka_docker
sudo docker build -t franka_robot_docker:v2 -f dockerfile_franka .
```

If the build fails because of Franka package compatibility, check the versions currently present in `src/libfranka` and `src/franka_ros` and compare them with the official Franka compatibility documentation.

## Run The Container

If you want GUI tools from the container to open on the host, allow local Docker access to X11 first:

```bash
xhost +local:docker
```

Then start the container:

```bash
sudo docker run -it \
  --net=host \
  --env="NVIDIA_DRIVER_CAPABILITIES=all" \
  --env="DISPLAY" \
  --env="QT_X11_NO_MITSHM=1" \
  --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" \
  --privileged \
  -v /dev:/dev \
  franka_robot_docker:v2 bash
```

The container starts in `/catkin_ws`, and the ROS environment is added to `~/.bashrc`.

## Start A Franka Controller

Inside the container, launch the custom Cartesian impedance controller and point it to the robot IP:

For Panda:

```bash
roslaunch franka_human_friendly_controllers cartesian_variable_impedance_controller.launch \
  robot_ip:=<ROBOT_IP> \
  load_gripper:=true \
  arm_id:=panda
```

For FR3:

```bash
roslaunch franka_human_friendly_controllers cartesian_variable_impedance_controller.launch \
  robot_ip:=<ROBOT_IP> \
  load_gripper:=true \
  arm_id:=fr3
```

This launch file starts:

- the Franka control node
- the gripper node when `load_gripper:=true`
- the custom impedance controller
- `rviz` and `rqt_reconfigure`

## Run A Simple Python Control Example

Once the controller is running, open another shell in the same container and run:

```bash
python3 python_franka/main_manually.py
```

This script publishes pose commands to `/equilibrium_pose`, so it only works after the controller above is already active.

## Notes

- The Python helper scripts assume the ROS topics exposed by `franka_human_friendly_controllers`.
- If you want to use a calibrated model, see the launch options described in [`src/franka_human_friendly_controllers/README.md`](/home/zhaoting/ros_docker_packages/franka_docker/src/franka_human_friendly_controllers/README.md).
- Older ad hoc experiment commands that were previously mixed into this README are now collected in [`docs/franka_experiment_notes.md`](/home/zhaoting/ros_docker_packages/franka_docker/docs/franka_experiment_notes.md).
