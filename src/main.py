from apscheduler.schedulers.blocking import BlockingScheduler
from bootstrap.bootstrap import start_service

from SonyBravia import SonyBraviaChecker

config, logger, timezone = start_service()

scheduler = BlockingScheduler(timezone=timezone)
device = SonyBraviaChecker(config)

scheduler.add_job(device.run, 'interval', seconds=config['interval-seconds'])

scheduler.start()
