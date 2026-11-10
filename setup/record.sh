#!/bin/bash
# The whole recording, in story order. Needs the server from setup.sh and no apps on it.
# Takes about ten minutes; most of it is waiting for idle apps to stop.
cd "$(dirname "$0")" && . ./env.sh
mkdir -p cap/shots
set -x
python3 capture.py part1 stage > cap/run1.log 2>&1 || exit 1
node shots.cjs > cap/shots.log 2>&1 || exit 1
python3 capture.py promote idle destroy audit > cap/run2.log 2>&1 || exit 1
python3 capture.py unstage   # the handbook edit was only for the recording
echo DONE
