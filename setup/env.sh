# Sourced by the setup scripts. Override any of these before sourcing.
export DEMO="${DEMO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
export OPENRUN_HOME="$DEMO/.server"
export CL_CONFIG_FILE="$OPENRUN_HOME/openrun.toml"
export DEMO_HTTP_PORT="${DEMO_HTTP_PORT:-25940}"
export DEMO_HTTPS_PORT="${DEMO_HTTPS_PORT:-25942}"
export DEMO_PG_PORT="${DEMO_PG_PORT:-25941}"
export DEMO_PG_NAME="${DEMO_PG_NAME:-demo-pg}"
export DEMO_PG_PASSWORD="${DEMO_PG_PASSWORD:-demo-pg-pw}"
# Demo users are <name>:<name>$DEMO_PW_SUFFIX, on a server bound to localhost
export DEMO_PW_SUFFIX="${DEMO_PW_SUFFIX:--demo-pw}"
# OPENRUN_BIN_DIR: directory holding the openrun binary, when it is not on PATH
[ -n "$OPENRUN_BIN_DIR" ] && export PATH="$OPENRUN_BIN_DIR:$PATH"
true
