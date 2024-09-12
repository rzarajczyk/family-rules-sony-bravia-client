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

        turned_on = not cast.status.is_stand_by
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
        print(json.dumps(request, indent=4))
        requests.post(
            url=f"{self.host}/api/v1/report",
            json=request,
            auth=HTTPBasicAuth(self.user, self.token)
        ).raise_for_status()
