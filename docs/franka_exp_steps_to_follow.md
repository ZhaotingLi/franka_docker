# Franka Experiment Steps To Follow

Use this checklist when setting up the Franka FR3 experiment for CDP data
collection or execution.

## Prerequisites

Make sure the required Docker containers are available on your personal PC:

- Robot base Docker container. See the [Docker build and run guide](docker_build_and_run.md)
  for build and run instructions. You can also pull it directly from
  [Docker Hub](https://hub.docker.com/repository/docker/zhaoting123/franka_robot_docker/general).

  ```bash
  sudo docker pull zhaoting123/franka_robot_docker:latest
  ```

- CDP environment Docker container (reqired for runnning CDP code). You could build it following [CDP Docker Commands](franka_experiment_notes.md#cdp-docker-commands).

## Step 1: Start The Lab Desktop Side

1. Turn on the robot controller.
2. Turn on the robot PC.
3. Open the Franka webpage interface from the lab desktop.
4. In the webpage interface, go to the robot page,:
   - Click Joints -> Unlock.
   - Click Activate FCI.

### Step 1-1: Launch ROS On The Lab Computer

Run the required `roslaunch` command on the lab computer, you could refer to  [franak_human_friendly_controllers](https://github.com/franzesegiovanni/franka_human_friendly_controllers).

```bash
# TODO: fill in the lab computer roslaunch command.
```

## Step 2: Set Up Network Connections

Connect the network cable between the Franka setup and the computer that will run
the Docker containers. If you are using a personal laptop, connect the Ethernet
cable to that laptop.

### Step 2-1: Configure The Ethernet IP

The IP address assigned to the Ethernet interface decides the values for `ROS_IP`
and `ROS_HOSTNAME` inside the Docker containers.

On Ubuntu:

1. Open Settings -> Network.
2. Click `+` for the wired connection.
3. Go to IPv4.
4. Choose Manual.
5. Set Address to `172.16.0.68`.
6. Set Netmask to `255.255.255.0`.

Use the same IP inside every Docker container:

```bash
export ROS_MASTER_URI=http://172.16.0.1:11311
export ROS_IP=172.16.0.68
export ROS_HOSTNAME=172.16.0.68
```

## Step 3: Start Docker Containers On Your PC

Open four terminals first. A multi-terminal layout is highly recommended; for
example, see the
[Terminator setup notes](https://innovativeinnovation.github.io/ubuntu-setup/terminals/terminator.html).

In one terminal, run this command outside the Docker container first:

```bash
xhost +local:docker
```

Then, in each terminal, run the Docker command to open one container. See
[CDP Docker Commands](franka_experiment_notes.md#cdp-docker-commands) for the
current Docker build and run commands:

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


 After each container starts, run the ROS
networking exports inside that container:

```bash
export ROS_MASTER_URI=http://172.16.0.1:11311
export ROS_IP=172.16.0.68
export ROS_HOSTNAME=172.16.0.68
```



### Step 3-2: Connect The SpaceMouse

Use one terminal for the SpaceMouse.

```bash
# if the space mouse is occupied by other process, use the following commands to find that process, then stop that process. 
ls -l /dev/input/by-id/
sudo lsof /dev/input/event23

# launch space mouse
spacenavd -v -d &
roslaunch spacenav_node classic.launch
```

On another container, you could test if the spacemouse works by 
```bash
rostopic echo /spacenav/joy
```

### Step 3-3: Connect The Cameras

Use a second terminal for the RealSense cameras.

First, launch one camera and check the serial number printed as
`Device Serial No: ...`.

```bash
roslaunch realsense2_camera rs_camera.launch
```

Then launch both cameras with their serial numbers:

```bash
roslaunch realsense2_camera rs_multiple_devices.launch serial_no_camera1:=336222073305 serial_no_camera2:=825312073923
```

Check that the images can be received (should use a CDP env container):

```bash
conda run -n conda-env-CLIC --no-capture-output python env/realsense_Image_receiver.py
```

## Step 4: Run The CDP Main Code with a CDP env container

Use another terminal to run the CDP container, see
[CDP Docker Commands](franka_experiment_notes.md#cdp-docker-commands). for the CDP main script:

```bash
conda run -n conda-env-CLIC --no-capture-output python main-kuka-cleaned.py --config-name train_CLIC_Diffusion_image_Ta8 hydra.run.dir='outputs/${experiment_id}' GENERAL.Ta_executed=4
```

## Step 5: Save Collected Data

If you are doing data collection, including offline demonstrations or online
corrections, save the collected data under:

```text
outputs/${experiment_id}
```

### Step 5-2: View Collected Data

Use the CDP visualization script:

```bash
python script/visualize_traj_buffer_data_and_manual_label.py
```

Before running the script, adjust the data path inside the script to point to the
collected trajectory buffer.
