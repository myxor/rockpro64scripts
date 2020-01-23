#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#   @date 2020-01-22
#   @author Marco H (myxor)
#
#   This script can be used for controlling the speed of the installed CPU fan
#     on the Pine64 RockPro64 SBC
#   Additionally it supports sending the temperatures and fan speeds via MQTT
#     (e.g. can be used to integrate this into home-assistant.io)
#
import os
import configparser

# file paths:
filepath_temperature_soc="/sys/devices/virtual/thermal/thermal_zone0/temp"
filepath_temperature_gpu="/sys/devices/virtual/thermal/thermal_zone1/temp"
filepath_fan_speed="/sys/class/hwmon/hwmon0/pwm1"

# minimum and maximum fan speed raw values:
fan_speed_min = 0
fan_speed_max = 255

# configure thresholds in °C:
threshold0 = 30
threshold1 = 35
threshold2 = 40
threshold3 = 45
threshold4 = 50

# fan speed percentage of maximum fan speed
def getFanSpeedPercentage(temperature):
    if (temperature < 0): # huh? what happened here?
        return 0
    elif (temperature >= 0 and temperature < threshold0):
        return 10
    elif (temperature >= threshold0 and temperature < threshold1):
        return 25
    elif (temperature >= threshold1 and temperature < threshold2):
        return 50
    elif (temperature >= threshold2 and temperature < threshold3):
        return 65
    elif (temperature >= threshold3 and temperature < threshold4):
        return 80
    else:
        return 100

def sendViaMQTT(topic, value):
    time.sleep(0.5)
    mqtt_client.publish(topic, value)

def getTemperatures():
    if os.path.exists(filepath_temperature_soc):
        with open(filepath_temperature_soc) as file_temperature_soc:
            temperature_soc = float(file_temperature_soc.read()) / 1000
            file_temperature_soc.close()

            if os.path.exists(filepath_temperature_gpu):
                with open(filepath_temperature_gpu) as file_temperature_gpu:
                    temperature_gpu = float(file_temperature_gpu.read()) / 1000
                    file_temperature_gpu.close()

                    sendViaMQTT(mqtt_topic + "/temperature/soc", temperature_soc)
                    sendViaMQTT(mqtt_topic + "/temperature/gpu", temperature_gpu)

                    print("temperatures: SoC=%0.2f C, GPU=%0.2f C" % (temperature_soc, temperature_gpu))

                    if os.path.exists(filepath_fan_speed):
                        with open(filepath_fan_speed) as file_fan_speed:
                            fan_speed = int(file_fan_speed.read())
                            fan_speed_percentage = int(float(fan_speed / fan_speed_max) * 100)
                            print("current fan speed: %s (raw: %d)" % (str(fan_speed_percentage) + "%", fan_speed))

                            file_fan_speed.close()

                            desired_fan_speed0 = getFanSpeedPercentage(temperature_soc)
                            desired_fan_speed1 = getFanSpeedPercentage(temperature_gpu)
                            desired_fan_speed = max(desired_fan_speed0, desired_fan_speed1)
                            desired_fan_speed_raw = int(float(desired_fan_speed / 100) * fan_speed_max)
                            # obey fan_speed_min and fan_speed_max:
                            desired_fan_speed_raw = max(fan_speed_min, desired_fan_speed_raw)
                            desired_fan_speed_raw = min(fan_speed_max, desired_fan_speed_raw)

                            print("desired fan speeds: (%s, %s) ==> %s (raw: %d)" % (str(desired_fan_speed0) + "%", str(desired_fan_speed1) + "%", str(desired_fan_speed) + "%", desired_fan_speed_raw))

                            sendViaMQTT(mqtt_topic + "/speed/raw", desired_fan_speed_raw)
                            sendViaMQTT(mqtt_topic + "/speed/percentage", desired_fan_speed)

                            with open(filepath_fan_speed, 'w') as file_fan_speed:
                                file_fan_speed.write(str(desired_fan_speed_raw))
                                file_fan_speed.close()
                    else:
                        print("Fan control not supported. Exiting.")
    else:
        print("SoC thermal sensor not found. Exiting.")

if __name__ == "__main__":
    # read config:
    config = configparser.ConfigParser()
    config.read('config.ini')

    mqtt = False
    mqtt_host = ""
    mqtt_port = ""
    mqtt_topic = ""

    try:
        mqtt = config['MQTT']
        if mqtt:
            mqtt_host = config['MQTT']['HOST']
            mqtt_port = int(config['MQTT']['PORT'])
            mqtt_topic = config['MQTT']['TOPIC']
            mqtt_client_id = config['MQTT']['CLIENT_ID']
            import paho.mqtt.client as mqtt
            import time
            def on_connect(client, userdata, flags, rc):
                print("Connected with result code " + str(rc))

            mqtt_client = mqtt.Client(client_id=mqtt_client_id)
            mqtt_client.on_connect = on_connect
            mqtt_client.connect(mqtt_host, mqtt_port, 60)
    except KeyError as e:
        print("Error: Required field in config.ini missing: " + str(e))
        exit()

    getTemperatures()
