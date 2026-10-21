# Startup file for the container shells opened by launch_exp_terminals.sh.
# It is mounted into each container and used as `bash --rcfile`.
source ~/.bashrc

if [[ -n ${PANE_CMD:-} ]]; then
  # Add the command to the history file before bash loads it, so Up recalls it.
  printf '%s\n' "$PANE_CMD" >>"${HISTFILE:-$HOME/.bash_history}"
  if [[ ${PANE_AUTORUN:-0} == 1 ]]; then
    echo "+ $PANE_CMD"
    eval "$PANE_CMD"
  else
    echo "Press Up then Enter to run: $PANE_CMD"
  fi
fi
