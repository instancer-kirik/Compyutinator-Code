#!/bin/bash
export QT_QPA_PLATFORM=xcb
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"
cd /home/kirik/Code/BigLinks/Compyutinator-Code
sudo -E /home/kirik/.cache/pypoetry/virtualenvs/biglinks--3BrBG9W-py3.12/bin/python ./GUX/pens/enhanced_pen_scroll.py

