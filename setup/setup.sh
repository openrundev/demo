#!/bin/bash
# Creates the demo server from nothing: a server home in .server/, a Postgres
# container, three users, the grants in rbac.json and an MCP key per agent.
# It does not create any app: that is what `openrun apply platform.star` is for.
set -euo pipefail
. "$(dirname "$0")/env.sh"

mkdir -p "$OPENRUN_HOME/keys" "$OPENRUN_HOME/config"
# A build from a source checkout has no app specs next to it: link them in
if [ -n "${OPENRUN_SRC:-}" ]; then ln -sfn "$OPENRUN_SRC/config/appspecs" "$OPENRUN_HOME/config/appspecs"; fi

cat > "$CL_CONFIG_FILE" <<EOF
[security]
app_default_auth_type = "builtin"   # every app requires a login unless it says otherwise
allowed_exec_commands = ["$DEMO/svc/restart.sh"]

[http]
port = $DEMO_HTTP_PORT

[https]
host = "127.0.0.1"
port = $DEMO_HTTPS_PORT

[api.mcp]
enable = true                        # serve actions to AI agents as MCP tools

[system]
container_command = "auto"

[node_config]
demo_src = "$DEMO"                   # local checkout; platform.star defaults to the GitHub path
ops_dir = "$DEMO/svc"                # where restart.sh lives on this server
EOF

# Postgres for the tasks apps. App containers reach it through the host's LAN
# address, so it listens there as well as on loopback.
HOST_IP="${DEMO_HOST_IP:-$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')}"
docker rm -f "$DEMO_PG_NAME" >/dev/null 2>&1 || true
docker run -d --name "$DEMO_PG_NAME" -e POSTGRES_PASSWORD="$DEMO_PG_PASSWORD" -e POSTGRES_DB=apps \
  -p "127.0.0.1:$DEMO_PG_PORT:5432" ${HOST_IP:+-p "$HOST_IP:$DEMO_PG_PORT:5432"} postgres:17-alpine >/dev/null

nohup openrun server start > "$OPENRUN_HOME/server.log" 2>&1 &
for i in $(seq 1 30); do openrun server version >/dev/null 2>&1 && break; sleep 1; done
for i in $(seq 1 30); do docker exec "$DEMO_PG_NAME" pg_isready -U postgres >/dev/null 2>&1 && break; sleep 1; done

openrun service create postgres/main \
  --config "url=postgres://postgres:$DEMO_PG_PASSWORD@127.0.0.1:$DEMO_PG_PORT/apps?sslmode=disable"

openrun user add alice --groups eng --value "alice$DEMO_PW_SUFFIX"
openrun user add bob --groups ops --value "bob$DEMO_PW_SUFFIX"
openrun user add carol --groups support --value "carol$DEMO_PW_SUFFIX"

# The grants. update-config replaces the whole document and wants the current version id.
VER=$(openrun server show-config | python3 -c 'import json,sys; print(json.load(sys.stdin)["version_id"])')
sed "s/\"version_id\": \".*\"/\"version_id\": \"$VER\"/" "$DEMO/rbac.json" > "$OPENRUN_HOME/rbac.json"
openrun server update-config "$OPENRUN_HOME/rbac.json"

# One MCP key per agent, each acting as its user
for u in bob carol; do
  openrun apikey create --user "builtin:$u" --resource app_mcp:builtin --scopes app:access \
    --desc "$u's agent" > "$OPENRUN_HOME/keys/$u.txt" 2>&1
done
echo "Server is up at https://localhost:$DEMO_HTTPS_PORT. Next: openrun apply --approve --promote platform.star"
