import time

from bootstrap.bootstrap import start_service

from SonyBravia import SonyBraviaChecker

config, logger, timezone = start_service()

device = SonyBraviaChecker(config)

while True:
    device.run()
    time.sleep(config['interval-seconds'])
