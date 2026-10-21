#!/usr/bin/env bash
# Open one Terminator window whose panes are already inside Docker containers
# (Step 3 of docs/franka_exp_steps_to_follow.md). The ROS networking variables
# are passed into every container, so no manual exports are needed. Each pane
# can also start its own command, see PANES below.
#
# Usage:
#   scripts/launch_exp_terminals.sh
#
# Override any default below with an environment variable, e.g.:
#   CDP_IMAGE=my-cdp-image scripts/launch_exp_terminals.sh
#   DRY_RUN=1 scripts/launch_exp_terminals.sh   # print the docker commands only
set -euo pipefail
shopt -s extglob

export ROBOT_IMAGE=${ROBOT_IMAGE:-franka_robot_docker:v2}
export CDP_IMAGE=${CDP_IMAGE:-bd-coach-image-franka}
export CDP_PROJECT_DIR=${CDP_PROJECT_DIR:-$HOME/TUD_Projects/BD-COACH/Files}
export ROS_MASTER_URI=${ROS_MASTER_URI:-http://172.16.0.1:11311}
export ROS_IP=${ROS_IP:-172.16.0.68}
export ROS_HOSTNAME=${ROS_HOSTNAME:-$ROS_IP}
export DRY_RUN=${DRY_RUN:-0}

# One line per pane, top to bottom:  container | title | run | command
#   container: robot (ROBOT_IMAGE) or cdp (CDP_IMAGE)
#   run:       auto = run the command as soon as the container starts
#              up   = only put it in the shell history: press Up, then Enter
#   command:   may be empty, for a plain shell
# Ctrl+C stops an auto command and leaves you at the container prompt.
PANES=(
  "robot | spacemouse      | auto | spacenavd -v -d & roslaunch spacenav_node classic.launch"
  "robot | cameras         | auto | roslaunch realsense2_camera rs_multiple_devices.launch serial_no_camera1:=336222073305 serial_no_camera2:=317222075615"
  "robot | spacemouse test | up   | rostopic echo /spacenav/joy"
  "robot | spare           | up   | "
  "cdp   | camera images   | up   | conda run -n conda-env-CLIC --no-capture-output python env/realsense_Image_receiver.py"
  "cdp   | CDP main        | up   | conda run -n conda-env-CLIC --no-capture-output python main-kuka-cleaned.py --config-name train_CLIC_Diffusion_image_Ta8 hydra.run.dir='outputs/\${experiment_id}' GENERAL.Ta_executed=4"
)

SCRIPT_PATH=$(readlink -f "$0")
SCRIPT_DIR=$(dirname "$SCRIPT_PATH")

# Split PANES[$1] into the globals kind, title, run and cmd.
parse_pane() {
  local field
  IFS='|' read -r kind title run cmd <<<"${PANES[$1]}"
  for field in kind title run cmd; do
    printf -v "$field" '%s' "${!field##+([[:space:]])}"
    printf -v "$field" '%s' "${!field%%+([[:space:]])}"
  done
}

# Runs inside one Terminator pane: start a container, then fall back to a host
# shell when it exits so error messages stay visible.
run_pane() {
  parse_pane "$1"
  local docker=(docker)
  docker info >/dev/null 2>&1 || docker=(sudo docker)

  local args=(run -it --net=host
    --env NVIDIA_DRIVER_CAPABILITIES=all
    --env DISPLAY
    --env QT_X11_NO_MITSHM=1
    --env "ROS_MASTER_URI=$ROS_MASTER_URI"
    --env "ROS_IP=$ROS_IP"
    --env "ROS_HOSTNAME=$ROS_HOSTNAME"
    --env "PANE_CMD=$cmd"
    --env "PANE_AUTORUN=$([[ $run == auto ]] && echo 1 || echo 0)"
    --volume /tmp/.X11-unix:/tmp/.X11-unix:rw
    --volume "$SCRIPT_DIR/pane_rc.bash:/pane_rc.bash:ro")
  case $kind in
    robot)
      args+=(--privileged -v /dev:/dev "$ROBOT_IMAGE") ;;
    cdp)
      args+=(--gpus=all --add-host pandahandler:172.16.0.1
        --volume "$CDP_PROJECT_DIR/src:/app/:rw" "$CDP_IMAGE") ;;
    *)
      echo "Unknown container '$kind' in PANES (use robot or cdp)." >&2
      exec bash -i ;;
  esac
  args+=(bash --rcfile /pane_rc.bash)

  echo "+$(printf ' %q' "${docker[@]}" "${args[@]}")"
  if [[ $DRY_RUN != 1 ]]; then
    "${docker[@]}" "${args[@]}" || true
    echo "[$kind container exited, this is now a host shell]"
  fi
  exec bash -i
}

# Print a Terminator config with one layout: all PANES stacked vertically.
write_terminator_config() {
  local n=${#PANES[@]} i

  cat <<EOF
[global_config]
  suppress_multiple_term_dialog = True
[profiles]
  [[default]]
    cursor_color = "#aaaaaa"
[layouts]
  [[franka_exp]]
    [[[window0]]]
      type = Window
      parent = ""
      size = 750, 1175
EOF
  # Each VPaned holds one terminal on top and the rest of the stack below;
  # ratio = 1/remaining gives every pane the same height.
  local parent=window0 order=0
  for ((i = 1; i <= n; i++)); do
    parse_pane $((i - 1))
    if ((i < n)); then
      cat <<EOF
    [[[paned$i]]]
      type = VPaned
      parent = $parent
      order = $order
      ratio = $(awk "BEGIN { print 1 / ($n - $i + 1) }")
EOF
      parent=paned$i
      order=0
    fi
    cat <<EOF
    [[[term$i]]]
      type = Terminal
      parent = $parent
      order = $order
      profile = default
      title = "$kind: $title"
      command = "'$SCRIPT_PATH' --pane $((i - 1))"
EOF
    order=1
  done
}

if [[ ${1:-} == --pane ]]; then
  run_pane "$2"
fi

if ((${#PANES[@]} < 1)); then
  echo "Nothing to open: PANES is empty." >&2
  exit 1
fi
if printf '%s\n' "${PANES[@]}" | grep -q '^ *cdp ' && [[ ! -d $CDP_PROJECT_DIR/src ]]; then
  echo "CDP_PROJECT_DIR/src not found: $CDP_PROJECT_DIR/src" >&2
  echo "Set CDP_PROJECT_DIR to your CDP checkout, or remove the cdp panes." >&2
  exit 1
fi
if ! ip -4 -o addr show | grep -q " $ROS_IP/"; then
  echo "Warning: no network interface has $ROS_IP (see Step 2-1). Continuing anyway." >&2
fi

xhost +local:docker >/dev/null

config=${XDG_RUNTIME_DIR:-/tmp}/franka_exp_terminator.conf
write_terminator_config >"$config"
# --no-dbus forces a new Terminator instance that reads this config instead of
# handing the request to an already running window.
setsid terminator --no-dbus -g "$config" -l franka_exp >/dev/null 2>&1 &
echo "Opened Terminator with ${#PANES[@]} container panes."
