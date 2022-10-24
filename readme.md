# XIQ Staggered Reboot
### XIQ_Staggered_Reboot.py
## Purpose
This script will reboot APs 1 at a time to allow minimal impact to clients. This can be done for all APs in your XIQ instance or all APs in a specified building.

## Information
##### Collecting Devices
When running the script, you will be given the option of entering a building name. The script will then just collect devices for floors within that building. If no building is provided, the script will collect all devices in XIQ. The script will filter out a list of devices that have a device function of AP and are currently connected to XIQ. 

##### Rebooting Devices
The script will provide the count of APs as well as a list of AP names for the devices to be rebooted. Once the user confirms they are good with starting the staggered reboot the script will begin rebooting the first device. An API call will be made to XIQ to reboot the first device. The script will then sleep for 5 mins with a countdown timer will be presented to the user. At the end of the countdown timer, the script will check the status of the device. If the device is connected the script will proceed with the next AP.
If for some reason the device is showing not connected at the end of the 5 minute time, the script will sleep for 1 min and check again. The script will do this a total of 10 times (so AP has been down for 15 mins total) before it will stop and inform the user that the AP has not connected back after reboot. The script will then ask the user if they would like to proceed with the next AP.

## Needed files
The XIQ_Staggered_Reboot.py script uses several other files. If these files are missing the script will not function.
In the same folder as the XIQ_Staggered_Reboot.py script there should be an /app/ folder. Inside this folder should be a logger.py file and a xiq_api.py file. After running the script a new file 'staggered_reboot.log' will be created.

The log file that is created when running will show any errors that the script might run into. It is a great place to look when troubleshooting any issues.

## Running the script
open the terminal to the location of the script and run this command.

```
python XIQ_Staggered_Reboot.py
```
### Logging in
The script will prompt the user for XIQ credentials.
>Note: your password will not show on the screen as you type

### flags
There is an optional flag that can be added to the script when running.
```
--external
```
This flag will allow you to create the locations and assign the devices to locations on an XIQ account you are an external user on. After logging in with your XIQ credentials the script will give you a numeric option of each of the XIQ instances you have access to. Choose the one you would like to use.

You can add the flag when running the script.
```
python XIQ_Staggered_Reboot.py --external
```
## requirements
There are additional modules that need to be installed in order for this script to function. They are listed in the requirements.txt file and can be installed with the command 'pip install -r requirements.txt' if using pip.