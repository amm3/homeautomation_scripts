#!/usr/bin/env python3

import sys
import os
from http.server import BaseHTTPRequestHandler,HTTPServer
from socketserver import ThreadingMixIn
import threading
import argparse
import re
import cgi
import subprocess
import time
import json

LOGLEVEL = 0

def main():

    #global args
    parser = argparse.ArgumentParser(description='HTTP Server')
    parser.add_argument('--port', type=int, default=8000, help='Listening port for HTTP Server')
    parser.add_argument('--ip', default='0.0.0.0', help='HTTP Server IP')
    parser.add_argument("-v", action="store_true", default=False, help="Print extra info")
    parser.add_argument("-vv", action="store_true", default=False, help="Print (more) extra info")
    args = parser.parse_args()

    ######################################
    # Establish LOGLEVEL
    ######################################
    global LOGLEVEL
    if args.vv:
        LOGLEVEL = 2
    elif args.v:
        LOGLEVEL = 1

    # Initial xset environment
    runCommandWithOutput(['xset', 'dpms', 's', '86400', '86400'], {'DISPLAY':':0'})
    runCommandWithOutput(['xset', 'dpms', 'dpms', '1800', '1800', '1800'], {'DISPLAY':':0'})

    server = SimpleHttpServer(args.ip, args.port)
    log_debug('HTTP Server listening on {}:{}'.format(args.ip, args.port))
    server.start()
    server.waitForThread()


class HTTPRequestHandler(BaseHTTPRequestHandler):
  def do_GET(self):
    results = {}
    if self.path == '/on':
        (status, out, err) = runCommandWithOutput(['xset', 'dpms', 'force', 'on'], {'DISPLAY':':0'})
    elif self.path == '/off':
        (status, out, err) = runCommandWithOutput(['xset', 'dpms', 'force', 'off'], {'DISPLAY':':0'})
    elif self.path.startswith('/set/'):
        try:
           timeout = int(self.path.split('/set/',1)[1])
        except ValueError:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            results['message'] = 'Must set integer value'
            self.wfile.write(json.dumps(results).encode('utf-8'))
            return
        timeout = str(timeout)
        (status, out, err) = runCommandWithOutput(['xset', 'dpms', timeout, timeout, timeout], {'DISPLAY':':0'})
    else:
        self.send_response(404)
        self.send_header('Content-Type', 'application/json')
        results['message'] = 'Invalid request'
        self.wfile.write(json.dumps(results).encode('utf-8'))
        return

    self.send_response(200)
    self.send_header('Content-Type', 'application/json')
    results['status'] = status
    results['cmd_out'] = str(out)
    results['cmd_err'] = str(err)
    self.wfile.write(json.dumps(results).encode('utf-8'))
    if status==0 and out==b'' and err==b'':
        log_debug("Command executed successfully")
    else:
        log_debug("Error: {}, Output: {}, Error: {}".format(status, out, err))

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
  allow_reuse_address = True

  def shutdown(self):
    self.socket.close()
    HTTPServer.shutdown(self)

class SimpleHttpServer():
  def __init__(self, ip, port):
    self.server = ThreadedHTTPServer((ip,port), HTTPRequestHandler)

  def start(self):
    self.server_thread = threading.Thread(target=self.server.serve_forever)
    self.server_thread.daemon = True
    self.server_thread.start()

  def waitForThread(self):
    self.server_thread.join()

  def stop(self):
    self.server.shutdown()
    self.waitForThread()

def runCommandWithOutput(parameterList, env={}, timeout=600):
    my_env=os.environ.copy()
    my_env.update(env)
    if type(parameterList) != tuple and type(parameterList) != list: parameterList = [parameterList]
    try:
        p = subprocess.Popen(parameterList, env=my_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as e:
        sys.stderr.write("Error running outside process:\n  %s\nErrno %s: %s\n" % (' '.join(parameterList), e.args[0], e.args[1]))
        return False
    timeExpired = False
    stime = time.time()
    while True:
        time.sleep(0.25)
        returnCode = p.poll()
        if returnCode != None: break
        if (time.time()-stime)>timeout:
            timeExpired = True
            break
    output = p.communicate()
    if timeExpired:
        try:
            import signal
            p.send_signal(signal.SIGINT)
            time.sleep(5)
            returnCode = p.poll()
            output = p.communicate()
            if returnCode != None:
                sys.stderr.write('Command exceeded timeout (%d s).  Sent INT to process.' % (timeout))
                return (returnCode, output[0], output[1])
        except:
            pass
        try:
            p.kill()
        except:
            pass
        sys.stderr.write('Command exceeded timeout (%d s).  Process terminated.\n' % (timeout))
    return (returnCode, output[0], output[1])

##############################################################################
#
# Output and Logging Message Functions
#
##############################################################################
def log_fatal(msg, exit_code=-1):
  sys.stderr.write("Fatal Err: %s\n" % msg)
  sys.exit(exit_code)

def log_info(msg):
  global LOGLEVEL
  if LOGLEVEL > 0:
    sys.stderr.write("Info: %s\n" % msg)

def log_error(msg):
  sys.stderr.write("Error: %s\n" % msg)

def log_debug(msg):
  global LOGLEVEL
  if LOGLEVEL > 1:
    sys.stderr.write("Debug: %s\n" % msg)

#
# Initial Setup and call to main()
#
if __name__ == '__main__':
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)  # reopen STDOUT unbuffered
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)
