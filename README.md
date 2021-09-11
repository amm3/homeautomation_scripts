# Home Automation (Misc) Scripts
## screen_server

A python web server to control dpms (Display Power Management Signaling) via simple GET requests. Built for integration with Home Assistant, using the rest_command service.

#### To run from systemd, create a service file at /etc/systemd/system/screenweb.service:

```
[Unit]
Description=Web Service for managing screen status
After=screenweb.service

[Service]
ExecStart=/bin/sh -c "/usr/bin/python3 /home/pi/screen_server.py"
WorkingDirectory=/home/pi
StandardOutput=inherit
StandardError=inherit
Restart=always
User=pi
Group=pi

[Install]
WantedBy=multi-user.target
```


### Home Assistant
#### configuration.yaml

```
rest_command:

  pidisplay_on:
    url: http://raspberrypi.local:8000/on
    method: GET
    content_type:  'application/json; charset=utf-8'

  pidisplay_off:
    url: http://raspberrypi.local:8000/off
    method: GET
    content_type:  'application/json; charset=utf-8'

  pidisplay_set:
    url: "{{ 'http://raspberrypi.local:8000/set/' + value|string }}"
    method: GET
    content_type:  'application/json; charset=utf-8'
```

#### In Automation

- Turn On
```
  action:
  - service: rest_command.pidisplay_on
```
- Turn Off
```
  action:
  - service: rest_command.pidisplay_off
```
- Set Timeout
```
  action:
  - service: rest_command.pidisplay_set
    data:
      value: 3600
```

