"""Public Python facade for the existing CLI and JSON worker contracts."""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import threading
import uuid
from pathlib import Path
from typing import Any

from .errors import (
    CANCELLED,
    INVALID_REQUEST,
    RUNTIME_NOT_FOUND,
    SYNTHESIS_FAILED,
    VoiceRuntimeError,
)
from .paths import default_runs_root, runtime_root


MARKER_PREFIX = "@@VOICE_DUB|"
_PATH_PATTERN = re.compile(r"(?:[A-Za-z]:)?[\\/][^\s\"']+")
MAX_CAPTURED_OUTPUT_CHARS = 1_000_000


class VoiceRuntime:
    """Run the public runtime commands without importing engine dependencies."""

    def __init__(
        self,
        *,
        python_executable: str | Path | None = None,
        working_directory: str | Path | None = None,
        runs_root: str | Path | None = None,
        timeout_seconds: float | None = 300,
    ) -> None:
        self.python_executable = str(python_executable or sys.executable)
        self.working_directory = Path(working_directory or runtime_root()).resolve()
        self.runs_root = Path(runs_root or default_runs_root()).resolve()
        self.timeout_seconds = timeout_seconds

    def capabilities(self) -> dict[str, Any]:
        """Return the existing ``capabilities --json`` payload."""

        return self._run_json("capabilities", ["capabilities", "--json"])

    def list_profiles(self) -> list[dict[str, Any]]:
        """Return profiles from the existing ``profiles list --json`` payload."""

        payload = self._run_json("profiles list", ["profiles", "list", "--json"])
        profiles = payload.get("profiles")
        if not isinstance(profiles, list) or not all(isinstance(item, dict) for item in profiles):
            raise VoiceRuntimeError(INVALID_REQUEST, "Runtime returned an invalid profile list.")
        return profiles

    def get_profile(self, profile_id: str) -> dict[str, Any]:
        """Return one profile using the existing ``profiles get --json`` command."""

        if not isinstance(profile_id, str) or not profile_id.strip():
            raise VoiceRuntimeError(INVALID_REQUEST, "profile_id must not be empty.")
        return self._run_json(
            "profiles get",
            ["profiles", "get", "--profile-id", profile_id, "--json"],
        )

    def synthesize(
        self,
        *,
        profile_id: str,
        text: str,
        language: str = "auto",
        engine: str = "auto",
        device: str = "cpu",
        speed: float = 1.0,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Run one schema-v1 synthesis job and return its durable result payload."""

        job = {
            "schema_version": 1,
            "job_id": str(uuid.uuid4()),
            "action": "synthesize",
            "profile_id": profile_id,
            "text": text,
            "language": language,
            "engine": engine,
            "device": device,
            "speed": speed,
            "seed": seed,
        }
        stdout, exit_code = self._run_command(
            "synthesize",
            ["worker", "--job", "-"],
            json.dumps(job, ensure_ascii=False),
            allow_nonzero=True,
        )
        error: dict[str, Any] | None = None
        result: dict[str, Any] | None = None
        terminal_markers = 0
        for line in stdout.splitlines():
            if not line.startswith(MARKER_PREFIX):
                continue
            try:
                marker = json.loads(line[len(MARKER_PREFIX) :])
            except json.JSONDecodeError as exc:
                raise VoiceRuntimeError(SYNTHESIS_FAILED, "Runtime returned a malformed worker marker.") from exc
            if not isinstance(marker, dict):
                raise VoiceRuntimeError(SYNTHESIS_FAILED, "Runtime returned a malformed worker marker.")
            if marker.get("job_id") not in (job["job_id"], None):
                raise VoiceRuntimeError(SYNTHESIS_FAILED, "Runtime returned a result for a different job.")
            if marker.get("type") == "error":
                error = marker
            elif marker.get("type") == "result":
                terminal_markers += 1
                if marker.get("status") == "success":
                    result = marker
                elif error is None:
                    error = {"code": marker.get("error_code"), "message": "Synthesis failed."}
        if terminal_markers != 1:
            raise VoiceRuntimeError(SYNTHESIS_FAILED, "Runtime returned an inconsistent terminal result.")
        if error is not None:
            raise self._error_from_payload(error, "Synthesis failed.")
        if exit_code != 0:
            raise VoiceRuntimeError(
                SYNTHESIS_FAILED,
                "Runtime command failed.",
                {"operation": "synthesize", "exit_code": exit_code},
            )
        if result is None:
            raise VoiceRuntimeError(SYNTHESIS_FAILED, "Runtime returned no successful synthesis result.")
        result_path = self._result_path_for_job(result, str(job["job_id"]))
        try:
            with result_path.open("r", encoding="utf-8-sig") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise VoiceRuntimeError(SYNTHESIS_FAILED, "Runtime result file could not be read.") from exc
        if (
            not isinstance(payload, dict)
            or payload.get("status") != "success"
            or payload.get("job_id") != job["job_id"]
        ):
            raise VoiceRuntimeError(SYNTHESIS_FAILED, "Runtime returned an invalid synthesis result.")
        payload["result_path"] = str(result_path)
        return payload

    def _result_path_for_job(self, marker: dict[str, Any], job_id: str) -> Path:
        value = marker.get("result_path")
        if not isinstance(value, str) or not value:
            raise VoiceRuntimeError(SYNTHESIS_FAILED, "Runtime returned no synthesis result file.")
        expected = (self.runs_root / job_id / "result.json").resolve()
        candidate = Path(value).expanduser().resolve()
        if candidate != expected:
            raise VoiceRuntimeError(SYNTHESIS_FAILED, "Runtime returned an invalid synthesis result location.")
        return candidate

    def _run_json(self, operation: str, arguments: list[str]) -> dict[str, Any]:
        stdout, exit_code = self._run_command(operation, arguments, allow_nonzero=True)
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise VoiceRuntimeError(INVALID_REQUEST, "Runtime returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise VoiceRuntimeError(INVALID_REQUEST, "Runtime returned a JSON value that is not an object.")
        if payload.get("status") == "failed" or payload.get("type") == "error":
            raise self._error_from_payload(payload, "Runtime command failed.")
        if exit_code != 0:
            raise VoiceRuntimeError(
                INVALID_REQUEST,
                "Runtime command failed.",
                {"operation": operation, "exit_code": exit_code},
            )
        return payload

    def _run_command(
        self,
        operation: str,
        arguments: list[str],
        request: str | None = None,
        *,
        allow_nonzero: bool = False,
    ) -> tuple[str, int]:
        command = [self.python_executable, "-u", "-m", "voice_dubbing_runtime", *arguments]
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTHONHOME", None)
        environment["PYTHONUTF8"] = "1"
        environment["PYTHONIOENCODING"] = "utf-8"
        launch_options: dict[str, Any] = {}
        if os.name == "nt":
            launch_options["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        else:
            launch_options["start_new_session"] = True
        try:
            process = subprocess.Popen(
                command,
                cwd=self.working_directory,
                env=environment,
                stdin=subprocess.PIPE if request is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                **launch_options,
            )
        except OSError as exc:
            raise VoiceRuntimeError(
                RUNTIME_NOT_FOUND,
                "Runtime process could not be started.",
                {"operation": operation},
            ) from exc
        try:
            stdout, stderr = self._capture_process_output(process, request)
        except subprocess.TimeoutExpired as exc:
            self._terminate_process(process)
            try:
                process.wait()
            except OSError:
                pass
            self._join_output_readers(process)
            raise VoiceRuntimeError(
                CANCELLED,
                "Runtime command timed out.",
                {"operation": operation, "timeout_seconds": self.timeout_seconds},
            ) from exc
        if len(stdout) >= MAX_CAPTURED_OUTPUT_CHARS or len(stderr) >= MAX_CAPTURED_OUTPUT_CHARS:
            raise VoiceRuntimeError(
                SYNTHESIS_FAILED if operation == "synthesize" else INVALID_REQUEST,
                "Runtime output exceeded the supported limit.",
                {"operation": operation},
            )
        if process.returncode != 0 and not allow_nonzero:
            raise VoiceRuntimeError(
                SYNTHESIS_FAILED if operation == "synthesize" else INVALID_REQUEST,
                "Runtime command failed.",
                {"operation": operation, "exit_code": process.returncode},
            )
        return stdout, int(process.returncode or 0)

    def _capture_process_output(
        self, process: subprocess.Popen[str], request: str | None
    ) -> tuple[str, str]:
        if request is not None and process.stdin is not None:
            process.stdin.write(request)
            process.stdin.close()
        captures: dict[str, str] = {"stdout": "", "stderr": ""}

        def drain(name: str, stream: Any) -> None:
            captured: list[str] = []
            remaining = MAX_CAPTURED_OUTPUT_CHARS
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    break
                if remaining > 0:
                    captured.append(chunk[:remaining])
                    remaining -= len(chunk)
            captures[name] = "".join(captured)

        readers = [
            threading.Thread(target=drain, args=("stdout", process.stdout), daemon=True),
            threading.Thread(target=drain, args=("stderr", process.stderr), daemon=True),
        ]
        for reader in readers:
            reader.start()
        setattr(process, "_voice_runtime_output_readers", readers)
        try:
            process.wait(timeout=self.timeout_seconds)
        except subprocess.TimeoutExpired:
            raise
        self._join_output_readers(process)
        return captures["stdout"], captures["stderr"]

    @staticmethod
    def _join_output_readers(process: subprocess.Popen[str]) -> None:
        readers = getattr(process, "_voice_runtime_output_readers", [])
        for reader in readers:
            reader.join()

    @staticmethod
    def _terminate_process(process: subprocess.Popen[str]) -> None:
        process_id = process.pid
        if os.name == "nt" and isinstance(process_id, int) and process_id > 0:
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(process_id), "/T", "/F"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=15,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except (OSError, subprocess.TimeoutExpired):
                pass
        elif isinstance(process_id, int) and process_id > 0:
            try:
                os.killpg(process_id, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
        try:
            process.kill()
        except OSError:
            pass

    @staticmethod
    def _error_from_payload(payload: dict[str, Any], fallback: str) -> VoiceRuntimeError:
        code = payload.get("code") or payload.get("error_code") or INVALID_REQUEST
        message = VoiceRuntime._public_message(str(payload.get("message") or fallback))
        details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
        return VoiceRuntimeError(str(code), message, VoiceRuntime._public_details(details))

    @staticmethod
    def _public_message(message: str) -> str:
        return _PATH_PATTERN.sub("<path>", message)

    @staticmethod
    def _public_details(details: dict[str, Any]) -> dict[str, Any]:
        private_keys = {"stderr", "stdout", "traceback"}

        def clean(value: Any) -> Any:
            if isinstance(value, dict):
                return {
                    str(key): clean(item)
                    for key, item in value.items()
                    if str(key).lower() not in private_keys
                    and not str(key).lower().endswith(("path", "paths"))
                }
            if isinstance(value, list):
                return [clean(item) for item in value]
            if isinstance(value, str):
                return VoiceRuntime._public_message(value)
            return value

        cleaned = clean(details)
        return cleaned if isinstance(cleaned, dict) else {}


__all__ = ["VoiceRuntime"]
