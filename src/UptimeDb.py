import datetime
import json
from datetime import timedelta
from pathlib import Path


class SingleDayUptimeDb:
    def __init__(self, file):
        with open(file, "r") as f:
            self.file = file
            self.content: dict = json.load(f)

    def inc_screen_time(self, delta: timedelta):
        self.set_screen_time(self.get_screen_time() + delta)

    def set_screen_time(self, amount: timedelta):
        self.content['screen-time'] = amount.total_seconds()

    def get_screen_time(self):
        return timedelta(seconds=self.content.get('screen-time', 0))

    def get_apps(self) -> dict[str, timedelta]:
        result = dict()
        for key in self.content.get('applications', {}):
            name = key
            duration = timedelta(seconds=self.content.get('applications', {}).get(key, 0))
            result[name] = duration
        return result

    def set_apps(self, apps: dict[str, timedelta]):
        self.content['applications'] = {k: v.total_seconds() for k, v in apps.items()}

    def inc_apps(self, deltas: dict[str, timedelta]):
        apps = self.get_apps()
        for app in deltas:
            apps[app] = apps.get(app, timedelta(seconds=0)) + deltas[app]
        self.set_apps(apps)

    def save(self):
        with open(self.file, "w") as f:
            json.dump(self.content, f, indent=4)


class UptimeDb:
    def __init__(self, data_dir: Path):
        self.data_dir: Path = data_dir

    def update(self, update: 'UsageUpdate') -> 'AbsoluteUsage':
        file = self.get_file_for_today()
        db = SingleDayUptimeDb(file)

        if not update.absolute:
            db.inc_screen_time(update.screen_time)
            db.inc_apps(update.applications)
        else:
            db.set_screen_time(update.screen_time)
            db.set_apps(update.applications)
        db.save()
        return AbsoluteUsage(db.get_screen_time(), db.get_apps())

    def get(self) -> 'AbsoluteUsage':
        db = SingleDayUptimeDb(self.get_file_for_today())
        return AbsoluteUsage(db.get_screen_time(), db.get_apps())

    def get_file_for_today(self):
        self.data_dir.mkdir(exist_ok=True)

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        file_path = self.data_dir / today
        if not file_path.exists():
            with open(file_path, "w") as f:
                f.write("{}")
        return file_path


class AbsoluteUsage:
    def __init__(self, screen_time, applications):
        self.screen_time: timedelta = screen_time
        self.applications: dict[str, timedelta] = applications


class UsageUpdate:
    def __init__(self, screen_time, applications, absolute: bool):
        self.screen_time: timedelta = screen_time
        self.applications: dict[str, timedelta] = applications
        self.absolute: bool = absolute
