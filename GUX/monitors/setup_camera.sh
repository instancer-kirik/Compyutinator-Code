#!/bin/bash

# Configure CIO2 (raw sensor input)
media-ctl -d /dev/media0 --set-v4l2 '"ov8865 9-0010":0[fmt:SBGGR10_1X10/1920x1080]'
media-ctl -d /dev/media0 --set-v4l2 '"intel-ipu3-cio2 0":0[fmt:SBGGR10_1X10/1920x1080]'

# Configure IMGU (image processing)
media-ctl -d /dev/media1 --set-v4l2 '"ipu3-imgu 1 input":0[fmt:SBGGR10_1X10/1920x1080]'
media-ctl -d /dev/media1 --set-v4l2 '"ipu3-imgu 1":0[fmt:SBGGR10_1X10/1920x1080]'
media-ctl -d /dev/media1 --set-v4l2 '"ipu3-imgu 1":2[fmt:YUYV8_2X8/1920x1080]'
media-ctl -d /dev/media1 --set-v4l2 '"ipu3-imgu 1 output":0[fmt:YUYV8_2X8/1920x1080]'

# Enable links
media-ctl -d /dev/media1 -l "'ipu3-imgu 1':2 -> 'ipu3-imgu 1 output':0[1]"

# Set controls
v4l2-ctl -d /dev/video0 --set-ctrl=link_frequency=0
v4l2-ctl -d /dev/video0 --set-ctrl=test_pattern=0
