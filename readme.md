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
- `docs`: experiment setup notes and step-by-step run instructions

## Documentation

- [Docker build and run guide](docs/docker_build_and_run.md)
- [Franka experiment steps](docs/franka_exp_steps_to_follow.md)
- [Franka experiment notes](docs/franka_experiment_notes.md)

## Notes

- The Python helper scripts assume the ROS topics exposed by `franka_human_friendly_controllers`.
- If you want to use a calibrated model, see the launch options described in [`src/franka_human_friendly_controllers/README.md`](/home/zhaoting/ros_docker_packages/franka_docker/src/franka_human_friendly_controllers/README.md).
- Older ad hoc experiment commands that were previously mixed into this README are now collected in [`docs/franka_experiment_notes.md`](/home/zhaoting/ros_docker_packages/franka_docker/docs/franka_experiment_notes.md).
