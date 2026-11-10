#!/bin/sh
# Stand-in for a real rolling restart: logs what one would do
svc=$1; env=$2; n=$3
i=1
while [ "$i" -le "$n" ]; do
  echo "[$env] $svc-$i: draining connections"; sleep 0.6
  echo "[$env] $svc-$i: stopped, starting new instance"; sleep 0.6
  echo "[$env] $svc-$i: healthy"; sleep 0.3
  i=$((i + 1))
done
echo "[$env] $svc: rolling restart complete ($n instances)"
