#!/usr/bin/env python3

import sys
import os
import json
import paho.mqtt.client as mqtt
import subprocess
import select
import time

run_duration='30m'
sensor_map = {
    12345 : 'home/electricmeter',
    67890 : 'home/gasmeter',
}
username = 'rtl'
password = 'mqttpassword'
mqtt_server = '192.168.x.x'
LOGFILE = '/home/pi/rtlamr_log.txt'
DEBUGLEVEL = 0

def main():

    global client, username, password
    client = mqtt.Client()
    client.username_pw_set(username, password)
    client.connect(mqtt_server, 1883, 60)
    client.loop_start()

    while True:
        sys.stderr.write("Starting rtlamr...\n")
        run_rtlamr()

    client.loop_stop()
    client.disconnect()


def run_rtlamr():

    #filter_string = '-filterid='+','.join([str(x) for x in sensor_map.keys()])
    filter_string = None
    #cmd_list = ['/home/pi/go/bin/rtlamr', '-msgtype=idm,scm', '-format=json', '-duration={}'.format(run_duration)]
    cmd_list = ['/home/pi/go/bin/rtlamr', '-msgtype=scm', '-format=json', '-duration={}'.format(run_duration)]
    if filter_string!=None:
        cmd_list.append(filter_string)

    
    proc = subprocess.Popen(cmd_list, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    poller = select.poll()
    poller.register(proc.stdout)

    while True:
        events  = poller.poll(1)
        for fd,event in events:
            if event&select.POLLIN==select.POLLIN:
                read_lines(proc.stdout)
            elif event&select.POLLHUP==select.POLLHUP:
                read_lines(proc.stdout)
                return
        time.sleep(1)

def read_lines(fh):
    while True:
        line = fh.readline()
        if not line:
            return
        handle_json(line)

def handle_json(jtext):
    try:
        data = json.loads(jtext)
    except:
        sys.stderr.write("Error handling json text:\n  {}\n".format(jtext))
        return
    
    if 'Message' not in data:
        sys.stderr.write("Improperly formatted response:\n  {}\n".format(jtext))
        return
    msg = data['Message']

    # Patch message for IDM fields
    if 'ERTSerialNumber' in msg:
        msg['ID'] = msg['ERTSerialNumber']
    if 'ERTType' in msg:
        msg['Type'] = msg['ERTType']
    if 'LastConsumptionCount' in msg:
        msg['Consumption'] = msg['LastConsumptionCount']

    if msg['ID'] not in sensor_map:
        msg['Time'] = data['Time']
        log_info("{Time} {ID}:{Type} -> {Consumption}".format(**msg))
        return
    publish_mqtt(msg['ID'], msg['Consumption'])

def publish_mqtt(ID, reading):
    if ID not in sensor_map:
        return
    topic = sensor_map[ID]
    client.publish(topic, reading, 0, True)

def log_info(msg):
    if DEBUGLEVEL < 1:
        return
    output = "INFO: {}\n".format(msg)
    if LOGFILE==None:
        sys.stderr.write(output)
    else:
        open(LOGFILE, 'a').write(output)

#
# Initial Setup and call to main()
#
if __name__ == '__main__':
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)  # reopen STDOUT unbuffered
    try:
        r = main()
        sys.exit(r)
    except KeyboardInterrupt:
        client.loop_stop()
        client.disconnect()
        sys.exit(1)
