#!/usr/bin/env python3
import logging
import argparse
from math import floor
import sys
import os
import sys
import inspect
import getpass
import time
import json
import pandas as pd
from pprint import pprint as pp
from app.logger import logger
from app.xiq_api import XIQ
current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
logger = logging.getLogger('StaggeredReboot.Main')

XIQ_API_token = ''

pageSize = 100

parser = argparse.ArgumentParser()
parser.add_argument('--external',action="store_true", help="Optional - adds External Account selection, to use an external VIQ")
args = parser.parse_args()

PATH = current_dir

# Git Shell Coloring - https://gist.github.com/vratiu/9780109
RED   = "\033[1;31m"  
BLUE  = "\033[1;34m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
RESET = "\033[0;0m"

def yesNoLoop(question):
    validResponse = False
    while validResponse != True:
        response = input(f"{question} (y/n) ").lower()
        if response =='n' or response == 'no':
            response = 'n'
            validResponse = True
        elif response == 'y' or response == 'yes':
            response = 'y'
            validResponse = True
        elif response == 'q' or response == 'quit':
            sys.stdout.write(RED)
            sys.stdout.write("script is exiting....\n")
            sys.stdout.write(RESET)
            raise SystemExit
    return response

if XIQ_API_token:
    x = XIQ(token=XIQ_API_token)
else:
    print("Enter your XIQ login credentials")
    username = input("Email: ")
    password = getpass.getpass("Password: ")
    x = XIQ(user_name=username,password = password)

#OPTIONAL - use externally managed XIQ account
if args.external:
    accounts, viqName = x.selectManagedAccount()
    if accounts == 1:
        validResponse = False
        while validResponse != True:
            response = input("No External accounts found. Would you like to import data to your network?")
            if response == 'y':
                validResponse = True
            elif response =='n':
                sys.stdout.write(RED)
                sys.stdout.write("script is exiting....\n")
                sys.stdout.write(RESET)
                raise SystemExit
    elif accounts:
        validResponse = False
        while validResponse != True:
            print("\nWhich VIQ would you like to import the floor plan and APs too?")
            accounts_df = pd.DataFrame(accounts)
            count = 0
            for df_id, viq_info in accounts_df.iterrows():
                print(f"   {df_id}. {viq_info['name']}")
                count = df_id
            print(f"   {count+1}. {viqName} (This is Your main account)\n")
            selection = input(f"Please enter 0 - {count+1}: ")
            try:
                selection = int(selection)
            except:
                sys.stdout.write(YELLOW)
                sys.stdout.write("Please enter a valid response!!")
                sys.stdout.write(RESET)
                continue
            if 0 <= selection <= count+1:
                validResponse = True
                if selection != count+1:
                    newViqID = (accounts_df.loc[int(selection),'id'])
                    newViqName = (accounts_df.loc[int(selection),'name'])
                    x.switchAccount(newViqID, newViqName)

buildingResponse = yesNoLoop("Would you like to filter on a building (This would include all floors of the building)?")
if buildingResponse == 'y':
    building = input("Please enter the name of the building: ")
    print("Collecting Location information")
    floor_list = x.getFloors(building)
    if 'errors' in floor_list:
        errors = ", ".join(floor_list['errors'])
        print(errors)
        print("script is exiting....")
        raise SystemExit
    if not floor_list:
        print(f"There was no floors associated with the building {building}")
        print("script is exiting....")
        raise SystemExit


    device_data = []
    for floor in floor_list:
        print(f"Collecting Devices for floor '{floor['name']}'...")
        ## Collect Devices
        temp_data = x.collectDevices(pageSize,location_id=floor['id'])
        device_data = device_data + temp_data
        #pp(device_data)

else:
    device_data = x.collectDevices(pageSize)

if not device_data:
    print("There were no devices found!")
    print("script is exiting....")
    raise SystemExit

device_df = pd.DataFrame(device_data)
device_df.set_index('id',inplace=True)
filt = (device_df['connected'] == True) & (device_df['device_function'] == 'AP')
reboot_devices = device_df.loc[filt].copy()
hostnames = reboot_devices['hostname'].tolist()
print(f"Found {len(reboot_devices.index)} Devices:\n  ",end="")
print(*hostnames, sep="\n  ")

if len(reboot_devices.index) == 0:
    raise SystemExit

preview = yesNoLoop(f"Would you like to proceed rebooting these {len(reboot_devices.index)} Devices one at a time?")
if preview == 'n':
    print("script is exiting....")
    raise SystemExit

print("Starting the Staggered Reboot...\n")
for device_id in reboot_devices.index:
    print(device_id)
    print(f"Sending reboot to {reboot_devices.loc[device_id,'hostname']} ({reboot_devices.loc[device_id,'ip_address']})... ",end="")
    response = x.rebootDevice(device_id)
    if response == "Success":
        rebootSuccess = False
        print("Successful Sent")
        print("Waiting for AP to come back online...")
        t = 240
        while t:
            mins, secs = divmod(t, 60)
            timer = '   {:02d}:{:02d}'.format(mins, secs)
            print(timer, end='\r')
            time.sleep(1)
            t -= 1
        count = 0
        while rebootSuccess != True and count < 10:
            data = x.checkDevice(device_id)
            rebootSuccess = data['connected']
            if rebootSuccess:
                sys.stdout.write(GREEN)
                print(f"Device {reboot_devices.loc[device_id,'hostname']} successfully rebooted.")
                sys.stdout.write(RESET)
            else:
                sys.stdout.write(YELLOW)
                print(f"Device {reboot_devices.loc[device_id,'hostname']} is not back online.")
                count += 1
                print(f"Checking again attempt {count} of {10} in 1 minute...")
                sys.stdout.write(YELLOW)
                t = 60
                while t:
                    mins, secs = divmod(t, 60)
                    timer = '   {:02d}:{:02d}'.format(mins, secs)
                    print(timer, end='\r')
                    time.sleep(1)
                    t -= 1
        if rebootSuccess != True:
            sys.stdout.write(RED)
            print(f"Device {reboot_devices.loc[device_id,'hostname']} is still not showing connected!!!")
            sys.stdout.write(RESET)
            continueloop = yesNoLoop("Would you like to continue with the next AP?")
            if continueloop == 'n':
                print("script is exiting...")
                raise SystemExit