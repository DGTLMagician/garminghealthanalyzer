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

# function to convert heartrate json data to InfluxDB suitable format and write it to InfluxDB
def daily_overview_to_influxdb(host, port, database, json_data):
    client = InfluxDBClient(host,port,username=influxuser, password=influxpass)
    client.switch_database(database)
    for item in json_data:
        json_body = [{
            "measurement": "dailyHeartRateOverview",
            "tags": {"date": item.get('calendarDate'),},
            "time": item.get('startTimestampGMT'),
            "fields": {
                "maxHeartRate": item.get('maxHeartRate'),
                "minHeartRate": item.get('minHeartRate'),
                "restingHeartRate": item.get('restingHeartRate'),
            }
        }]
        client.write_points(json_body)

def heartrates_to_influxdb(host,port,database,json_data):
    client = InfluxDBClient(host,port,username=influxuser, password=influxpass)
    client.switch_database(database)
    measurements = []
    for item in json_data:
        for hrValue in item.get('heartRateValuesArray', []):
            date = datetime.datetime.fromtimestamp(hrValue[0]/1000)
            formatted_date = date.isoformat()
            measurements.append({
                "measurement": "heartRateValues",
                "tags": {"date": item['date'],},
                "time": formatted_date,
                "fields": {
                    "heartRateValue": hrValue[1],
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
        # fetching heartrate data for the day and writing to the InfluxDB
        heartrate = garth.connectapi(f"/wellness-service/wellness/dailyHeartRate/{garth.client.profile['displayName']}",params={"date": start_date.strftime('%Y-%m-%d')},)
        daily_overview_to_influxdb(influxhost,influxport,influxdatabase,heartrate)
        heartrates_to_influxdb(influxhost,influxport,influxdatabase,heartrate)
        start_date += delta

        # random sleep period to prevent detection
        time.sleep(random.randint(1,10))
