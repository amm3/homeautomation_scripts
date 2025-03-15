#!/usr/bin/env python3

import sys
import os
import argparse
import logging
import time
import requests
import json

DEFAULT_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
LOGGING_FORMAT = '%(asctime)s:%(levelname)s:%(message)s'

API_BASE_PATH = 'api'    # Base path 
API_SSL = False
API_PORT = None     # If none, use default for schema

def main():

    #global args
    global CONFIG_FILE_DEFAULT
    parser = argparse.ArgumentParser(description='Manage PiHole Teleporter Backups')
    parser.add_argument('--host1', '-1', type=str, help="Host #1 (read from)", required=True)
    parser.add_argument('--host2', '-2', type=str, help="Host #2 (write to)", required=True)
    parser.add_argument('--passwd', '-p', type=str, help="Password (for both)", required=True)
    parser.add_argument('--port', help="Non-standard port to use", default=None)
    parser.add_argument('--ssl', action="store_true", default=False, help="Connect via SSL")
    parser.add_argument("-v", action="store_true", default=False, help="Print extra info")
    parser.add_argument("-vv", action="store_true", default=False, help="Print (more) extra info")
    args = parser.parse_args()

    ######################################
    # Establish LOGLEVEL
    ######################################
    if args.vv:
        logging.basicConfig(format=LOGGING_FORMAT, datefmt=DEFAULT_TIME_FORMAT, level=logging.DEBUG)
    elif args.v:
        logging.basicConfig(format=LOGGING_FORMAT, datefmt=DEFAULT_TIME_FORMAT, level=logging.INFO)
    else:
        logging.basicConfig(format=LOGGING_FORMAT, datefmt=DEFAULT_TIME_FORMAT, level=logging.WARNING)

    # Update Settings
    global API_SSL, API_PORT
    API_SSL = args.ssl
    API_PORT = args.port

    # Authenticate to Both Servers
    auth_data1 = pihole_authenticate(args.host1, args.passwd)
    auth_data2 = pihole_authenticate(args.host2, args.passwd)

    # Download from Host #1
    backup_data = pihole_teleporter_download(args.host1, auth_data1)
    # Upload to Host #2
    pihole_teleporter_upload(args.host2, auth_data2, backup_data)

    # Deauthenticate Both Sessions
    pihole_del_authenticate(args.host1, auth_data1)
    pihole_del_authenticate(args.host2, auth_data2)

def pihole_authenticate(host, password):

    endpoint = '/auth'
    url = make_url(host, endpoint)
    log_debug(f"Using url: {url}")

    body = {'password':password}
    r = requests.post(url, json=body)
    if r.status_code != 200:
        log_fatal("Bad response from server: " + str(r))
    data = r.json()
    if not data['session']['valid']:
        log_fatal(f"Bad password authenticating to {host}")
    return data

def pihole_del_authenticate(host, auth_data):

    endpoint = '/auth'
    url = make_url(host, endpoint)
    log_debug(f"Using url: {url}")

    params = {'sid':auth_data['session']['sid']}
    r = requests.delete(url, params=params)
    if r.status_code != 204:
        log_fatal("Bad response from server: " + str(r))
    return r

def pihole_teleporter_download(host, auth_data):

    endpoint = '/teleporter'
    url = make_url(host, endpoint)
    log_debug(f"Using url: {url}")

    params = {'sid':auth_data['session']['sid']}
    r = requests.get(url, params=params)
    return r.content


def pihole_teleporter_upload(host, auth_data, backup_binary_data):

    endpoint = '/teleporter'
    url = make_url(host, endpoint)
    log_debug(f"Using url: {url}")

    params = {'sid':auth_data['session']['sid']}
    body = {
      "config": True,
      "dhcp_leases": True,
      "gravity": {
        "group": True,
        "adlist": True,
        "adlist_by_group": True,
        "domainlist": True,
        "domainlist_by_group": True,
        "client": True,
        "client_by_group": True
      }
    }
    file_data = {'file': ('backup.zip', backup_binary_data)}

    r = requests.post(url, params=params, json=body, files=file_data)
    if r.status_code != 200:
        log_fatal(f"Error uploading teleporter backup data to {host}: {r}")
    return r

def make_url(host, endpoint):

    global API_BASE_PATH, API_SSL, API_PORT

    if API_SSL:
        scheme = 'https'
    else:
        scheme = 'http'

    if API_PORT != None:
        port_txt = f":{API_PORT}"
    else:
        port_txt = ''

    return f"{scheme}://{host}{port_txt}/{API_BASE_PATH}{endpoint}"

##############################################################################
#
# Output and Logging Message Functions
#
##############################################################################
def write_out(message):
    info = {
      'levelname' : 'OUTPUT',
      'asctime'   : time.strftime(DEFAULT_TIME_FORMAT, time.localtime()),
      'message'   : message
    }
    print(LOGGING_FORMAT % info)

def log_fatal(msg, exit_code=-1):
    logging.critical("Fatal Err: %s\n" % msg)
    sys.exit(exit_code)

def log_warning(msg):
    logging.warning(msg)

def log_error(msg):
    logging.error(msg)

def log_info(msg):
    logging.info(msg)

def log_debug(msg):
    logging.debug(msg)

#
# Initial Setup and call to main()
#
if __name__ == '__main__':
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)  # reopen STDOUT unbuffered
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)
