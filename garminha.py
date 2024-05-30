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

# function to convert sleep json data to InfluxDB suitable format and write it to InfluxDB
def sleepjson_to_influxdb(host,port,database,json_data):
	# creating a connection to influxDB
    client = InfluxDBClient(host,port,username=influxuser, password=influxpass)  # replace with your InfluxDB host and port
	# switch to specific database
    client.switch_database(database)  # replace with your database name
    # Extracting relevant data from the JSON and converting to desired format, if not found assigning default values
    sleepTimeSeconds = json_data['dailySleepDTO'].get('sleepTimeSeconds', 0)
    if sleepTimeSeconds is not None:
        sleepTimeSeconds = int(sleepTimeSeconds)
    else:
        sleepTimeSeconds = 0
    napTimeSeconds = json_data['dailySleepDTO'].get('napTimeSeconds', 0)
    if napTimeSeconds is not None:
        napTimeSeconds = int(napTimeSeconds)
    else:
        napTimeSeconds = 0
    # Preparing json payload which will be pushed to InfluxDB
    json_body = [{
        "measurement": "dailySleepDTO",
        "tags": {
            "userID": json_data['dailySleepDTO'].get('userProfilePK', 0),
            "sleepFromDevice": json_data['dailySleepDTO'].get('sleepFromDevice', 0),
            "retro": json_data['dailySleepDTO'].get('retro', 0),
            "sleppFromDevice": json_data['dailySleepDTO'].get('sleepFromDevice', 0),
            "deviceRemCapable": json_data['dailySleepDTO'].get('deviceRemCapable', 0)
        },
        "time": json_data['dailySleepDTO'].get('calendarDate', 0),
        "fields": {
            "sleepTimeSeconds": sleepTimeSeconds,
            "napTimeSeconds": napTimeSeconds,
            "autoSleepStartTimestampGMT": json_data['dailySleepDTO'].get('autoSleepStartTimestampGMT', 0),
            "averageSpO2Value": float(json_data['dailySleepDTO'].get('averageSpO2Value', 0.0)),
            "lowestSpO2Value": float(json_data['dailySleepDTO'].get('lowestSpO2Value', 0.0)),
            "highestSpO2Value": float(json_data['dailySleepDTO'].get('highestSpO2Value', 0.0)),
            "averageSpO2HRSleep": float(json_data['dailySleepDTO'].get('averageSpO2HRSleep', 0.0)),
            "averageRespirationValue": float(json_data['dailySleepDTO'].get('averageRespirationValue', 0.0)),
            "lowestRespirationValue": float(json_data['dailySleepDTO'].get('lowestRespirationValue', 0.0)),
            "highestRespirationValue": float(json_data['dailySleepDTO'].get('highestRespirationValue', 0.0)),
            "awakeCount": int(json_data['dailySleepDTO'].get('awakeCount', 0)),
            "avgSleepStress": float(json_data['dailySleepDTO'].get('avgSleepStress', 0.0)),
            "ageGroup": str(json_data['dailySleepDTO'].get('ageGroup', "Unknown")),
            "sleepScoreFeedback": str(json_data['dailySleepDTO'].get('sleepScoreFeedback', "Unknown")),
            "sleepScoreInsight": str(json_data['dailySleepDTO'].get('sleepScoreInsight', "Unknown")),
            "sleepVersion": str(json_data['dailySleepDTO'].get('sleepVersion', "Unknown")),
            "appType": "APP"
        }
    }]
    # Write points to InfluxDB
    client.write_points(json_body)

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
    garth.resume(garmintoken)
    try:
        garth.client.username
    except GarthException:
        garth.login(email, password)

        garth.save(garmintoken)

    # if command line arguments are passed use them to set the start and end date else use default values
    if sys.argv > 1:
        start_date = datetime.date.today() - datetime.timedelta(days=sys.argv[1])
        end_date = datetime.date.today()
    elif sys.arg > 2:
        start_date = datetime.date.today() - datetime.timedelta(days=sys.argv[1])
        end_date = datetime.date.today() - datetime.timedelta(days=sys.argv[2])
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
        sleep = garth.connectapi(f"/wellness-service/wellness/dailySleepData/{garth.client.username}",params={"date": start_date.strftime('%Y-%m-%d'), "nonSleepBufferMinutes": 60},)
        sleepjson_to_influxdb(influxhost,influxport,influxdatabase,sleep)
        start_date += delta

        # random sleep period to prevent detection
        time.sleep(random.randint(1,10))