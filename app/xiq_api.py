#!/usr/bin/env python3
import logging
import os
import inspect
import sys
import json
import time
import requests
import pandas as pd
from pprint import pprint as pp
current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir) 
from requests.exceptions import HTTPError, ReadTimeout
from app.logger import logger

logger = logging.getLogger('StaggeredReboot.xiq_api')

PATH = current_dir


class XIQ:
    def __init__(self, user_name=None, password=None, token=None):
        self.URL = "https://api.extremecloudiq.com"
        self.headers = {"Accept": "application/json", "Content-Type": "application/json"}
        self.totalretries = 5
        self.locationTree_df = pd.DataFrame(columns = ['id', 'name', 'type', 'parent'])
        if token:
            self.headers["Authorization"] = "Bearer " + token
        else:
            try:
                self.__getAccessToken(user_name, password)
            except ValueError as e:
                print(e)
                raise SystemExit
            except HTTPError as e:
               print(e)
               raise SystemExit
            except:
                log_msg = "Unknown Error: Failed to generate token for XIQ"
                logger.error(log_msg)
                print(log_msg)
                raise SystemExit 
    #API CALLS
    def __setup_get_api_call(self, info, url):
        success = 0
        for count in range(1, self.totalretries):
            try:
                response = self.__get_api_call(url=url)
            except ValueError as e:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with {e}")
            except Exception as e:
                print(f"API to {info} failed with {e}")
                print('script is exiting...')
                raise SystemExit
            except:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with unknown API error")
            else:
                success = 1
                break
        if success != 1:
            print("failed to {}. Cannot continue.".format(info))
            print("exiting script...")
            raise Exception
        if 'error' in response:
            if response['error_mssage']:
                log_msg = (f"Status Code {response['error_id']}: {response['error_message']}")
                logger.error(log_msg)
                print(f"API Failed {info} with reason: {log_msg}")
                print("Script is exiting...")
                raise Exception
        return response

    def __setup_post_api_call(self, info, url, payload):
        success = 0
        for count in range(1, self.totalretries):
            try:
                response = self.__post_api_call(url=url, payload=payload)
            except ValueError as e:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with {e}")
            except Exception as e:
                print(f"API to {info} failed with {e}")
                print('script is exiting...')
                raise SystemExit
            except:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with unknown API error")
            else:
                success = 1
                break
        if success != 1:
            print("failed {}. Cannot continue to import".format(info))
            print("exiting script...")
            raise SystemExit
        if 'error' in response:
            if response['error_mssage']:
                log_msg = (f"Status Code {response['error_id']}: {response['error_message']}")
                logger.error(log_msg)
                print(f"API Failed {info} with reason: {log_msg}")
                print("Script is exiting...")
                raise SystemExit
        return response

    def __setup_post_api_call_no_payload(self, info, url):
        success = 0
        for count in range(1, self.totalretries):
            try:
                response = self.__post_api_call_no_payload(url=url)
            except ValueError as e:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with {e}")
            except Exception as e:
                print(f"API to {info} failed with {e}")
                print('script is exiting...')
                raise SystemExit
            except:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with unknown API error")
            else:
                success = 1
                break
        if success != 1:
            print("failed {}. Cannot continue to import".format(info))
            print("exiting script...")
            raise SystemExit
        if 'error' in response:
            if response['error_mssage']:
                log_msg = (f"Status Code {response['error_id']}: {response['error_message']}")
                logger.error(log_msg)
                print(f"API Failed {info} with reason: {log_msg}")
                print("Script is exiting...")
                raise SystemExit
        return response
    
    def __setup_post_lro_call(self,info,url,payload):
        success = 0
        print("Sending CLI commands... ",end="")
        for count in range(1, self.totalretries):
            try:
                lro_url = self.__post_lro_call(url=url,payload=payload)
            except TypeError as e:
                print("Failed")
                print(f"API failed attempt {count} of {self.totalretries} with {e}")
            except HTTPError as e:
                print("Failed")
                print(f"API failed attempt {count} of {self.totalretries} with {e}")
            except Exception as e:
                print("Failed")
                print(f"API to {info} failed with {e}")
                print('script is exiting...')
                raise SystemExit
            except:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with unknown API error")		
            else:
                success = 1
                break
        if success != 1:
            print("failed {}. Cannot continue to import".format(info))
            print("exiting script...")
            raise SystemExit
        print("Done")
        time.sleep(10)
        if lro_url:
            lro_running = True
            count = 1
            while lro_running and count < 11:
                print(f"Attempting to collect CLI responses - attempt {count} of 10")
                try:
                    rawData = self.__setup_get_api_call(info='to gather LRO CLI response',url=lro_url)
                except TypeError as e:
                    print(f"API failed with {e}")
                    count+=1
                    success = False
                except HTTPError as e:
                    print(f"API HTTP Error {e}")
                    count+=1
                    success = False
                except Exception as e:
                    raise SystemExit
                except:
                    print(f"API failed to gather LRO CLI response with an unknown API error:\n 	{lro_url}")		
                    count+=1
                    success = False
                else:
                    success = True
                if success:
                    if rawData['done'] == True:
                        data = rawData['response']
                        lro_running = False
                        break
                    else:
                        if rawData['metadata']['status'] != "RUNNING":
                            print(f"It appears that the long-running operation failed. The status is f{rawData['metadata']['status']}")
                            print(rawData)
                            lro_running = False
                        else:
                            print(f"The long-running operation is not complete. Checking again in 120 secs.")
                            t = 120
                            while t:
                                mins, secs = divmod(t, 60)
                                timer = '   {:02d}:{:02d}'.format(mins, secs)
                                print(timer, end='\r')
                                time.sleep(1)
                                t -= 1

                count += 1
        if data:
            return(data)
        else:
            print("collecting CLI failed")
            raise SystemExit

    def __get_api_call(self, url):
        try:
            response = requests.get(url, headers= self.headers)
        except HTTPError as http_err:
            logger.error(f'HTTP error occurred: {http_err} - on API {url}')
            raise ValueError(f'HTTP error occurred: {http_err}') 
        if response is None:
            log_msg = "ERROR: No response received from XIQ!"
            logger.error(log_msg)
            raise ValueError(log_msg)
        if response.status_code != 200:
            log_msg = f"Error - HTTP Status Code: {str(response.status_code)}"
            logger.error(f"{log_msg}")
            try:
                data = response.json()
            except json.JSONDecodeError:
                logger.warning(f"\t\t{response.text}")
            else:
                if 'error_message' in data:
                    logger.warning(f"\t\t{data['error_message']}")
                else:
                    logger.warning(f"\n\n{data}")
            raise ValueError(log_msg) 
        try:
            data = response.json()
        except json.JSONDecodeError:
            logger.error(f"Unable to parse json data - {url} - HTTP Status Code: {str(response.status_code)}")
            raise ValueError("Unable to parse the data from json, script cannot proceed")
        return data

    def __post_api_call(self, url, payload):
        try:
            response = requests.post(url, headers= self.headers, data=payload)
        except HTTPError as http_err:
            logger.error(f'HTTP error occurred: {http_err} - on API {url}')
            raise ValueError(f'HTTP error occurred: {http_err}') 
        if response is None:
            log_msg = "ERROR: No response received from XIQ!"
            logger.error(log_msg)
            raise ValueError(log_msg)
        if response.status_code == 201:
            return "Success"
        elif response.status_code != 200:
            log_msg = f"Error - HTTP Status Code: {str(response.status_code)}"
            logger.error(f"{log_msg}")
            try:
                data = response.json()
            except json.JSONDecodeError:
                logger.warning(f"\t\t{response.text()}")
            else:
                if 'error_message' in data:
                    logger.warning(f"\t\t{data['error_message']}")
                    raise Exception(data['error_message'])
            raise ValueError(log_msg)
        try:
            data = response.json()
        except json.JSONDecodeError:
            logger.error(f"Unable to parse json data - {url} - HTTP Status Code: {str(response.status_code)}")
            raise ValueError("Unable to parse the data from json, script cannot proceed")
        return data

    def __post_api_call_no_payload(self, url):
        try:
            response = requests.post(url, headers= self.headers)
        except HTTPError as http_err:
            logger.error(f'HTTP error occurred: {http_err} - on API {url}')
            raise ValueError(f'HTTP error occurred: {http_err}') 
        if response is None:
            log_msg = "ERROR: No response received from XIQ!"
            logger.error(log_msg)
            raise ValueError(log_msg)
        if response.status_code == 201:
            return "Success"
        elif response.status_code != 200:
            log_msg = f"Error - HTTP Status Code: {str(response.status_code)}"
            logger.error(f"{log_msg}")
            try:
                data = response.json()
            except json.JSONDecodeError:
                logger.warning(f"\t\t{response.text()}")
            else:
                if 'error_message' in data:
                    logger.warning(f"\t\t{data['error_message']}")
                    raise Exception(data['error_message'])
            raise ValueError(log_msg)
        else:
            return "Success"
    
    def __post_lro_call(self, url, payload = {},):
        try:
            response = requests.post(url, headers=self.headers, data=payload, timeout=60)
        except HTTPError as http_err:
            raise HTTPError(f'HTTP error occurred: {http_err} - on API {url}')
        except ReadTimeout as timout_err:
            raise HTTPError(f'HTTP error occurred: {timout_err} - on API {url}')
        except Exception as err:
            raise ValueError(f'Other error occurred: {err}: on API {url}')
        else:
            if response is None:
                log_msg = "ERROR: No response received from XIQ!"
                logger.error(log_msg)
                raise ValueError(log_msg)
            elif response.status_code != 202:
                log_msg = f"Error - HTTP Status Code: {str(response.status_code)}"
                logger.error(f"{log_msg}")
                try:
                    data = response.json()
                except json.JSONDecodeError:
                    logger.warning(f"\t\t{response.text()}")
                else:
                    if 'error_message' in data:
                        logger.warning(f"\t\t{data['error_message']}")
                        raise Exception(data['error_message'])
                raise ValueError(log_msg)
            data = response.headers
            return data['Location']
    

    def __getAccessToken(self, user_name, password):
        info = "get XIQ token"
        success = 0
        url = self.URL + "/login"
        payload = json.dumps({"username": user_name, "password": password})
        for count in range(1, self.totalretries):
            try:
                data = self.__post_api_call(url=url,payload=payload)
            except ValueError as e:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with {e}")
            except Exception as e:
                print(f"API to {info} failed with {e}")
                print('script is exiting...')
                raise SystemExit
            except:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with unknown API error")
            else:
                success = 1
                break
        if success != 1:
            print("failed to get XIQ token. Cannot continue to import")
            print("exiting script...")
            raise SystemExit
        
        if "access_token" in data:
            #print("Logged in and Got access token: " + data["access_token"])
            self.headers["Authorization"] = "Bearer " + data["access_token"]
            return 0

        else:
            log_msg = "Unknown Error: Unable to gain access token for XIQ"
            logger.warning(log_msg)
            raise ValueError(log_msg)

    #BUILDINGS
    def __buildLocationDf(self, location, pname = 'Global'):
        if 'parent_id' not in location:
            temp_df = pd.DataFrame([{'id': location['id'], 'name':location['name'], 'type': 'Global', 'parent':pname}])
            self.locationTree_df = pd.concat([self.locationTree_df, temp_df], ignore_index=True)
        else:
            temp_df = pd.DataFrame([{'id': location['id'], 'name':location['name'], 'type': location['type'], 'parent':pname}])
            self.locationTree_df = pd.concat([self.locationTree_df, temp_df], ignore_index=True)
        r = json.dumps(location['children'])
        if location['children']:
            parent_name = location['name']
            for child in location['children']:
                self.__buildLocationDf(child, pname=parent_name)

    # EXTERNAL ACCOUNTS
    def __getVIQInfo(self):
        info="get current VIQ name"
        success = 0
        url = "{}/account/home".format(self.URL)
        for count in range(1, self.totalretries):
            try:
                data = self.__get_api_call(url=url)
            except ValueError as e:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with {e}")
            except:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with unknown API error")
            else:
                success = 1
                break
        if success != 1:
            print(f"Failed to {info}")
            return 1
            
        else:
            self.viqName = data['name']
            self.viqID = data['id']

    ## EXTERNAL FUNCTION

    #ACCOUNT SWITCH
    def selectManagedAccount(self):
        self.__getVIQInfo()
        info="gather accessible external XIQ acccounts"
        success = 0
        url = "{}/account/external".format(self.URL)
        for count in range(1, self.totalretries):
            try:
                data = self.__get_api_call(url=url)
            except ValueError as e:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with {e}")
            except:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with unknown API error")
            else:
                success = 1
                break
        if success != 1:
            print(f"Failed to {info}")
            return 1
            
        else:
            return(data, self.viqName)
      
    def switchAccount(self, viqID, viqName):
        info=f"switch to external account {viqName}"
        success = 0
        url = "{}/account/:switch?id={}".format(self.URL,viqID)
        payload = ''
        for count in range(1, self.totalretries):
            try:
                data = self.__post_api_call(url=url, payload=payload)
            except ValueError as e:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with {e}")
            except Exception as e:
                print(f"API to {info} failed with {e}")
                print('script is exiting...')
                raise SystemExit
            except:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with unknown API error")
            else:
                success = 1
                break
        if success != 1:
            print("failed to get XIQ token to {}. Cannot continue to import".format(info))
            print("exiting script...")
            raise SystemExit
        
        if "access_token" in data:
            #print("Logged in and Got access token: " + data["access_token"])
            self.headers["Authorization"] = "Bearer " + data["access_token"]
            self.__getVIQInfo()
            if viqName != self.viqName:
                logger.error(f"Failed to switch external accounts. Script attempted to switch to {viqName} but is still in {self.viqName}")
                print("Failed to switch to external account!!")
                print("Script is exiting...")
                raise SystemExit
            return 0

        else:
            log_msg = "Unknown Error: Unable to gain access token for XIQ"
            logger.warning(log_msg)
            raise ValueError(log_msg)

    ## LOCATIONS
    def gatherLocations(self):
        info=f"gather location tree"
        url = "{}/locations/tree".format(self.URL)
        response = self.__setup_get_api_call(info,url)
        for location in response:
            self.__buildLocationDf(location)
        return (self.locationTree_df)

    ## Devices
    def collectDevices(self, pageSize, location_id=None):
        info = "collecting devices" 
        page = 1
        pageCount = 1
        firstCall = True

        devices = []
        while page <= pageCount:
            url = self.URL + "/devices?views=FULL&page=" + str(page) + "&limit=" + str(pageSize)
            if location_id:
                url = url  + "&locationId=" +str(location_id)
            rawList = self.__setup_get_api_call(info,url)
            devices = devices + rawList['data']

            if firstCall == True:
                pageCount = rawList['total_pages']
            print(f"completed page {page} of {rawList['total_pages']} collecting Devices")
            page = rawList['page'] + 1 
        return devices

    def checkDevice(self, device_id):
        info = "checking device status"
        url = self.URL + "/devices/" + str(device_id) + "?fields=CONNECTED"
        rawList = self.__setup_get_api_call(info,url)
        return rawList


    ## Reboot
    def rebootDevice(self, device_id):
        info = "rebooting device"
        url = self.URL + "/devices/" + str(device_id) + "/:reboot"
        response = self.__setup_post_api_call_no_payload(info,url)
        return response

