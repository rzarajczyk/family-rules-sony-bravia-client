import json
import logging
import os
from datetime import timedelta
from pathlib import Path

import pychromecast
import requests
from bravia_tv import BraviaRC
from requests.auth import HTTPBasicAuth

from UptimeDb import UptimeDb, UsageUpdate


class SonyBraviaChecker:
    def __init__(self, config):
        self.logger = logging.getLogger('SonyBravia')
        self.tv_name = config['tv']['name']
        self.ip = config['tv']['ip']
        self.mac = config['tv']['mac']
        self.pin = config['tv']['pin']
        self.id = config['tv']['unique-id']
        self.db = UptimeDb(Path(os.getenv('STORAGE', '/app/data')))
        self.interval = timedelta(seconds=config['interval-seconds'])

        self.host = config['family-rules-server']['host']
        self.user = config['family-rules-server']['user']
        self.instance_id = config['family-rules-server']['instance-id']
        self.token = config['family-rules-server']['token']

        requests.post(
            url=f"{self.host}/api/v2/launch",
            headers={'Content-Type': 'application/json'},
            json={
                "version": "3.0",
                "availableStates": [
                    {
                        "deviceState": "ACTIVE",
                        "title": "Active",
                        "icon": "<path d=\"m424-296 282-282-56-56-226 226-114-114-56 56 170 170Zm56 216q-83 0-156-31.5T197-197q-54-54-85.5-127T80-480q0-83 31.5-156T197-763q54-54 127-85.5T480-880q83 0 156 31.5T763-763q54 54 85.5 127T880-480q0 83-31.5 156T763-197q-54 54-127 85.5T480-80Zm0-80q134 0 227-93t93-227q0-134-93-227t-227-93q-134 0-227 93t-93 227q0 134 93 227t227 93Zm0-320Z\"/>",
                        "description": None
                    },
                    {
                        "deviceState": "TURNED_OFF",
                        "title": "Turned off",
                        "icon": "<path d=\"M480-80q-83 0-156-31.5T197-197q-54-54-85.5-127T80-480q0-84 31.5-156.5T197-763l56 56q-44 44-68.5 102T160-480q0 134 93 227t227 93q134 0 227-93t93-227q0-67-24.5-125T707-707l56-56q54 54 85.5 126.5T880-480q0 83-31.5 156T763-197q-54 54-127 85.5T480-80Zm-40-360v-440h80v440h-80Z\"/>",
                        "description": None
                    }
                ]
            },
            auth=HTTPBasicAuth(self.instance_id, self.token)
        ).raise_for_status()

    def run(self):
        try:
            turned_on, app = self.get_now_playing()
            state = 'ACTIVE'

            if turned_on:
                update = UsageUpdate(
                    screen_time=self.interval,
                    applications={app: self.interval} if app is not None else {},
                    absolute=False
                )
                usage = self.db.update(update)

                state = self.report(usage)
            else:
                state = self.report(None)

            self.handle_state(state)
        except Exception as e:
            logging.error("Error occured", e)

    def get_now_playing(self):
        bravia = BraviaRC(self.ip, mac=self.mac)
        bravia.connect(self.pin, self.id, self.id)
        turned_on = bravia.get_power_status() == 'active'
        app = None

        logging.info("Power: " + bravia.get_power_status())

        if turned_on:

            cast = pychromecast.get_chromecast_from_host(
                host=(self.ip, None, self.id, self.id, self.id),
                tries=1,
                retry_wait=0,
                timeout=5.0
            )
            try:
                cast.wait(timeout=5.0)
                app = cast.status.display_name
                logging.info(cast.status)
            finally:
                cast.disconnect(timeout=5.0)
        return turned_on, app

    def handle_state(self, state):
        if state == 'TURNED_OFF':
            logging.info("Forcing turning TV off...")
            bravia = BraviaRC(self.ip, mac=self.mac)
            bravia.connect(self.pin, self.id, self.id)
            bravia.turn_off()

    def report(self, usage):
        request = {
            "instanceId": self.instance_id,
        }
        if usage is not None:
            request = {
                'screenTime': usage.screen_time.total_seconds(),
                'applications': {app: time.total_seconds() for app, time in usage.applications.items()}
            }
        response = requests.post(
            url=f"{self.host}/api/v2/report",
            json=request,
            auth=HTTPBasicAuth(self.instance_id, self.token)
        )
        response.raise_for_status()
        return response.json()['deviceState']
