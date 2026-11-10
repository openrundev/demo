#!/bin/bash
# Removes everything setup.sh and the demo created. Add --purge to delete .server/ too.
. "$(dirname "$0")/env.sh"
(cd "$DEMO" && openrun delete platform.star)
openrun server stop
docker rm -f "$DEMO_PG_NAME"
[ "${1:-}" = "--purge" ] && rm -rf "$OPENRUN_HOME"
true
