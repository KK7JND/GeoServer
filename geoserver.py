#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Python adapter to send messages and spot reports to a GeoChron display. This
adapter depends on the GeoChron cloud services, so if the Internet is down
this adapter is inoperative.

This adapter listens for JSON UDP messages on the assigned port, processes
the messages, then posts updates to the GeoChron servers via the GeoChron
REST APIs over HTTPS.

GeoServer version 0.4
"""

import socket
import sys
import time
import configparser
import json
import datetime
import re
import requests
import threading
import string
import warnings
from distutils.util import strtobool

# Import version specific modules
if sys.version_info.major == 3:
    import queue
elif sys.version_info.major == 2:
    import Queue
else:
    raise NotImplementedError

class GeoServer:
    """ Class GeoServer """
    # pylint: disable=too-many-instance-attributes
    # These are all required variables.    
    # Configuration variables.
    computer_name = ""
    config = ""
    consolelevel = 0
    logfilelevel = 0
    logfile = ""
    geoBaseUrl = ""
    geoApiKey = ""
    geoSpotLayer = "0"
    geoSpotComponent = ""
    geoMsgLayer = "0"
    geoMsgComponent = ""
    geoMsgPosition = ""
    geoMsgColor = ""
    geoMsgFontSize = ""
    geoGridNoCall = ""
    geoGridNoColor = ""
    geoAuthEnabled = False
    geoAuthToken = ""
    # Debugging constants.
    log_smdr = 1
    log_critical = 2
    log_error = 3
    log_warning = 4
    log_info = 5
    log_entry = 6
    log_parm = 7
    log_debug = 8
    log_hidebug = 9
    log_experimental = 10 
    # Runtime variables.
    addr = ""
    recv_buffer = ""
    send_buffer = ""
    log_handle = ""
    grid_data = ''
    spot_data = ''
    message_data = ''

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config')
        self.computer_name = socket.gethostname()
        self.consolelevel = int(self.config['DEBUG']['consolelevel'])
        self.logfilelevel = int(self.config['DEBUG']['logfilelevel'])
        self.logfile = str(self.config['DEBUG']['logfile'])
        self.geoBaseUrl = str(self.config['GeoChron']['base_url'])
        self.geoApiKey = str(self.config['GeoChron']['api_key'])
        self.geoSpotLayer = str(self.config['GeoChron']['contacts_layer'])
        self.geoSpotComponent = str(self.config['GeoChron']['contacts_component'])
        self.geoMsgLayer = str(self.config['GeoChron']['messages_layer'])
        self.geoMsgComponent = str(self.config['GeoChron']['messages_component'])
        self.geoMsgPosition = str(self.config['GeoChron']['messages_position'])
        self.geoMsgColor = str(self.config['GeoChron']['messages_color'])
        self.geoMsgFontSize = str(self.config['GeoChron']['messages_font_size'])
        self.geoGridNoCall = str(self.config['GeoChron']['grid_nocall'])
        self.geoGridNoColor = str(self.config['GeoChron']['grid_nocolor'])
        self.geoAuthEnabled = bool(strtobool(self.config['Auth']['enabled']))
        self.geoAuthToken = str(self.config['Auth']['token'])
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Supress those nasty SSL certificate warnings
        warnings.filterwarnings("ignore")
        
        # If flie logging is enabled, open the log file
        if not self.logfilelevel == 0:
            try:
                self.log_handle = open(self.logfile,'a',0)
            except:
                print ("ERROR Unable to open log file")

    def parse_json(self):
        """ Parse json message """
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements
        # It's a parser after all
        self.debug_log(self.log_entry,"parse_json: --Enter--")
        try:
            self.debug_log(self.log_info,"parse_json: Getting message from queue")
            msgJSON = msgQueue.get()
            self.debug_log(self.log_debug,"parse_json: Removing non-ascii garbage")
            msgJSON = str(re.sub(r'[^\x00-\x7f]',r'',msgJSON))
            self.debug_log(self.log_hidebug,"parse_json: Raw message: %s" %msgJSON)
            self.debug_log(self.log_info,"parse_json: Parsing JSON message from Client...")
            message = json.loads(msgJSON)
            msgQueue.task_done()
        except:
            message = {}

        if not message:
            self.debug_log(self.log_info,"parse_json: No JSON message to parse")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return

        self.debug_log(self.log_info,"parse_json: Got JSON message")
        try:
            typ = message.get('type', '')
            value = message.get('value', '')
            params = message.get('params', {})
        except:
            self.debug_log(self.log_error,"parse_json: Unable to parse JSON message.")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        
        if typ:
            self.debug_log(self.log_hidebug,"parse_json: -> typ: " + typ)
        if value:
            self.debug_log(self.log_hidebug,"parse_json: -> value: " + value)
        if params:
            self.debug_log(self.log_hidebug,"parse_json: -> params: ")
            self.debug_log(self.log_hidebug,params)
 
        # check for valid security token
        if self.geoAuthEnabled:
            auth = ""
            try:
                # remove non-ascii garbage
                auth = str(params['AUTH'])
                auth = str(re.sub(r'[^\x00-\x7f]',r'',auth))
                auth = auth.strip()
            except:
                auth = ""
                self.debug_log(self.log_debug,"parse_json: Unable to save JSON[AUTH].")

            if not auth == self.geoAuthToken:
                self.debug_log(self.log_smdr,"Authorization Failure.")
                self.debug_log(self.log_info,"parse_json: Authorization failed.")
                self.debug_log(self.log_entry,"parse_json: --Exit--\n")
                return
            
        # check for valid type
        if not typ:
            self.debug_log(self.log_info,"parse_json: Missing message TYPE")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return

        if typ == 'MESSAGE.CLEAR':
            self.debug_log(self.log_info,"parse_json: ---MESSAGE.CLEAR---")
            self.message_clear()
            self.debug_log(self.log_smdr,"Clear Messages")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'MESSAGE.TEST':
            self.debug_log(self.log_info,"parse_json: ---MESSAGE.TEST---")
            self.message_test()
            self.debug_log(self.log_smdr,"Test Messages")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'MESSAGE.SEND':
            self.debug_log(self.log_info,"parse_json: ---MESSAGE.SEND---")
            msgQ = ""
            try:
                # remove non-ascii garbage
                msgQ = str(params['MESSAGE'])
                msgQ = str(re.sub(r'[^\x00-\x7f]',r'',msgQ))
                msgQ = msgQ.strip()
                # limit message length to 40 characters
                msgQ = msgQ[:40]
            except:
                msgQ = ""
                self.debug_log(self.log_debug,"parse_json: Unable to save JSON[MESSAGE].")

            if not msgQ:
                self.debug_log(self.log_info,"parse_json: No message to send.")
                self.debug_log(self.log_entry,"parse_json: --Exit--\n")
                return

            # Write SMDR record
            self.debug_log(self.log_smdr,"Message: %s" %msgQ)
            
            # Now let's put the new message on the top of the stack
            self.debug_log(self.log_info,"parse_json: Found message")
            msgQ = msgQ + "\n"

            # If other messages already exist, add them below the new message
            # and remove the oldest if message count exceeds 5
            if len(self.message_data) > 0:
                self.debug_log(self.log_info,"parse_json: Found existing messages")
                msgIndex = self.message_data.split('\n')
                end = len(msgIndex)
                if end > 5:
                    end = 4
                for m in range(end):
                  msgQ = msgQ + msgIndex[m] + "\n" 
            
            # Update the message database, and send the messages
            self.debug_log(self.log_info,"parse_json: Updating Message Database")
            self.debug_log(self.log_hidebug,"parse_json: Message Q:\n" + msgQ)
            self.message_data = msgQ

            self.debug_log(self.log_info,"parse_json: Sending message...")
            self.message_send()
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'SPOT.CLEAR':
            self.debug_log(self.log_info,"parse_json: ---SPOT.CLEAR---")
            self.spot_clear()
            self.grid_clear()
            self.debug_log(self.log_smdr,"Clear Spots/Grids")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'SPOT.TEST':
            self.debug_log(self.log_info,"parse_json: ---SPOT.TEST---")
            self.spot_test()
            self.debug_log(self.log_smdr,"Test Spots")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'SPOT.SEND':
            self.debug_log(self.log_info,"parse_json: ---SPOT.SEND---")
            spotQ = ""
            try:
                # remove non-ascii garbage
                spotQ = str(params['SPOT'])
                spotQ = str(re.sub(r'[^\x00-\x7f]',r'',spotQ))
                spotQ = spotQ.strip()
            except:
                spotQ = ""
                self.debug_log(self.log_debug,"parse_json: Unable to save JSON[SPOT].")

            if not spotQ:
                self.debug_log(self.log_info,"parse_json: No spot to send.")
                self.debug_log(self.log_entry,"parse_json: --Exit--\n")
                return

            # Write SMDR record
            self.debug_log(self.log_smdr,"Spot: %s" %spotQ)

            # Now let's add the new spot to the stack
            self.debug_log(self.log_info,"parse_json: Updating Spot Database")
            self.spot_data = self.spot_data + spotQ + "\n"
            self.debug_log(self.log_hidebug,"parse_json: Spot Q:\n" + self.spot_data)
            
            self.debug_log(self.log_info,"parse_json: Sending spot...")
            self.spot_send()
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return

        if typ == 'SPOT.GRID':
            """
            Due to limitations in the current CSV component implementation,
            this function takes a different approach. It creates new
            point components for each new request and updates the grid
            database for later removal of the points.
            """
            self.debug_log(self.log_info,"parse_json: ---SPOT.GRID---")
            spotC = ""  # callsign [CALL]
            spotF = ""  # color [COLOR]
            spotG = ""  # gridsquare [GRID]
            spotQ = ""  # assembled command
            try:
                # remove non-ascii garbage
                spotC = str(params['CALL'])
                spotC = str(re.sub(r'[^\x00-\x7f]',r'',spotC))
                spotC = spotC.strip()
            except:
                spotC = self.geoGridNoCall
                self.debug_log(self.log_debug,"parse_json: Unable to save JSON[CALL].")
            try:
                # remove non-ascii garbage
                spotF = str(params['COLOR'])
                spotF = str(re.sub(r'[^\x00-\x7f]',r'',spotF))
                spotF = spotF.strip()
            except:
                spotF = self.geoGridNoColor
                self.debug_log(self.log_debug,"parse_json: Unable to save JSON[COLOR].")
            try:
                # remove non-ascii garbage
                spotG = str(params['GRID'])
                spotG = str(re.sub(r'[^\x00-\x7f]',r'',spotG))
                spotG = spotG.strip()
            except:
                spotG = ""
                self.debug_log(self.log_debug,"parse_json: Unable to save JSON[GRID].")

            if not spotG:
                self.debug_log(self.log_info,"parse_json: No grid to send.")
                self.debug_log(self.log_entry,"parse_json: --Exit--\n")
                return

            # Write SMDR record
            self.debug_log(self.log_smdr,"Grid: %s %s %s" %(spotC, spotG, spotF))

            self.debug_log(self.log_info,"parse_json: Processing grid")        
            lat,lng = None, None
            lat,lng = self.to_latlng(spotG)

            if lat==None or lng==None:
                self.debug_log(self.log_info,"parse_json: Unable to calculate lat/lon.")
                self.debug_log(self.log_entry,"parse_json: --Exit--\n")
                return

            self.debug_log(self.log_debug,"parse_json: Calculating parameters")
            try:
                url = self.geoBaseUrl + self.geoSpotLayer + "/component/" + \
                      spotC + "/?key=" + self.geoApiKey
                method = "post"
                params = {
                    'Type': 'Point',
                    'Label': spotC,
                    'ShowPoint': 'True',
                    'Lat': lat,
                    'Lng': lng,
                    'Color': spotF,
                    'Icon': {"ImageURL":"","ImageHash":"","Rotation":0.0}
                }
                self.debug_log(self.log_hidebug,"parse_json: url: %s" %url)
                self.debug_log(self.log_hidebug,"parse_json: method: %s" %method)
                self.debug_log(self.log_hidebug,"parse_json: params: %s" %params)
            except:
                self.debug_log(self.log_error,"parse_json: Error in calculating parameters")
                self.debug_log(self.log_entry,"parse_json: --Exit--\n")
                return

            # Now let's add the new grid to the stack, to track for later removal
            self.debug_log(self.log_info,"parse_json: Updating Grid Database")
            self.grid_data = self.grid_data + spotC + "\n"
            self.debug_log(self.log_hidebug,"parse_json: Grid Q:\n" + self.grid_data)
           
            self.debug_log(self.log_info,"parse_json: Sending grid to GeoChron...")
            self.send_GeoChron(method,url,params)
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return

        if typ == 'CLOSE':
            self.debug_log(self.log_info,"parse_json: ---CLOSE---")
            self.debug_log(self.log_critical,"parse_json: Client has terminated.")
            self.debug_log(self.log_critical,"---Shutting Down---\n")
            sys.exit(0)

        self.debug_log(self.log_error,"parse_json: Unreconized TYPE: %s" %typ)
        self.debug_log(self.log_entry,"parse_json: --Exit--\n")
        return

    def message_clear(self):
        """ Clears messages from GeoChron servers """
        self.debug_log(self.log_entry,"message_clear: --Enter--")
        try:
            self.message_data = ''
            self.debug_log(self.log_debug,"message_clear: Cleared Message Database in Memory")
            self.debug_log(self.log_debug,"message_clear: Size: " + str(len(self.message_data)))
        except:
            self.debug_log(self.log_error,"message_clear: Failed to clear Message Database")
            self.debug_log(self.log_entry,"message_clear: --Exit--\n")
            return
        self.message_send()
        self.debug_log(self.log_entry,"message_clear: --Exit--")

    def message_test(self):
        """ Sends test message to GeoChron servers """
        self.debug_log(self.log_entry,"message_test: --Enter--")
        try:
            self.message_data = ''
            self.message_data = self.message_data + "Hello World I\n"
            self.message_data = self.message_data + "Hello World II\n"
            self.debug_log(self.log_debug,"message_test: Upadated Message Database in Memory")
            self.debug_log(self.log_debug,"message_test: Size: " + str(len(self.message_data)))
        except:
            self.debug_log(self.log_error,"message_test: Failed to update Message Database")
            self.debug_log(self.log_entry,"message_test: --Exit--")
            return
        self.message_send()
        self.debug_log(self.log_entry,"message_test: --Exit--")

    def message_send(self):
        """ Sends message to GeoChron servers """
        self.debug_log(self.log_entry,"message_send: --Enter--")
        try:
            self.debug_log(self.log_debug,"message_send: Calculating parameters")
            # Fix for empty message data disabling custom layers
            #if not self.message_data:
            #    self.message_data = ' '
            url = self.geoBaseUrl + self.geoMsgLayer + "/component/" + \
                  self.geoMsgComponent + "/update?key=" + self.geoApiKey
            method = "post"
            params = {
                'Type': 'TextLegend',
                'Purpose': 'Message Display',
                'Priority': '0',
                'Position': self.geoMsgPosition,
                'TextColor': self.geoMsgColor,
                'BackgroundColor': '"rgba(0, 0, 0, 0)"',
                'FontSize': self.geoMsgFontSize,
                'Message': self.message_data
            }
            self.debug_log(self.log_hidebug,"message_send: url: %s" %url)
            self.debug_log(self.log_hidebug,"message_send: method: %s" %method)
            self.debug_log(self.log_hidebug,"message_send: params: %s" %params)
        except:
            self.debug_log(self.log_error,"message_send: Error in calculating parameters")
            self.debug_log(self.log_entry,"message_send: --Exit--")
            return
        self.debug_log(self.log_info,"message_send: Sending message to GeoChron...")
        self.send_GeoChron(method,url,params)
        self.debug_log(self.log_entry,"message_send: --Exit--")

    def spot_clear(self):
        """ Clears spots from GeoChron servers """
        self.debug_log(self.log_entry,"spot_clear: --Enter--")
        try:
            self.spot_data = ''
            self.debug_log(self.log_debug,"spot_clear: Cleared Spot Database in Memory")
            self.debug_log(self.log_debug,"spot_clear: Size: " + str(len(self.spot_data)))
        except:
            self.debug_log(self.log_error,"spot_clear: Failed to clear Spot Database")
            self.debug_log(self.log_entry,"spot_clear: --Exit--")
            return
        self.spot_send()
        self.debug_log(self.log_entry,"spot_clear: --Exit--")
        
    def spot_test(self):
        """ Sends test spots to GeoChron servers """
        self.debug_log(self.log_entry,"spot_test: --Enter--")
        try:
            self.spot_data = ''
            self.spot_data = self.spot_data + "Location,PostalCode,90212,Beverly Hills,#ff00ff\n"
            self.spot_data = self.spot_data + "Location,PostalCode,97045,Oregon City,#ff00ff\n"
            self.debug_log(self.log_debug,"spot_test: Upadated Spot Database in Memory")
            self.debug_log(self.log_debug,"spot_test: Size: " + str(len(self.spot_data)))
        except:
            self.debug_log(self.log_error,"spot_test: Failed to update Spot Database")
            self.debug_log(self.log_entry,"spot_test: --Exit--")
            return
        self.spot_send()
        self.debug_log(self.log_entry,"spot_test: --Exit--")

    def spot_send(self):
        """ Sends spots to GeoChron servers """
        self.debug_log(self.log_entry,"spot_send: --Enter--")
        try:
            self.debug_log(self.log_debug,"spot_send: Calculating parameters")
            url = self.geoBaseUrl + self.geoSpotLayer + "/component/" + \
                  self.geoSpotComponent + "/update?key=" + self.geoApiKey
            method = "post"
            params = {
                'Type': 'Csv',
                'Data': self.spot_data
            }
            self.debug_log(self.log_hidebug,"spot_send: url: %s" %url)
            self.debug_log(self.log_hidebug,"spot_send: method: %s" %method)
            self.debug_log(self.log_hidebug,"spot_send: params: %s" %params)
        except:
            self.debug_log(self.log_error,"spot_send: Error in calculating parameters")
            self.debug_log(self.log_entry,"spot_send: --Exit--")
            return
        self.debug_log(self.log_info,"spot_send: Sending spots to GeoChron...")
        self.send_GeoChron(method,url,params)
        self.debug_log(self.log_entry,"spot_send: --Exit--")

    def grid_clear(self):
        """ Clears points (aka grids) from GeoChron servers """
        self.debug_log(self.log_entry,"grid_clear: --Enter--")

        if len(self.grid_data) > 0:
            self.debug_log(self.log_info,"grid_clear: Grid database has entries")
            self.debug_log(self.log_debug,"grid_clear: Calculating parameters")
            try:
                method = "get"
                params = {
                    'Type': 'Point'
                }
            except:
                self.debug_log(self.log_error,"grid_clear: Error in calculating parameters")
                self.debug_log(self.log_entry,"grid_clear: --Exit--")
                return                

            # Now walk the grid database and remove each point component
            gridIndex = self.grid_data.split('\n')
            for point in gridIndex:
                try:
                    self.debug_log(self.log_debug,"grid_clear: Removing point %s" %point)
                    if not point:
                        self.debug_log(self.log_debug,"grid_clear: Reached end of grid database")
                        break
                    self.debug_log(self.log_debug,"grid_clear: Calculating url")
                    url = self.geoBaseUrl + self.geoSpotLayer + "/component/" + \
                        point + "/delete?key=" + self.geoApiKey
                    
                    self.debug_log(self.log_hidebug,"grid_clear: url: %s" %url)
                    self.debug_log(self.log_hidebug,"grid_clear: method: %s" %method)
                    self.debug_log(self.log_hidebug,"grid_clear: params: %s" %params)
                except:
                    self.debug_log(self.log_error,"grid_clear: Error in calculating url")
                    continue
                self.debug_log(self.log_info,"grid_clear: Clearing grid from GeoChron...")
                self.send_GeoChron(method,url,params)

        # Now clear the grid database
        try:
            self.grid_data = ''
            self.debug_log(self.log_debug,"grid_clear: Cleared Grid Database in Memory")
            self.debug_log(self.log_debug,"grid_clear: Size: " + str(len(self.grid_data)))
        except:
            self.debug_log(self.log_error,"grid_clear: Failed to clear Grid Database")

        self.debug_log(self.log_entry,"grid_clear: --Exit--")
        
    def send_GeoChron(self, method, url, params):
        """ Sends message to GeoChron servers """
        self.debug_log(self.log_entry,"send_GeoChron: --Enter--")
        if not method:
            self.debug_log(self.log_error,"send_GeoChron: Missing method.")
            self.debug_log(self.log_entry,"send_GeoChron: --Exit--")
            return
        if not url:
            self.debug_log(self.log_error,"send_GeoChron: Missing url.")
            self.debug_log(self.log_entry,"send_GeoChron: --Exit--")
            return
        if not params:
            self.debug_log(self.log_error,"send_GeoChron: Missing params.")
            self.debug_log(self.log_entry,"send_GeoChron: --Exit--")
            return

        self.debug_log(self.log_debug,"send_GeoChron: Sending request")
        try:
            if method == "get":
                self.debug_log(self.log_debug,"send_GeoChron: via GET.")
                resp = requests.get(url, json=params, verify=False)

            if method == "post":
                self.debug_log(self.log_debug,"send_GeoChron: via POST")
                resp = requests.post(url, json=params, verify=False)

            self.debug_log(self.log_debug,"send_GeoChron: Status: %s" %resp.status_code)
            self.debug_log(self.log_hidebug,"send_GeoChron: Text: %s" %resp.text)
        except:
            self.debug_log(self.log_error,"send_GeoChron: Error in sending request")

        self.debug_log(self.log_entry,"send_GeoChron: --Exit--")

    def debug_log(self, level, msg):
        """ Log debug message to console and/or file """
        if not level:
            return
        if not msg:
            return

        # Calculate tags
        tag = ''
        if level == self.log_smdr:
            tag = '[SMDR]'
        if level == self.log_critical:
            tag = '[CRITICAL]'
        if level == self.log_error:
            tag = '[ERROR]'
        if level == self.log_warning:
            tag = '[WARNING]'
        if level == self.log_info:
            tag = '[INFO]'

        # Calculate DateTime stamp
        mytime = datetime.datetime.utcnow()
        dg = mytime.strftime("%Y-%m-%d")
        tg = mytime.strftime("%H:%M:%S")

        # Format message compatible for machine procesing
        try:
            msgF = dg + "|" + tg + "|" + tag + "|" + msg
        except:
            msgF = dg + "|" + tg + "|" + tag + "|[object]"
        
        if level in range(1, self.consolelevel+1):
            print (msgF)
        if level in range(1, self.logfilelevel+1):
            self.log_handle.write(msgF)
            self.log_handle.write("\n")

    def to_latlng(self, gs):
            """
            Takes in a Maidenhead locator string (gridsquare) and converts it
            into a tuple of WGS-84 compatible (latitude, longitude).
            """
            self.debug_log(self.log_entry,"to_latlng: --Enter--")
            self.debug_log(self.log_debug,"to_latlng: Grid: %s" %gs)
            if len(gs) < 4:
                    self.debug_log(self.log_debug,"to_latlng: Invalid gridsquare specified.")
                    self.debug_log(self.log_entry,"to_latlng: --Exit--")
                    return None, None
            lat, lng = None, None
            if len(gs) > 4:
                    lng = self._to_lng(gs[0], int(gs[2]), gs[4])
                    lat = self._to_lat(gs[1], int(gs[3]), gs[5])
            else:
                    lng = self._to_lng(gs[0], int(gs[2]))
                    lat = self._to_lat(gs[1], int(gs[3]))

            # if either calc fails, return error
            if lat==None or lng==None:
                self.debug_log(self.log_debug,"to_latlng: lat: %s lng: %s" %(str(lat), str(lng)))
                self.debug_log(self.log_entry,"to_latlng: --Exit--")
                return None, None

            self.debug_log(self.log_debug,"to_latlng: lat: %s lng: %s" %(str(lat), str(lng)))
            self.debug_log(self.log_entry,"to_latlng: --Exit--")
            return round(lat, 3), round(lng, 3)

    def _to_lat(self, field, square, subsq=None):
            """
            Converts the specified field, square, and (optional) sub-square
            into a WGS-84 compatible latitude value.
            """
            self.debug_log(self.log_entry,"_to_lat: --Enter--")
            try:
                lat = (string.ascii_uppercase.index(field.upper()) * 10.0) - 90
                lat += square
                if subsq is not None:
                        lat += (string.ascii_lowercase.index(subsq.lower()) / 24.0)
                        lat += 1.25 / 60.0 
                else:
                        lat += 0.5
            except:
                self.debug_log(self.log_debug,"_to_lat: Unable to calculate lat")
                lat = None
                
            self.debug_log(self.log_entry,"_to_lat: --Exit--")
            return lat

    def _to_lng(self, field, square, subsq=None):
            """
            Converts the specified field, square, and (optional) sub-square
            into a WGS-84 compatible longitude value.
            """
            self.debug_log(self.log_entry,"_to_lng: --Enter--")
            try:
                lng = (string.ascii_uppercase.index(field.upper()) * 20.0) - 180
                lng += square * 2.0
                if subsq is not None:
                    lng += string.ascii_lowercase.index(subsq.lower()) / 12.0
                    lng += 2.5 / 60.0
                else:
                    lng += 1.0
            except:
                self.debug_log(self.log_debug,"_to_lng: Unable to calculate lng")
                lng = None
                
            self.debug_log(self.log_entry,"_to_lng: --Exit--")
            return lng

class udp_server:
    """ Class UDP Server """
    config = ""
    geoHost = ""
    geoPort = ""
    
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config')
        self.geoHost = self.config['GeoServer']['host']
        self.geoPort = self.config['GeoServer']['port']
        print("udp_server: Host: " + self.geoHost)
        print("udp_server: Port: " + self.geoPort)
        msgServer = threading.Thread(name='msgServer',target=self.run)
        msgServer.daemon = True
        msgServer.start()
        print("udp_server: Started > %s \n" % msgServer.is_alive())

    def run(self):
        try:
            addr = ""
            recv_buffer = ""
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((self.geoHost,int(self.geoPort)))
            while True:
                recv_buffer, addr = sock.recvfrom(65500)
                if sys.version_info.major < 3:
                    msg = str(recv_buffer)
                else:
                    msg = str(recv_buffer.decode('utf-8'))
                msgQueue.put(msg)
                recv_buffer = ""
        except socket.error as msg:
            sys.stderr.write("[ERROR] %s" % msg)
            sys.exit(2)

if __name__ == "__main__":
    msgQueue = {}

    # Python version specific functions
    if sys.version_info.major == 3:
        msgQueue = queue.Queue()
    elif sys.version_info.major == 2:
        msgQueue = Queue.Queue()
    else:
        raise NotImplementedError

    print("GeoServer v0.4 written by KK7JND")
    print("Starting UDP server...")
    S = udp_server()
    G = GeoServer()
    while True:
        while not msgQueue.empty():
            G.parse_json()
            #print("Inner loop")
        #print("Outer loop")
        time.sleep(5)
    G.sock.close()
