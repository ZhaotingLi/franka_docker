# Franka Experiment Notes

This file keeps personal experiment notes and one-off commands that are not part of the core `franka_docker` setup flow.

## ROS Networking Inside The Container

Connect the Ethernet cable to the Franka FR3 network first. The IP address assigned
to that Ethernet interface decides the values for `ROS_IP` and `ROS_HOSTNAME`.

To set the Ethernet IP on Ubuntu: open Settings -> Network, click `+` for the
wired connection, go to IPv4, choose Manual, then set the address to
`172.16.0.68` and Netmask to '255.255.255.0'.


```bash
export ROS_MASTER_URI=http://172.16.0.1:11311
export ROS_IP=172.16.0.68
export ROS_HOSTNAME=172.16.0.68
```


## Test franka gripper

```bash
rostopic pub -1 /franka_gripper/homing/goal franka_gripper/HomingActionGoal '{header: auto, goal_id: {stamp: now, id: ""}, goal: {}}'

rostopic pub -1 /franka_gripper/grasp/goal franka_gripper/GraspActionGoal '{header: auto, goal_id: {stamp: now, id: ""}, goal: {width: 0.0, epsilon: {inner: 0.005, outer: 0.005}, speed: 0.05, force: 20.0}}'
```


## Example External Commands

```bash
conda run -n conda-env-CLIC --no-capture-output python main-kuka-cleaned.py --config-name train_CLIC_Diffusion_image_Ta8 hydra.run.dir='outputs/${experiment_id}' GENERAL.Ta_executed=4
conda run -n conda-env-CLIC --no-capture-output python env/realsense_Image_receiver.py
```

## One Example Of Controlling The Robot

```bash
python3 python_franka/main_manually.py
```

## SpaceMouse

```bash
## used to remove the current process that use the space mouse
ls -l /dev/input/by-id/
sudo lsof /dev/input/event23

spacenavd -v -d &
roslaunch spacenav_node classic.launch
```

## RealSense

```bash
roslaunch realsense2_camera rs_camera.launch
roslaunch realsense2_camera rs_multiple_devices.launch serial_no_camera1:=045322075902 serial_no_camera2:=825312073923
sudo rm /var/log/uvcdynctrl-udev.log
```

## CDP Docker Commands

```bash
# Set this to the local checkout that contains dockerfile_CLIC_franka and src/.
CDP_PROJECT_DIR=/path/to/CDP/project
CDP_IMAGE_NAME=bd-coach-image-franka

# build the docker (not necessary if you pull it from the dockerhub)
cd "$CDP_PROJECT_DIR"
sudo docker build -t "$CDP_IMAGE_NAME" -f dockerfile_CLIC_franka .

# run the docker image
sudo docker run -it --gpus=all --net=host --env="NVIDIA_DRIVER_CAPABILITIES=all" --env="DISPLAY" --env="QT_X11_NO_MITSHM=1" --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" "$CDP_IMAGE_NAME" bash


# run with the local src/ directory mounted into /app/
sudo docker run -it   --gpus=all   --net=host   --env="NVIDIA_DRIVER_CAPABILITIES=all"   --env="DISPLAY"   --env="QT_X11_NO_MITSHM=1"   --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw"   --volume="$CDP_PROJECT_DIR/src:/app/:rw"   "$CDP_IMAGE_NAME" bash
```

## Docker Cleanup

```bash
sudo docker container prune
sudo docker image prune
sudo docker images -a | grep none | awk '{ print $3; }' | sudo xargs docker rmi --force
sudo docker system df
sudo docker builder prune
```

## Copy Files From Docker To Local

```bash
sudo docker ps
sudo docker cp d2eff0e71dc6:app/saved_data/kuka-push-BD-COACH-1027-1505 /home/zhaoting/Documents

sudo docker cp d5aa1c6eb768:app/outputs/ ~/outputs_franka/outputs/
sudo chmod -R a+w ~/outputs_franka/

sudo docker cp a1e084003c2b:app/outputs_docker/Camera\ 2_screenshot_27.11.2025.png ~/outputs_franka/outputs/
sudo chmod -R a+w ~/outputs_franka/

sudo docker cp f2b81da43982:/catkin_ros1_ws/src/relaxed_ik_ros1/relaxed_ik_core/trajectory_buffer_self_play0.hdf5 ~/outputs/

sudo docker cp e3df53de2978:/catkin_ros1_ws/src/relaxed_ik_ros1/relaxed_ik_core/saved_data/ ~/outputs/
sudo docker cp 5f4108b5428d:/catkin_ros1_ws/src/relaxed_ik_ros1/relaxed_ik_core/results/ /home/zhaoting/Documents/results

sudo chmod a+w <file_name>
sudo chmod -R a+w saved_data/
sudo chmod -R a+w ~/outputs_franka/
```
