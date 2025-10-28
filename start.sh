#!/bin/bash
cmd="python3 -m server"

trap ctrl_c INT

function ctrl_c() {
    echo "Stopping."
    kill $(pgrep -f "$cmd")
    exit 0
}

kill $(pgrep -f "$cmd")

$cmd &
echo $(pgrep -f "$cmd")
echo "--------------"
while inotifywait -e close_write server; do 
    kill $(pgrep -f "$cmd")
    clear
    $cmd &
    echo $(pgrep -f "$cmd")
    echo "--------------"
done
