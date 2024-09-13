import json
import logging
import os
from datetime import timedelta
from pathlib import Path

import pychromecast
import requests
from requests.auth import HTTPBasicAuth

from UptimeDb import UptimeDb, UsageUpdate


class SonyBraviaChecker:
    def __init__(self, config):
        self.logger = logging.getLogger('SonyBravia')
        self.tv_name = config['tv']['name']
        self.ip = config['tv']['ip']
        self.db = UptimeDb(Path(os.getenv('STORAGE', '/app/data')))
        self.interval = timedelta(seconds=config['interval-seconds'])

        self.host = config['family-rules-server']['host']
        self.user = config['family-rules-server']['user']
        self.instance_id = config['family-rules-server']['instance-id']
        self.token = config['family-rules-server']['token']

        requests.post(
            url=f"{self.host}/api/v1/launch",
            json={
                "instanceId": self.instance_id,
                "version": "v1",
                "availableStates": [
                    {
                        "deviceState": "ACTIVE",
                        "title": "Active",
                        "icon": "<path d=\"m424-296 282-282-56-56-226 226-114-114-56 56 170 170Zm56 216q-83 0-156-31.5T197-197q-54-54-85.5-127T80-480q0-83 31.5-156T197-763q54-54 127-85.5T480-880q83 0 156 31.5T763-763q54 54 85.5 127T880-480q0 83-31.5 156T763-197q-54 54-127 85.5T480-80Zm0-80q134 0 227-93t93-227q0-134-93-227t-227-93q-134 0-227 93t-93 227q0 134 93 227t227 93Zm0-320Z\"/>",
                        "description": None
                    }
                ]
            },
            auth=HTTPBasicAuth(self.user, self.token)
        ).raise_for_status()

    def run(self):
        try:
            turned_on, app = self.get_now_playing()

            if turned_on:
                update = UsageUpdate(
                    screen_time=self.interval,
                    applications={app: self.interval} if app is not None else {},
                    absolute=False
                )
                usage = self.db.update(update)

                self.report(usage)
        except Exception as e:
            logging.error("Error occured", e)

    def get_now_playing(self):
        chromecasts, browser = pychromecast.get_listed_chromecasts(
            friendly_names=[self.tv_name],
            known_hosts=[self.ip],
            discovery_timeout=10
        )
        cast = chromecasts[0]
        cast.wait()

        turned_on = cast.status.display_name is not None
        app = cast.status.display_name
        logging.info(cast.status)

        browser.stop_discovery()
        return turned_on, app

    def report(self, usage):
        request = {
            "instanceId": self.instance_id,
            'screenTime': usage.screen_time.total_seconds(),
            'applications': {app: time.total_seconds() for app, time in usage.applications.items()}
        }
        requests.post(
            url=f"{self.host}/api/v1/report",
            json=request,
            auth=HTTPBasicAuth(self.user, self.token)
        ).raise_for_status()
