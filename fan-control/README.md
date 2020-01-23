# fan-control

This script can be used for controlling the speed of the installed CPU fan on the Pine64 RockPro64 SBC.

Additionally it supports sending the temperatures and fan speeds via MQTT (e.g. can be used to integrate this into [home-assistant](https://github.com/home-assistant/home-assistant)).

## Pre-requisites 🛠
* [Python3](https://www.python.org/downloads/)

## Quick start 🍕

1. (optional) If you want to send temperature and fan speeds via MQTT you need to install python dependencies with

```pip3 install paho-mqtt```

2. Copy config.example.ini to config.ini and adapt settings if you want

3. Run script with

```python3 fan-control.py```

You probably need to run it as root if you want to actually control the fan speed.
