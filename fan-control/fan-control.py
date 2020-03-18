#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#   @date 2020-01-22
#   @author Marco H (myxor)
#
#   This script can be used for controlling the speed of the installed CPU fan
#     on the Pine64 RockPro64 SBC
#   Additionally it supports sending the temperatures and fan speeds via MQTT
#     (e.g. can be used to integrate this as a sensor into home-assistant.io)
#
import configparser
import os
import sched
import sys
import time

# file paths:
filepath_temperature_soc = "/sys/devices/virtual/thermal/thermal_zone0/temp"
filepath_temperature_gpu = "/sys/devices/virtual/thermal/thermal_zone1/temp"
filepath_fan_speed = "/sys/class/hwmon/hwmon0/pwm1"

# minimum and maximum fan speed raw values:
fan_speed_min = 0
fan_speed_max = 255

# -------------------------------------------
# end of configuration

s = sched.scheduler(time.time, time.sleep)


# fan speed percentage of maximum fan speed
def get_fan_speed_percentage(temperature):
    if temperature < 0:  # huh? what happened here?
        return 0
    elif 0 <= temperature < threshold0:
        return 10
    elif threshold0 <= temperature < threshold1:
        return 20
    elif threshold1 <= temperature < threshold2:
        return 30
    elif threshold2 <= temperature < threshold3:
        return 40
    elif threshold3 <= temperature < threshold4:
        return 50
    elif threshold4 <= temperature < threshold5:
        return 60
    elif threshold5 <= temperature < threshold6:
        return 70
    elif threshold6 <= temperature < threshold7:
        return 80
    elif threshold7 <= temperature < threshold8:
        return 90
    elif threshold8 <= temperature < threshold9:
        return 95
    else:
        return 100


def send_via_mqtt(topic, value):
    time.sleep(0.5)
    print("MQTT: Sending value %s into topic '%s'..." % (value, topic))
    mqtt_client.publish(topic, value, qos=0, retain=True)


prev_temperature_soc = -99
prev_temperature_gpu = -99
prev_fan_speed = -99
prev_fan_speed_raw = -99


# Lets only send value by MQTT if current value has enough difference to previous value
def is_enough_percentage_difference(prev_value, current_value):
    global mqtt_update_threshold
    if prev_value == -99:
        return True
    v = abs(((prev_value / current_value) - 1) * 100)
    return v >= mqtt_update_threshold


def get_temperatures():
    global prev_temperature_soc, prev_temperature_gpu, prev_fan_speed, prev_fan_speed_raw
    if os.path.exists(filepath_temperature_soc):
        with open(filepath_temperature_soc) as file_temperature_soc:
            temperature_soc = float(file_temperature_soc.read()) / 1000
            file_temperature_soc.close()

            print("Temperatures: SoC=%0.2f" % temperature_soc)

            if is_enough_percentage_difference(prev_temperature_soc, temperature_soc):
                send_via_mqtt(mqtt_topic + "/temperature/soc", temperature_soc)
            prev_temperature_soc = temperature_soc

            if os.path.exists(filepath_temperature_gpu):
                with open(filepath_temperature_gpu) as file_temperature_gpu:
                    temperature_gpu = float(file_temperature_gpu.read()) / 1000
                    file_temperature_gpu.close()

                    print("Temperatures: GPU=%0.2f" % temperature_gpu)

                    if is_enough_percentage_difference(prev_temperature_gpu, temperature_gpu):
                        send_via_mqtt(mqtt_topic + "/temperature/gpu", temperature_gpu)

                    prev_temperature_gpu = temperature_gpu

                    if os.path.exists(filepath_fan_speed):
                        with open(filepath_fan_speed) as file_fan_speed:
                            fan_speed = int(file_fan_speed.read())
                            fan_speed_percentage = int(float(fan_speed / fan_speed_max) * 100)
                            print("Fan speed: %s (raw: %d)" % (str(fan_speed_percentage) + "%", fan_speed))

                            file_fan_speed.close()

                            desired_fan_speed0 = get_fan_speed_percentage(temperature_soc)
                            desired_fan_speed1 = get_fan_speed_percentage(temperature_gpu)
                            desired_fan_speed = max(desired_fan_speed0, desired_fan_speed1)
                            desired_fan_speed_raw = int(float(desired_fan_speed / 100) * fan_speed_max)
                            # obey fan_speed_min and fan_speed_max:
                            desired_fan_speed_raw = max(fan_speed_min, desired_fan_speed_raw)
                            desired_fan_speed_raw = min(fan_speed_max, desired_fan_speed_raw)

                            print("Fan speed set to: %s (raw: %d)" % (
                                str(desired_fan_speed) + "%", desired_fan_speed_raw))

                            if is_enough_percentage_difference(prev_fan_speed_raw, desired_fan_speed_raw):
                                send_via_mqtt(mqtt_topic + "/speed/raw", desired_fan_speed_raw)
                            prev_fan_speed_raw = desired_fan_speed_raw

                            if is_enough_percentage_difference(prev_fan_speed, desired_fan_speed):
                                send_via_mqtt(mqtt_topic + "/speed/percentage", desired_fan_speed)
                            prev_fan_speed = desired_fan_speed

                            with open(filepath_fan_speed, 'w') as file_fan_speed_rw:
                                file_fan_speed_rw.write(str(desired_fan_speed_raw))
                                file_fan_speed_rw.close()
                    else:
                        print("Fan control not supported. Exiting.", file=sys.stderr)
                        exit(1)
    else:
        print("SoC thermal sensor not found. Exiting.", file=sys.stderr)
        exit(1)
    if interval > 0:
        s.enter(interval, 1, get_temperatures)


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

        thresholds = config['THRESHOLDS']
        if thresholds:
            threshold0 = int(config['THRESHOLDS']['threshold0'])
            threshold1 = int(config['THRESHOLDS']['threshold1'])
            threshold2 = int(config['THRESHOLDS']['threshold2'])
            threshold3 = int(config['THRESHOLDS']['threshold3'])
            threshold4 = int(config['THRESHOLDS']['threshold4'])
            threshold5 = int(config['THRESHOLDS']['threshold5'])
            threshold6 = int(config['THRESHOLDS']['threshold6'])
            threshold7 = int(config['THRESHOLDS']['threshold7'])
            threshold8 = int(config['THRESHOLDS']['threshold8'])
            threshold9 = int(config['THRESHOLDS']['threshold9'])

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
        print("Error: Required field in config.ini missing: " + str(e), file=sys.stderr)
        exit()

    s.enter(0, 1, get_temperatures)
    s.run()
