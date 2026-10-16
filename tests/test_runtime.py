from __future__ import annotations

import io
import json
import os
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

from voice_dubbing_runtime import VoiceRuntime
from voice_dubbing_runtime.errors import (
    CANCELLED,
    INVALID_REQUEST,
    RUNTIME_NOT_FOUND,
    SYNTHESIS_FAILED,
    VoiceRuntimeError,
)
from voice_dubbing_runtime.runtime import MARKER_PREFIX


class VoiceRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.runs = self.base / "runs"
        self.runtime = VoiceRuntime(
            working_directory=self.base,
            runs_root=self.runs,
            timeout_seconds=1,
        )
        self.job_id = str(uuid.uuid4())

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def process(self, stdout: str, returncode: int = 0, stderr: str = "") -> mock.Mock:
        process = mock.Mock()
        process.stdin = mock.Mock()
        process.stdout = io.StringIO(stdout)
        process.stderr = io.StringIO(stderr)
        process.returncode = returncode
        process.wait.return_value = returncode
        process.pid = 0
        return process

    def result_path(self) -> Path:
        path = self.runs / self.job_id / "result.json"
        path.parent.mkdir(parents=True)
        return path

    def success_marker(self, result_path: Path | None = None) -> str:
        return MARKER_PREFIX + json.dumps(
            {
                "type": "result",
                "status": "success",
                "job_id": self.job_id,
                "result_path": str(result_path or self.result_path()),
            }
        ) + "\n"

    def write_success_result(self, *, job_id: str | None = None) -> Path:
        path = self.result_path()
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "success",
                    "job_id": job_id or self.job_id,
                    "output_audio": "generated.wav",
                }
            ),
            encoding="utf-8",
        )
        return path

    def synthesize(self) -> dict:
        with mock.patch("voice_dubbing_runtime.runtime.uuid.uuid4", return_value=self.job_id):
            return self.runtime.synthesize(profile_id="voice_1", text="Hello")

    @mock.patch("voice_dubbing_runtime.runtime.subprocess.Popen")
    def test_capabilities_and_profiles_use_existing_json_commands(self, popen: mock.Mock) -> None:
        popen.side_effect = [
            self.process('{"schema_version":1,"engines":[]}'),
            self.process('{"schema_version":1,"profiles":[{"profile_id":"voice_1"}]}'),
            self.process('{"profile_id":"voice_1"}'),
        ]

        self.assertEqual([], self.runtime.capabilities()["engines"])
        self.assertEqual([{"profile_id": "voice_1"}], self.runtime.list_profiles())
        self.assertEqual("voice_1", self.runtime.get_profile("voice_1")["profile_id"])

        commands = [call.args[0] for call in popen.call_args_list]
        self.assertEqual(["capabilities", "--json"], commands[0][-2:])
        self.assertEqual(["profiles", "list", "--json"], commands[1][-3:])
        self.assertEqual(["profiles", "get", "--profile-id", "voice_1", "--json"], commands[2][-5:])

    @mock.patch("voice_dubbing_runtime.runtime.subprocess.Popen")
    def test_synthesize_returns_matching_durable_worker_result(self, popen: mock.Mock) -> None:
        result_path = self.write_success_result()
        process = self.process(self.success_marker(result_path))
        popen.return_value = process

        result = self.synthesize()

        self.assertEqual("generated.wav", result["output_audio"])
        self.assertEqual(str(result_path), result["result_path"])
        command = popen.call_args.args[0]
        self.assertEqual(["worker", "--job", "-"], command[-3:])
        request = json.loads(process.stdin.write.call_args.args[0])
        self.assertEqual(1, request["schema_version"])
        self.assertEqual("synthesize", request["action"])
        self.assertEqual(self.job_id, request["job_id"])

    @mock.patch("voice_dubbing_runtime.runtime.subprocess.Popen", side_effect=OSError("missing"))
    def test_process_launch_failure_is_structured(self, _popen: mock.Mock) -> None:
        with self.assertRaises(VoiceRuntimeError) as context:
            self.runtime.capabilities()
        self.assertEqual(RUNTIME_NOT_FOUND, context.exception.code)
        self.assertEqual({"operation": "capabilities"}, context.exception.details)

    @mock.patch("voice_dubbing_runtime.runtime.subprocess.Popen")
    def test_timeout_kills_process_group_and_reports_structured_error(self, popen: mock.Mock) -> None:
        process = self.process("")
        process.wait.side_effect = [subprocess.TimeoutExpired("runtime", 1), 0]
        popen.return_value = process

        with self.assertRaises(VoiceRuntimeError) as context:
            self.runtime.capabilities()

        self.assertEqual(CANCELLED, context.exception.code)
        process.kill.assert_called_once()

    @mock.patch("voice_dubbing_runtime.runtime.subprocess.run")
    @mock.patch("voice_dubbing_runtime.runtime.os.name", "nt")
    def test_windows_timeout_terminates_the_process_tree(self, taskkill: mock.Mock) -> None:
        process = self.process("")
        process.pid = 4321

        VoiceRuntime._terminate_process(process)

        self.assertEqual(["taskkill", "/PID", "4321", "/T", "/F"], taskkill.call_args.args[0])
        process.kill.assert_called_once()

    @unittest.skipIf(os.name == "nt", "POSIX-only process-group behavior")
    @mock.patch("voice_dubbing_runtime.runtime.os.killpg")
    def test_posix_timeout_terminates_the_process_group(self, killpg: mock.Mock) -> None:
        process = self.process("")
        process.pid = 4321

        VoiceRuntime._terminate_process(process)

        killpg.assert_called_once()
        process.kill.assert_called_once()

    @mock.patch("voice_dubbing_runtime.runtime.subprocess.Popen")
    def test_success_marker_with_nonzero_exit_is_rejected(self, popen: mock.Mock) -> None:
        result_path = self.write_success_result()
        popen.return_value = self.process(self.success_marker(result_path), returncode=1)

        with self.assertRaises(VoiceRuntimeError) as context:
            self.synthesize()

        self.assertEqual(SYNTHESIS_FAILED, context.exception.code)
        self.assertEqual({"operation": "synthesize", "exit_code": 1}, context.exception.details)

    @mock.patch("voice_dubbing_runtime.runtime.subprocess.Popen")
    def test_outside_root_and_mismatched_job_results_are_rejected(self, popen: mock.Mock) -> None:
        outside = self.base / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        popen.return_value = self.process(self.success_marker(outside))
        with self.assertRaises(VoiceRuntimeError) as outside_context:
            self.synthesize()
        self.assertEqual(SYNTHESIS_FAILED, outside_context.exception.code)

        result_path = self.write_success_result(job_id=str(uuid.uuid4()))
        popen.return_value = self.process(self.success_marker(result_path))
        with self.assertRaises(VoiceRuntimeError) as job_context:
            self.synthesize()
        self.assertEqual(SYNTHESIS_FAILED, job_context.exception.code)

    @mock.patch("voice_dubbing_runtime.runtime.subprocess.Popen")
    def test_contradictory_or_malformed_terminal_markers_are_rejected(self, popen: mock.Mock) -> None:
        result_path = self.write_success_result()
        failure = MARKER_PREFIX + json.dumps(
            {"type": "result", "status": "failed", "job_id": self.job_id, "error_code": "SYNTHESIS_FAILED"}
        ) + "\n"
        popen.return_value = self.process(self.success_marker(result_path) + failure)
        with self.assertRaises(VoiceRuntimeError) as multiple_context:
            self.synthesize()
        self.assertEqual(SYNTHESIS_FAILED, multiple_context.exception.code)

        popen.return_value = self.process(MARKER_PREFIX + "not-json\n")
        with self.assertRaises(VoiceRuntimeError) as malformed_context:
            self.synthesize()
        self.assertEqual(SYNTHESIS_FAILED, malformed_context.exception.code)

    @mock.patch("voice_dubbing_runtime.runtime.subprocess.Popen")
    def test_missing_or_failed_durable_results_are_rejected(self, popen: mock.Mock) -> None:
        missing = self.runs / self.job_id / "result.json"
        popen.return_value = self.process(self.success_marker(missing))
        with self.assertRaises(VoiceRuntimeError) as missing_context:
            self.synthesize()
        self.assertEqual(SYNTHESIS_FAILED, missing_context.exception.code)

        result_path = self.result_path()
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps({"status": "failed", "job_id": self.job_id}), encoding="utf-8")
        popen.return_value = self.process(self.success_marker(result_path))
        with self.assertRaises(VoiceRuntimeError) as failed_context:
            self.synthesize()
        self.assertEqual(SYNTHESIS_FAILED, failed_context.exception.code)

    @mock.patch("voice_dubbing_runtime.runtime.subprocess.Popen")
    def test_nonzero_exit_with_json_output_is_structured(self, popen: mock.Mock) -> None:
        popen.return_value = self.process(
            '{"status":"failed","type":"error","code":"ENGINE_UNAVAILABLE",'
            '"message":"Engine is unavailable.","details":{"engine":"xtts"}}',
            returncode=2,
        )

        with self.assertRaises(VoiceRuntimeError) as context:
            self.runtime.capabilities()

        self.assertEqual("ENGINE_UNAVAILABLE", context.exception.code)
        self.assertEqual({"engine": "xtts"}, context.exception.details)

    @mock.patch("voice_dubbing_runtime.runtime.subprocess.Popen")
    def test_invalid_json_and_bounded_output_are_rejected(self, popen: mock.Mock) -> None:
        popen.return_value = self.process("not json")
        with self.assertRaises(VoiceRuntimeError) as json_context:
            self.runtime.capabilities()
        self.assertEqual(INVALID_REQUEST, json_context.exception.code)

        popen.return_value = self.process("x" * 1_000_001)
        with self.assertRaises(VoiceRuntimeError) as limit_context:
            self.runtime.capabilities()
        self.assertEqual(INVALID_REQUEST, limit_context.exception.code)

    @mock.patch("voice_dubbing_runtime.runtime.subprocess.Popen")
    def test_worker_error_and_nested_private_values_are_sanitized(self, popen: mock.Mock) -> None:
        popen.return_value = self.process(
            MARKER_PREFIX
            + json.dumps(
                {
                    "type": "error",
                    "job_id": self.job_id,
                    "code": "CONSENT_REQUIRED",
                    "message": "Cannot read C:/private/audio.wav.",
                    "details": {
                        "output_path": "C:/private/audio.wav",
                        "nested": {"traceback": "secret", "reason": "C:/private/audio.wav"},
                        "items": [{"source_path": "C:/private/audio.wav", "safe": "ok"}],
                    },
                }
            )
            + "\n"
            + MARKER_PREFIX
            + json.dumps({"type": "result", "status": "failed", "job_id": self.job_id})
            + "\n",
            returncode=2,
        )

        with self.assertRaises(VoiceRuntimeError) as context:
            self.synthesize()

        self.assertEqual("CONSENT_REQUIRED", context.exception.code)
        self.assertEqual("Cannot read <path>", context.exception.message)
        self.assertEqual({"nested": {"reason": "<path>"}, "items": [{"safe": "ok"}]}, context.exception.details)


if __name__ == "__main__":
    unittest.main()
