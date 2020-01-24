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
import sched, time

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

# -------------------------------------------
# end of configuration

s = sched.scheduler(time.time, time.sleep)

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
    print("Sending value %s via MQTT into topic '%s'..." % (value, topic))
    mqtt_client.publish(topic, value)

prev_temperature_soc = -99
prev_temperature_gpu = -99
prev_fan_speed = -99
prev_fan_speed_raw = -99


# Lets only send value by MQTT if current value has enough difference to previous value
def isEnoughPercentageDifference(prev_value, current_value):
    global mqtt_update_threshold
    if prev_value == -99:
        return True
    v = abs(((prev_value / current_value) - 1) * 100)
    return v >= mqtt_update_threshold

def getTemperatures():
    global prev_temperature_soc, prev_temperature_gpu, prev_fan_speed, prev_fan_speed_raw
    if os.path.exists(filepath_temperature_soc):
        with open(filepath_temperature_soc) as file_temperature_soc:
            temperature_soc = float(file_temperature_soc.read()) / 1000
            file_temperature_soc.close()

            print("Temperatures: SoC=%0.2f" % temperature_soc)

            if isEnoughPercentageDifference(prev_temperature_soc, temperature_soc):
                sendViaMQTT(mqtt_topic + "/temperature/soc", temperature_soc)
            prev_temperature_soc = temperature_soc

            if os.path.exists(filepath_temperature_gpu):
                with open(filepath_temperature_gpu) as file_temperature_gpu:
                    temperature_gpu = float(file_temperature_gpu.read()) / 1000
                    file_temperature_gpu.close()

                    print("Temperatures: GPU=%0.2f" % temperature_gpu)

                    if isEnoughPercentageDifference(prev_temperature_gpu, temperature_gpu):
                        sendViaMQTT(mqtt_topic + "/temperature/gpu", temperature_gpu)

                    prev_temperature_gpu = temperature_gpu

                    if os.path.exists(filepath_fan_speed):
                        with open(filepath_fan_speed) as file_fan_speed:
                            fan_speed = int(file_fan_speed.read())
                            fan_speed_percentage = int(float(fan_speed / fan_speed_max) * 100)
                            print("Current fan speed: %s (raw: %d)" % (str(fan_speed_percentage) + "%", fan_speed))

                            file_fan_speed.close()

                            desired_fan_speed0 = getFanSpeedPercentage(temperature_soc)
                            desired_fan_speed1 = getFanSpeedPercentage(temperature_gpu)
                            desired_fan_speed = max(desired_fan_speed0, desired_fan_speed1)
                            desired_fan_speed_raw = int(float(desired_fan_speed / 100) * fan_speed_max)
                            # obey fan_speed_min and fan_speed_max:
                            desired_fan_speed_raw = max(fan_speed_min, desired_fan_speed_raw)
                            desired_fan_speed_raw = min(fan_speed_max, desired_fan_speed_raw)

                            print("Setting fan speed to: %s (raw: %d)" % (str(desired_fan_speed) + "%", desired_fan_speed_raw))

                            if isEnoughPercentageDifference(prev_fan_speed_raw, desired_fan_speed_raw):
                                sendViaMQTT(mqtt_topic + "/speed/raw", desired_fan_speed_raw)
                            prev_fan_speed_raw = desired_fan_speed_raw

                            if isEnoughPercentageDifference(prev_fan_speed, desired_fan_speed):
                                sendViaMQTT(mqtt_topic + "/speed/percentage", desired_fan_speed)
                            prev_fan_speed = desired_fan_speed

                            with open(filepath_fan_speed, 'w') as file_fan_speed:
                                file_fan_speed.write(str(desired_fan_speed_raw))
                                file_fan_speed.close()
                    else:
                        print("Fan control not supported. Exiting.")
                        exit(1)
    else:
        print("SoC thermal sensor not found. Exiting.")
        exit(1)
    if interval > 0:
        s.enter(interval, 1, getTemperatures)
        print("Sleeping for %d seconds" % interval)

if __name__ == "__main__":
    # read config:
    config = configparser.ConfigParser()
    config.read('config.ini')

    interval = 60

    mqtt = False
    mqtt_host = ""
    mqtt_port = ""
    mqtt_topic = ""
    mqtt_update_threshold = 1

    try:
        interval = int(config['RUN']['INTERVAL'])
        mqtt = config['MQTT']
        if mqtt:
            mqtt_host = config['MQTT']['HOST']
            mqtt_port = int(config['MQTT']['PORT'])
            mqtt_topic = config['MQTT']['TOPIC']
            mqtt_client_id = config['MQTT']['CLIENT_ID']
            mqtt_update_threshold = float(config['MQTT']['UPDATE_THRESHOLD'])
            import paho.mqtt.client as mqtt
            def on_connect(client, userdata, flags, rc):
                print("Connected with result code " + str(rc))

            mqtt_client = mqtt.Client(client_id=mqtt_client_id)
            mqtt_client.on_connect = on_connect
            mqtt_client.connect(mqtt_host, mqtt_port, 60)
    except KeyError as e:
        print("Error: Required field in config.ini missing: " + str(e))
        exit()

    s.enter(0, 1, getTemperatures)
    s.run()
