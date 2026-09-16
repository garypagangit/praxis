"""Offline cloud-control safety tests. No AWS connections or account changes."""
import copy
import datetime as dt
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import cloud_d0 as cloud


class FakeAWS:
    class MissingSchedule(Exception):
        pass

    def __init__(self, settings):
        self.settings = settings
        self.state = "stopped"
        self.schedules = {}
        self.starts = []
        self.stops = []
        self.deletes = []
        self.commands = []
        self.reply_status = "Success"
        self.start_error = False
        self.schedule_tamper = None
        self.exceptions = type("Exceptions", (), {"ResourceNotFoundException": self.MissingSchedule})

    def client(self, name, **kwargs):
        return self

    def get_caller_identity(self):
        return {"Account": self.settings["account"]}

    def describe_instances(self, **kwargs):
        return {"Reservations": [{"OwnerId": self.settings["account"], "Instances": [{
            "InstanceId": self.settings["instance"], "InstanceType": "g5.xlarge", "State": {"Name": self.state}
        }]}]}

    def describe_instance_attribute(self, **kwargs):
        return {"InstanceInitiatedShutdownBehavior": {"Value": "stop"}}

    def describe_instance_information(self, **kwargs):
        return {"InstanceInformationList": []}

    def create_schedule(self, **kwargs):
        schedule = copy.deepcopy(kwargs)
        schedule["Arn"] = "arn:aws:scheduler:" + self.settings["region"] + ":" + self.settings["account"] + ":schedule/default/" + kwargs["Name"]
        self.schedules[kwargs["Name"]] = schedule
        return {"ScheduleArn": schedule["Arn"]}

    def get_schedule(self, Name, **kwargs):
        if Name not in self.schedules:
            raise self.MissingSchedule()
        schedule = copy.deepcopy(self.schedules[Name])
        if self.schedule_tamper:
            self.schedule_tamper(schedule)
        return schedule

    def delete_schedule(self, Name, **kwargs):
        self.deletes.append(Name)
        self.schedules.pop(Name)
        return {}

    def start_instances(self, InstanceIds):
        self.starts.append(InstanceIds)
        self.state = "running"
        if self.start_error:
            raise TimeoutError("Ambiguous start response")
        return {"StartingInstances": [{"InstanceId": self.settings["instance"]}]}

    def stop_instances(self, InstanceIds):
        self.stops.append(InstanceIds)
        self.state = "stopping"
        return {"StoppingInstances": [{"InstanceId": self.settings["instance"]}]}

    def send_command(self, **kwargs):
        self.commands.append(kwargs)
        return {"Command": {"CommandId": "test-command-" + str(len(self.commands))}}

    def get_command_invocation(self, **kwargs):
        return {"Status": self.reply_status, "ResponseCode": 0 if self.reply_status == "Success" else 1}


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.settings = {"profile": "test-only", "account": "000000000000", "region": "us-east-1",
            "instance": "i-00000000000000000", "bucket": "test-only-bucket", "prefix": "test-only/d0/",
            "stop_role_arn": "arn:aws:iam::000000000000:role/test-only-stop"}
        self.settings_path = self.root / "settings.json"
        self.settings_path.write_text(json.dumps(self.settings))
        self.now = dt.datetime(2026, 9, 15, 12, tzinfo=dt.timezone.utc)
        self.aws = FakeAWS(self.settings)
        self.controller = cloud.Controller(self.settings_path, session=self.aws, clock=lambda: self.now)
        self.identity = {"path": "test", "sha256": "0" * 64, "commit": "0" * 40}
        self.script = self.root / "worker.sh"
        self.script.write_text("#!/bin/sh\ntrue\n")

    def start(self):
        with patch.object(cloud, "committed_identity", return_value=self.identity):
            return self.controller.start(self.root / "protocol", self.root / "freeze")

    def test_start_one_host_after_verified_schedule(self):
        self.start()
        active = self.controller.active()
        self.assertEqual(self.aws.starts, [[self.settings["instance"]]])
        self.assertEqual(cloud.parse_stamp(active["scheduled_stop_utc"]) - self.now, dt.timedelta(minutes=26))
        self.assertEqual(cloud.parse_stamp(active["worker_deadline_utc"]) - self.now, dt.timedelta(minutes=22))
        self.assertTrue(all(active["watchdog_checks"].values()))

    def test_bad_watchdog_never_starts_host(self):
        self.aws.schedule_tamper = lambda schedule: schedule.update(State="DISABLED")
        with self.assertRaises(ValueError):
            self.start()
        self.assertEqual(self.aws.starts, [])
        self.assertEqual(len(self.aws.schedules), 1)
        self.assertTrue(self.controller.active()["gate_failed"])

    def test_wrong_account_never_creates_schedule(self):
        self.aws.get_caller_identity = lambda: {"Account": "111111111111"}
        with self.assertRaises(ValueError):
            self.start()
        self.assertEqual(self.aws.schedules, {})
        self.assertEqual(self.aws.starts, [])

    def test_running_host_is_not_taken_over(self):
        self.aws.state = "running"
        with self.assertRaises(ValueError):
            self.start()
        self.assertEqual(self.aws.schedules, {})

    def test_slow_preflight_does_not_start_against_stale_deadline(self):
        original = self.aws.create_schedule
        def slow_schedule(**kwargs):
            result = original(**kwargs)
            self.now += dt.timedelta(seconds=121)
            return result
        self.aws.create_schedule = slow_schedule
        with self.assertRaises(ValueError):
            self.start()
        self.assertEqual(self.aws.starts, [])
        self.assertEqual(len(self.aws.schedules), 1)

    def test_settings_identity_cannot_change_after_start(self):
        self.start()
        self.controller.settings["instance"] = "i-11111111111111111"
        with self.assertRaises(ValueError):
            self.controller.stop()
        self.assertEqual(self.aws.stops, [])

    def test_ambiguous_start_keeps_watchdog_blocks_restart(self):
        self.aws.start_error = True
        with self.assertRaises(TimeoutError):
            self.start()
        self.assertEqual(len(self.aws.schedules), 1)
        self.assertTrue(self.controller.active()["gate_failed"])
        self.aws.state = "stopped"
        with self.assertRaises(ValueError):
            self.start()
        self.assertEqual(len(self.aws.starts), 1)
        self.assertEqual(self.aws.deletes, [])

    def test_send_absolute_deadline_includes_delivery(self):
        self.start()
        self.now += dt.timedelta(minutes=6)
        with self.assertRaises(ValueError):
            self.controller.send(self.script, 900)
        self.assertEqual(self.aws.commands, [])
        self.controller.send(self.script, 800)
        self.assertEqual(self.aws.commands[0]["Parameters"]["executionTimeout"], ["800"])

    def test_no_send_after_minute_22(self):
        self.start()
        self.now += dt.timedelta(minutes=22)
        with self.assertRaises(ValueError):
            self.controller.send(self.script, 30)
        self.assertEqual(self.aws.commands, [])

    def test_only_one_pending_command(self):
        self.start()
        self.controller.send(self.script, 900)
        with self.assertRaises(ValueError):
            self.controller.send(self.script, 100)
        self.assertEqual(len(self.aws.commands), 1)

    def test_failed_worker_blocks_further_processing(self):
        self.start()
        self.controller.send(self.script, 900)
        self.aws.reply_status = "Failed"
        self.controller.poll("test-command-1")
        with self.assertRaises(ValueError):
            self.controller.send(self.script, 100)
        self.assertTrue(self.controller.active()["gate_failed"])

    def test_unowned_command_cannot_be_polled(self):
        self.start()
        with self.assertRaises(ValueError):
            self.controller.poll("not-ours")

    def test_stop_retains_watchdog_until_stopped(self):
        self.start()
        self.controller.stop()
        result = self.controller.finalize()
        self.assertTrue(result["status"].startswith("PENDING_"))
        self.assertEqual(self.aws.deletes, [])
        self.assertEqual(self.aws.stops, [[self.settings["instance"]]])

    def test_finalize_deletes_only_owned_schedule_after_stopped(self):
        self.start()
        own = self.controller.active()["schedule"]
        self.aws.schedules["unrelated"] = {"do_not_touch": True}
        self.aws.state = "stopped"
        self.now += dt.timedelta(minutes=18)
        result = self.controller.finalize()
        self.assertEqual(result["status"], "CLOSED_VERIFIED_STOPPED")
        self.assertEqual(self.aws.deletes, [own])
        self.assertIn("unrelated", self.aws.schedules)
        self.assertAlmostEqual(result["approximate_total_with_allowance_usd"], 5 + .3 * 1.006)
        self.assertEqual(self.controller.finalize()["status"], "CLOSED_VERIFIED_STOPPED")

    def test_finalize_refuses_tampered_watchdog_target(self):
        self.start()
        self.aws.state = "stopped"
        self.aws.schedule_tamper = lambda schedule: schedule["Target"].update(Input='{"InstanceIds":["other-host"]}')
        with self.assertRaises(ValueError):
            self.controller.finalize()
        self.assertEqual(self.aws.deletes, [])

    def test_late_observation_is_reported_as_cap_miss(self):
        self.start()
        self.aws.state = "stopped"
        self.now += dt.timedelta(minutes=31)
        self.controller.finalize()
        self.assertFalse(self.controller.active()["host_time_cap_observed"])

    def test_transfer_scope_and_cost_cap(self):
        for key in ["another-prefix/a", "test-only/d0/../a", "test-only/d0\\x", "test-only/d0//x"]:
            with self.assertRaises(ValueError):
                cloud.validate_key(self.settings, key)
        self.assertEqual(cloud.validate_key(self.settings, "test-only/d0/results/a"), "test-only/d0/results/a")
        with self.assertRaises(ValueError):
            cloud.validate_settings({**self.settings, "usd_per_hour": 11})


class GitIdentityTests(unittest.TestCase):
    def test_exact_git_bytes_and_uncommitted_edit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            def git(*arguments):
                return subprocess.check_output(["git", *arguments], cwd=root, stderr=subprocess.DEVNULL)
            git("init")
            git("config", "user.name", "Offline Test")
            git("config", "user.email", "offline@example.invalid")
            git("config", "core.autocrlf", "false")
            file = root / "FREEZE.json"
            file.write_bytes(b'{"frozen": true}\n')
            git("add", "FREEZE.json")
            git("commit", "-m", "Offline fixture")
            self.assertEqual(cloud.committed_identity(file)["path"], "FREEZE.json")
            file.write_bytes(b'{"frozen": true}\r\n')
            with self.assertRaises(ValueError):
                cloud.committed_identity(file)


if __name__ == "__main__":
    unittest.main(verbosity=2)
