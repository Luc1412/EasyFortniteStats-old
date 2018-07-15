#!/usr/bin/env bash
while true
do
    python3.6 EasyFortniteStats.py
    echo 'Do you want to stop the Bot? Press Ctl+C!'
    echo "Rebooting in:"
    for i in 5 4 3 2 1
    do
        echo "$i..."
        sleep 1
    done
    echo 'Bot restart!'
done