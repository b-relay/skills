#!/usr/bin/env python3
"""Behavior tests for babysit:until's watch script."""

import datetime
import importlib.machinery
import importlib.util
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time
import unittest

WATCH = pathlib.Path(__file__).resolve().parents[1] / 'plugins/babysit/skills/until/scripts/watch'


def watch(*args, env=None):
    started = time.monotonic()
    result = subprocess.run([sys.executable, str(WATCH), *args], capture_output=True, text=True, timeout=30,
                            env=None if env is None else {**os.environ, **env})
    return result, time.monotonic() - started


class WatchTests(unittest.TestCase):
    def test_time_deadline_exits_0(self):
        result, elapsed = watch('1s')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('reached', result.stdout)
        self.assertGreaterEqual(elapsed, 1)

    def test_condition_met_exits_0_with_last_output_line(self):
        with tempfile.TemporaryDirectory() as scratch:
            ready = pathlib.Path(scratch) / 'ready'
            subprocess.Popen(['sh', '-c', f'sleep 1; touch {ready}'])
            result, _ = watch('10s', '--every', '0.2', '--', 'sh', '-c', f'test -e {ready} && echo all green')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, r'^met after \d+s: all green$')

    def test_condition_never_met_exits_2(self):
        result, _ = watch('1s', '--every', '0.2', '--', 'false')
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('deadline', result.stdout)

    def test_slow_command_cannot_outlast_the_deadline(self):
        result, elapsed = watch('1s', '--', sys.executable, '-c', 'import time; time.sleep(5)')
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertLess(elapsed, 3)

    def test_timeout_stops_the_command_and_its_children(self):
        with tempfile.TemporaryDirectory() as scratch:
            marker = pathlib.Path(scratch) / 'marker'
            result, _ = watch('1s', '--', 'sh', '-c', f'(sleep 2; touch {marker}) & wait')
            time.sleep(2.5)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertFalse(marker.exists(), 'a child of the timed-out command kept running')

    def test_ctrl_c_stops_the_command_too(self):
        with tempfile.TemporaryDirectory() as scratch:
            marker = pathlib.Path(scratch) / 'marker'
            watcher = subprocess.Popen([sys.executable, str(WATCH), '10s', '--', 'sh', '-c', f'sleep 2; touch {marker}'],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(0.5)
            watcher.send_signal(signal.SIGINT)
            self.assertEqual(watcher.wait(timeout=5), 130)
            time.sleep(2.5)
            self.assertFalse(marker.exists(), 'the command kept running after Ctrl-C')

    def test_success_counts_even_when_an_escaped_child_holds_the_output(self):
        escape = 'import subprocess; subprocess.Popen(["sleep", "3"], start_new_session=True)'
        result, elapsed = watch('5s', '--', sys.executable, '-c', escape)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertLess(elapsed, 2)

    def test_success_counts_even_when_a_background_child_holds_the_output(self):
        result, elapsed = watch('5s', '--', 'sh', '-c', 'sleep 2 & exit 0')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertLess(elapsed, 1.5)

    def test_children_of_a_failed_attempt_are_stopped(self):
        with tempfile.TemporaryDirectory() as scratch:
            marker = pathlib.Path(scratch) / 'marker'
            result, _ = watch('1s', '--every', '5', '--', 'sh', '-c',
                              f'(sleep 2; touch {marker}) >/dev/null 2>&1 & exit 1')
            time.sleep(2.5)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertFalse(marker.exists(), 'a child of a failed attempt kept running')

    def test_clock_time_waits_for_that_time(self):
        soon = (datetime.datetime.now() + datetime.timedelta(seconds=2)).strftime('%H:%M:%S')
        result, elapsed = watch(soon)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertGreaterEqual(elapsed, 1)

    def test_clock_time_already_past_waits_for_tomorrow(self):
        past = (datetime.datetime.now() - datetime.timedelta(seconds=5)).strftime('%H:%M:%S')
        with self.assertRaises(subprocess.TimeoutExpired):
            subprocess.run([sys.executable, str(WATCH), past], capture_output=True, timeout=2)

    def test_clock_time_already_past_lands_on_the_next_day(self):
        loader = importlib.machinery.SourceFileLoader('watch_script', str(WATCH))
        script = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
        loader.exec_module(script)
        now = datetime.datetime(2026, 3, 10, 18, 0).astimezone()
        deadline = script.parse_deadline('17:00', now)
        self.assertEqual((deadline.date(), deadline.hour), (datetime.date(2026, 3, 11), 17))

    def test_a_far_deadline_does_not_crash(self):
        result, _ = watch('9999-12-31T23:59:59+00:00', '--', 'true')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_huge_retry_interval_does_not_crash(self):
        args = [sys.executable, str(WATCH), '9999-12-31T23:59:59+00:00', '--every', '1000000000000', '--', 'false']
        with self.assertRaises(subprocess.TimeoutExpired):
            subprocess.run(args, capture_output=True, timeout=2)

    def test_an_ascii_only_output_encoding_does_not_override_success(self):
        result, _ = watch('5s', '--', sys.executable, '-c', 'import os; os.write(1, bytes([255]))',
                          env={'PYTHONIOENCODING': 'ascii'})
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_utc_z_timestamp_is_accepted(self):
        result, _ = watch('2000-01-01T00:00:00Z')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_success_with_undecodable_output_exits_0(self):
        result, _ = watch('5s', '--', sys.executable, '-c', 'import os; os.write(1, bytes([255]))')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith('met after'))

    def test_usage_error_is_one_line(self):
        for args in (['soon'], []):
            with self.subTest(args=args):
                result, _ = watch(*args)
                self.assertEqual(result.returncode, 64)
                self.assertEqual(len((result.stdout + result.stderr).strip().splitlines()), 1,
                                 result.stdout + result.stderr)

    def test_every_sets_the_time_between_attempt_starts(self):
        with tempfile.TemporaryDirectory() as scratch:
            log = pathlib.Path(scratch) / 'starts'
            check = f'import time; open({str(log)!r}, "a").write(f"{{time.monotonic()}}\\n"); time.sleep(0.5); raise SystemExit(1)'
            watch('4s', '--every', '1', '--', sys.executable, '-c', check)
            starts = [float(line) for line in log.read_text().split()]
        gaps = [later - earlier for earlier, later in zip(starts, starts[1:])]
        self.assertGreaterEqual(len(starts), 4, starts)
        self.assertLess(max(gaps[:-1]), 1.3, gaps)

    def test_sigterm_stops_the_command_too(self):
        with tempfile.TemporaryDirectory() as scratch:
            marker = pathlib.Path(scratch) / 'marker'
            watcher = subprocess.Popen([sys.executable, str(WATCH), '10s', '--', 'sh', '-c', f'sleep 2; touch {marker}'],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(0.5)
            watcher.terminate()
            self.assertEqual(watcher.wait(timeout=5), 143)
            time.sleep(2.5)
            self.assertFalse(marker.exists(), 'the command kept running after SIGTERM')

    def test_bad_input_exits_64(self):
        for args in (['soon'], ['25:00'], ['5s', '--every'], ['5s', '--every', 'nan', '--', 'true'],
                     ['5s', '--'], ['5s', '--every', '1'], ['999999999999999h'], ['1' * 4301 + 's'],
                     ['5s', '--', 'no-such-command-for-watch']):
            with self.subTest(args=args):
                result, _ = watch(*args)
                self.assertEqual(result.returncode, 64, result.stdout + result.stderr)
                self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
