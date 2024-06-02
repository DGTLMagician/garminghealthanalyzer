import datetime
import time
import random
import json
import logging
import os
import sys
import requests
import calendar
import html
import matplotlib.pyplot as plt
import numpy as np
import garth

from dotenv import load_dotenv
from garth.exc import GarthException
from getpass import getpass
from openai import OpenAI
from influxdb import InfluxDBClient

# function to convert body battery json data to InfluxDB suitable format and write it to InfluxDB
def bbjson_to_influxdb(host,port,database,json_data):
	# creating a connection to influxDB
    client = InfluxDBClient(host,port,username=influxuser, password=influxpass)  # replace with your InfluxDB host and port
	# switch to specific database
    client.switch_database(database)
    # Preparing json payload which will be pushed to InfluxDB
    for item in json_data:
        date_obj = datetime.datetime.strptime(item['date'], '%Y-%m-%d')
        default_timestamp =  datetime.datetime.timestamp(date_obj)
        json_body = [{
        "measurement": "dailyBodyBatteryChargeDrain",
        "tags": {
            "date": item['date'],
        },
        "time": item.get('startTimestampGMT',default_timestamp),
        "fields": {
            "charged": item.get('charged', 1),
            "drained": item.get('drained', 1),
            }
        }]
    print(json_body)
    # Write points to InfluxDB
    client.write_points(json_body)

# function to convert body battery json data to InfluxDB suitable format and write it to InfluxDB
def bbvaluesjson_to_influxdb(host,port,database,json_data):
	# creating a connection to influxDB
    client = InfluxDBClient(host,port,username=influxuser, password=influxpass)  # replace with your InfluxDB host and port
	# switch to specific database
    client.switch_database(database)  # replace with your database name
    # Extracting relevant data from the JSON and converting to desired format, if not found assigning default values
    measurements = []
    for item in json_data:
        date_obj = datetime.datetime.strptime(item['date'], '%Y-%m-%d')
        default_timestamp =  datetime.datetime.timestamp(date_obj)
        for bodyBatteryValue in item.get('bodyBatteryValuesArray', []):
            measurements.append({
                "measurement": "bodyBattery",
                "tags": {
                    "date": item['date'],
                },
                "time": bodyBatteryValue[0] if len(bodyBatteryValue)>0 else default_timestamp,
                "fields": {
                    "bodyBatteryLevel": bodyBatteryValue[1] if len(bodyBatteryValue)>1 else 1,
                }
            })
    client.write_points(measurements)

# Entry point for the script
if __name__ == "__main__":
    # Loading environment variables
    load_dotenv()
    # assigning environment variables
    email = os.getenv("GARMINEMAIL")
    password = os.getenv("GARMINPASSWORD")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    garmintoken = os.getenv("GARMINTOKENS") or "~/.garminconnect"
    influxhost = os.getenv("INFLUXHOST")
    influxport = os.getenv("INFLUXPORT")
    influxuser = os.getenv("INFLUXUSER")
    influxpass = os.getenv("INFLUXPASS")
    influxdatabase = os.getenv("INFLUXDB")

    # Login to Garmin
    # If there's MFA, you'll be prompted during the login
    if os.path.isfile(garmintoken):
        try:
            garth.resume(garmintoken)
            garth.client.username
        except:
            # Login to Garmin
            garth.login(email, password)

            garth.save(garmintoken)
    else:
        # Login to Garmin
        garth.login(email, password)

        garth.save(garmintoken)

    # if command line arguments are passed use them to set the start and end date else use default values
    if len(sys.argv) > 1:
        start_date = datetime.date.today() - datetime.timedelta(days=int(sys.argv[1]))
        end_date = datetime.date.today()
    elif len(sys.argv) > 2:
        start_date = datetime.date.today() - datetime.timedelta(days=int(sys.argv[1]))
        end_date = datetime.date.today() - datetime.timedelta(days=int(sys.argv[2]))
    else:
        start_date = datetime.date.today() - datetime.timedelta(days=365*2)  # 2 years ago from today
        end_date = datetime.date.today()

    print(f"Syncing {start_date} until {end_date}")
    delta = datetime.timedelta(days=1)

    # iterating over days from start to end
    while start_date <= end_date:
        print("Working on Day: ")
        print(start_date)
        # fetching sleep data for the day and writing to the InfluxDB
        bodybattery = garth.connectapi(f"/wellness-service/wellness/bodyBattery/reports/daily",params={"startDate": start_date.strftime('%Y-%m-%d'), "endDate": start_date.strftime('%Y-%m-%d')},)
        bbjson_to_influxdb(influxhost,influxport,influxdatabase,bodybattery)
        bbvaluesjson_to_influxdb(influxhost,influxport,influxdatabase,bodybattery)
        start_date += delta

        # random sleep period to prevent detection
        time.sleep(random.randint(1,10))
