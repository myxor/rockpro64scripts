#!/usr/bin/env python
#
#   @date 2020-01-22
#   @author Marco H (myxor)
#
#   This script can be used for controlling the speed of the installed CPU fan
#    on the Pine64 RockPro64 SBC
#
#
import os

filepath_temperature0="/sys/devices/virtual/thermal/thermal_zone0/temp"
filepath_temperature1="/sys/devices/virtual/thermal/thermal_zone1/temp"

filepath_fan_speed="/sys/class/hwmon/hwmon0/pwm1"
fan_speed_min = 0
fan_speed_max = 255

# thresholds in °C:
threshold0 = 30
threshold1 = 35
threshold2 = 40
threshold3 = 45
threshold4 = 50

# value in percentage of maximum fan speed
def getFanSpeedPercentage(temperature):
    if (temperature < 0): # huh? what happened here?
        return 0
    elif (temperature >= 0 and temperature < threshold0):
        return 5
    elif (temperature >= threshold0 and temperature < threshold1):
        return 20
    elif (temperature >= threshold1 and temperature < threshold2):
        return 40
    elif (temperature >= threshold2 and temperature < threshold3):
        return 60
    elif (temperature >= threshold3 and temperature < threshold4):
        return 80
    else:
        return 100 # fallback


# start
if os.path.exists(filepath_temperature0):
    with open(filepath_temperature0) as file_temperature0:
        temperature0 = float(file_temperature0.read()) / 1000
        file_temperature0.close()

        if os.path.exists(filepath_temperature1):
            with open(filepath_temperature1) as file_temperature1:
                temperature1 = float(file_temperature1.read()) / 1000
                file_temperature1.close()

                print("temperatures: %0.2f°C, %0.2f°C" % (temperature0, temperature1))

                if os.path.exists(filepath_fan_speed):
                    with open(filepath_fan_speed) as file_fan_speed:
                        fan_speed = int(file_fan_speed.read())
                        fan_speed_percentage = int(float(fan_speed / fan_speed_max) * 100)
                        print("current fan speed: %s (raw: %d)" % (str(fan_speed_percentage) + "%", fan_speed))
                        file_fan_speed.close()

                        desired_fan_speed0 = getFanSpeedPercentage(temperature0)
                        desired_fan_speed1 = getFanSpeedPercentage(temperature1)
                        desired_fan_speed = max(desired_fan_speed0, desired_fan_speed1)
                        desired_fan_speed_raw = int(float(desired_fan_speed / 100) * fan_speed_max)

                        print("desired fan speeds: (%s, %s) ==> %s (raw: %d)" % (str(desired_fan_speed0) + "%", str(desired_fan_speed1) + "%", str(desired_fan_speed) + "%", desired_fan_speed_raw))

                        with open(filepath_fan_speed, 'w') as file_fan_speed:
                            file_fan_speed.write(str(desired_fan_speed_raw))
                            file_fan_speed.close()