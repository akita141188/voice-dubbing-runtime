from __future__ import annotations

import ast
import hashlib
import inspect
import json
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from voice_dubbing_runtime.errors import CANCELLED, VoiceRuntimeError
from voice_dubbing_runtime.source_separation import (
    BAG_FILENAME,
    ENGINE_MARKER,
    MODEL_FILENAME,
    ModelManifestError,
    SourceSeparationRunner,
    verify_model_manifest,
)
from voice_dubbing_runtime.source_separation_worker import (
    _commit_wav_exclusive,
    _run,
    _verify_runtime_packages,
)
from tests.helpers import (
    assert_paths_equal,
    build_broken_split_fixture,
    json_write,
    wave_validator,
    write_pcm_wav,
    write_wav,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _write_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(2)
        writer.setsampwidth(2)
        writer.setframerate(44100)
        writer.writeframes(b"\x00\x00\x10\x00" * 512)


class _NeverCancelled:
    def is_cancelled(self) -> bool:
        return False


class _CancelAfterTimeout:
    def __init__(self) -> None:
        self.calls = 0

    def is_cancelled(self) -> bool:
        self.calls += 1
        return self.calls >= 3


class _FakeProcess:
    _next_pid = 5000

    def __init__(self, *, mode: str, requests: list[dict]) -> None:
        type(self)._next_pid += 1
        self.pid = type(self)._next_pid
        self.mode = mode
        self.requests = requests
        self.returncode: int | None = None
        self._request: dict | None = None

    def poll(self) -> int | None:
        return self.returncode

    def communicate(self, input: str | None = None, timeout: float | None = None):
        if input is not None:
            self._request = json.loads(input)
            self.requests.append(self._request)
        if self.mode in {"timeout", "cancel"}:
            assert self._request is not None
            Path(self._request["temporary_output_path"]).write_bytes(b"partial")
            (Path(self._request["work_dir"]) / "partial.bin").write_bytes(b"partial")
            raise subprocess.TimeoutExpired(
                "fake-demucs",
                timeout,
                output="partial technical stdout",
                stderr=b"partial demucs stderr",
            )
        assert self._request is not None
        if self.mode == "success":
            _write_wav(Path(self._request["output_path"]))
            self.returncode = 0
            payload = {
                "schema_version": 1,
                "status": "success",
                "metrics": {
                    "device": "cpu",
                    "model_signature": "955717e8",
                    "peak_ram_bytes": 123456,
                },
            }
            return ENGINE_MARKER + json.dumps(payload) + "\n", ""
        _write_wav(Path(self._request["output_path"]))
        Path(self._request["temporary_output_path"]).write_bytes(b"partial")
        (Path(self._request["work_dir"]) / "diagnostic.tmp").write_bytes(b"partial")
        self.returncode = 2
        payload = {
            "schema_version": 1,
            "status": "failed",
            "error": {
                "code": "SOURCE_SEPARATION_FAILED",
                "message": "fixture worker failure",
                "details": {"traceback": "fixture traceback"},
            },
        }
        return ENGINE_MARKER + json.dumps(payload) + "\n", "technical demucs stderr"

    def wait(self, timeout: float | None = None) -> int:
        if self.returncode is None:
            self.returncode = -9
        return self.returncode

    def terminate(self) -> None:
        self.returncode = -15

    def kill(self) -> None:
        self.returncode = -9


class SourceSeparationFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "voice-dubbing-runtime"
        self.root.mkdir(parents=True)
        self.python = self.root / ".venv-source-separation" / "Scripts" / "python.exe"
        self.python.parent.mkdir(parents=True)
        self.python.write_bytes(b"fixture python")
        self.lock = self.root / "requirements-source-separation.lock.txt"
        self.lock.write_bytes(b"fixture hash-locked dependencies\n")
        self.model_dir = self.root / "models" / "source_separation" / "htdemucs"
        self.model_dir.mkdir(parents=True)
        self.model = self.model_dir / MODEL_FILENAME
        self.model.write_bytes(b"fixture model bytes")
        self.bag = self.model_dir / BAG_FILENAME
        self.bag.write_bytes(b"models: ['955717e8']\n")
        self.expected_records = {
            MODEL_FILENAME: (self.model.stat().st_size, _sha(self.model)),
            BAG_FILENAME: (self.bag.stat().st_size, _sha(self.bag)),
        }

        self.manifest = {
            "schema_version": 1,
            "engine_id": "demucs_htdemucs_vocals",
            "model_id": "demucs/htdemucs",
            "model_name": "htdemucs",
            "model_signature": "955717e8",
            "model_format": "legacy_torch_checkpoint",
            "model_source_url": (
                "https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/"
                "955717e8-8726e21a.th"
            ),
            "model_filename_checksum_prefix": "8726e21a",
            "license_id": "MIT",
            "license_url": "https://github.com/adefossez/demucs/blob/v4.1.0/LICENSE",
            "package_revision": "demucs==4.1.0",
            "package_wheel_sha256": (
                "4916A804702033CE934A6CDFA7E38DDE03F7A7A6E85F41D0120EEFE9E2966758"
            ),
            "provision_status": "HASH_VERIFIED",
            "runtime_contract": {
                "python_series": "3.11",
                "torch": "2.6.0+cpu",
                "numpy": "1.26.4",
                "sphn": "0.2.1",
                "psutil": "7.2.2",
                "torchaudio": None,
                "device": "cpu",
            },
            "requirements_lock": {
                "path": "requirements-source-separation.lock.txt",
                "size_bytes": self.lock.stat().st_size,
                "sha256": _sha(self.lock),
            },
            "inference_contract": {
                "two_stems": "vocals",
                "shifts": 0,
                "jobs": 0,
                "split": True,
                "overlap": 0.25,
                "output_format": "pcm_s16le_wav",
            },
            "files": [
                {
                    "path": name,
                    "size_bytes": size,
                    "sha256": digest,
                }
                for name, (size, digest) in self.expected_records.items()
            ],
        }
        self.manifest_path = self.model_dir / "model_manifest.json"
        self.manifest_path.write_text(json.dumps(self.manifest), encoding="utf-8")

    def test_worker_uses_only_named_vocals_stem(self) -> None:
        source = inspect.getsource(_run)
        tree = ast.parse(source)
        subscripts = [
            node.slice.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ]
        self.assertIn("vocals", subscripts)
        self.assertNotIn("no_vocals", subscripts)
        self.assertIn('save_audio(\n            stems["vocals"]', source)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def runner(self, *, timeout: float = 5.0) -> SourceSeparationRunner:
        return SourceSeparationRunner(
            self.root,
            python_executable=self.python,
            model_dir=self.model_dir,
            timeout_seconds=timeout,
        )

    def manifest_patch(self):
        return patch(
            "voice_dubbing_runtime.source_separation._expected_file_records",
            return_value=self.expected_records,
        )

    @staticmethod
    def fake_popen(mode: str, requests: list[dict]):
        def factory(*_args, **_kwargs):
            return _FakeProcess(mode=mode, requests=requests)

        return factory


class SourceSeparationManifestTests(SourceSeparationFixture):
    def test_child_runtime_contract_requires_pinned_numpy(self) -> None:
        versions = {
            "demucs": "4.1.0",
            "torch": "2.6.0+cpu",
            "numpy": "1.26.4",
            "sphn": "0.2.1",
            "psutil": "7.2.2",
        }

        def version(name: str) -> str:
            if name == "torchaudio":
                from importlib.metadata import PackageNotFoundError

                raise PackageNotFoundError(name)
            return versions[name]

        with patch(
            "voice_dubbing_runtime.source_separation_worker.importlib.metadata.version",
            side_effect=version,
        ):
            self.assertEqual("1.26.4", _verify_runtime_packages()["numpy"])

    def test_manifest_verifies_full_hashes_without_importing_ml(self) -> None:
        with self.manifest_patch():
            result = verify_model_manifest(self.model_dir)
        self.assertEqual("955717e8", result["model_signature"])
        self.model.write_bytes(b"tampered")
        with self.manifest_patch(), self.assertRaisesRegex(
            ModelManifestError, "MODEL_FILE_MISSING_OR_SIZE_MISMATCH"
        ):
            verify_model_manifest(self.model_dir)

    def test_manifest_rejects_unexpected_or_escaping_file_record(self) -> None:
        payload = dict(self.manifest)
        payload["files"] = [*self.manifest["files"], {"path": "../escape.th"}]
        self.manifest_path.write_text(json.dumps(payload), encoding="utf-8")
        with self.manifest_patch(), self.assertRaisesRegex(
            ModelManifestError, "MODEL_MANIFEST_UNEXPECTED_FILE"
        ):
            verify_model_manifest(self.model_dir)

    def test_manifest_rejects_unlisted_actual_model_directory_file(self) -> None:
        (self.model_dir / "unexpected-checkpoint.th").write_bytes(b"unexpected")
        with self.manifest_patch(), self.assertRaisesRegex(
            ModelManifestError, "MODEL_DIRECTORY_FILE_SET_MISMATCH"
        ):
            verify_model_manifest(self.model_dir)

    def test_manifest_rejects_dependency_lock_tamper(self) -> None:
        self.lock.write_bytes(b"tampered lock")
        with self.manifest_patch(), self.assertRaisesRegex(
            ModelManifestError, "DEPENDENCY_LOCK_MISSING_OR_SIZE_MISMATCH"
        ):
            verify_model_manifest(self.model_dir)

    def test_parent_launcher_has_no_ml_imports(self) -> None:
        import voice_dubbing_runtime.source_separation as module

        tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertTrue(
            {"demucs", "torch", "torchaudio", "sphn", "psutil", "numpy"}.isdisjoint(
                imported
            )
        )


class SourceSeparationLauncherTests(SourceSeparationFixture):
    def _run(self, *, mode: str, token=None, timeout: float = 5.0):
        requests: list[dict] = []
        source = self.root / "fixtures" / "synthetic English voice.wav"
        _write_wav(source)
        output = self.root / "runs" / "kiểm thử" / "ref_voice_only.wav"
        work = self.root / "runs" / "kiểm thử" / "work"

        def kill(process: _FakeProcess) -> None:
            process.returncode = -9

        with self.manifest_patch(), patch(
            "voice_dubbing_runtime.source_separation.subprocess.Popen",
            side_effect=self.fake_popen(mode, requests),
        ), patch.object(SourceSeparationRunner, "_kill_tree", staticmethod(kill)):
            result = self.runner(timeout=timeout).separate_vocals(
                input_path=source,
                output_path=output,
                work_dir=work,
                progress=lambda *_: None,
                cancel_token=token or _NeverCancelled(),
            )
        return result, requests, source, output, work

    def test_unicode_request_round_trip_and_success_output(self) -> None:
        result, requests, source, output, work = self._run(mode="success")
        self.assertEqual(123456, result["peak_ram_bytes"])
        self.assertTrue(output.is_file())
        assert_paths_equal(source, requests[0]["input_path"])
        assert_paths_equal(output, requests[0]["output_path"])
        self.assertEqual("vocals", requests[0]["two_stems"])
        self.assertEqual([], list(work.glob(".source-separation-*")))
        self.assertEqual([], list(output.parent.glob(".*.demucs.wav")))
        log_path = Path(result["diagnostic_log_path"])
        self.assertTrue(log_path.is_file())
        diagnostic = json.loads(log_path.read_text(encoding="utf-8"))
        self.assertEqual("success", diagnostic["status"])
        assert_paths_equal(source, diagnostic["input_path"])
        assert_paths_equal(output, diagnostic["output_path"])

    def test_cancel_kills_worker_and_cleans_only_job_temp(self) -> None:
        with self.assertRaises(VoiceRuntimeError) as caught:
            self._run(mode="cancel", token=_CancelAfterTimeout())
        self.assertEqual(CANCELLED, caught.exception.code)
        run_root = self.root / "runs" / "kiểm thử"
        self.assertEqual([], list(run_root.rglob(".source-separation-*")))
        self.assertEqual([], list(run_root.glob(".*.demucs.wav")))
        logs = list((run_root / "work").glob("source_separation_*.log"))
        self.assertEqual(1, len(logs))
        self.assertEqual(
            "cancelled", json.loads(logs[0].read_text(encoding="utf-8"))["status"]
        )
        self.assertIn(
            "partial demucs stderr",
            json.loads(logs[0].read_text(encoding="utf-8"))["stderr_tail"],
        )
        self.assertTrue(     logs[0].samefile(         Path(caught.exception.details["diagnostic_log_path"])     ) )

    def test_timeout_kills_worker_and_cleans_temp(self) -> None:
        with self.assertRaises(VoiceRuntimeError) as caught:
            self._run(mode="timeout", timeout=0.001)
        self.assertEqual("SOURCE_SEPARATION_FAILED", caught.exception.code)
        self.assertEqual("WORKER_TIMEOUT", caught.exception.details["reason"])
        run_root = self.root / "runs" / "kiểm thử"
        self.assertEqual([], list(run_root.rglob(".source-separation-*")))
        self.assertEqual([], list(run_root.glob(".*.demucs.wav")))
        logs = list((run_root / "work").glob("source_separation_*.log"))
        self.assertEqual(1, len(logs))
        self.assertEqual(
            "timeout", json.loads(logs[0].read_text(encoding="utf-8"))["status"]
        )
        self.assertTrue(     logs[0].samefile(         Path(caught.exception.details["diagnostic_log_path"])     ) )

    def test_worker_stderr_is_preserved_and_output_not_committed(self) -> None:
        with self.assertRaises(VoiceRuntimeError) as caught:
            self._run(mode="failed")
        self.assertIn("technical demucs stderr", caught.exception.details["stderr_tail"])
        self.assertEqual("fixture traceback", caught.exception.details["traceback"])
        output = self.root / "runs" / "kiểm thử" / "ref_voice_only.wav"
        self.assertFalse(output.exists())
        log_path = Path(caught.exception.details["diagnostic_log_path"])
        self.assertTrue(log_path.is_file())
        diagnostic = json.loads(log_path.read_text(encoding="utf-8"))
        self.assertEqual("failed", diagnostic["status"])
        self.assertIn("technical demucs stderr", diagnostic["stderr_tail"])


class SourceSeparationWorkerPersistenceTests(unittest.TestCase):
    def test_worker_commit_is_durable_exclusive_and_keeps_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            temporary = root / ".voice.demucs.wav"
            output = root / "voice.wav"
            _write_wav(temporary)
            metrics = _commit_wav_exclusive(temporary, output)
            self.assertGreater(metrics["duration_seconds"], 0)
            original = _sha(output)
            second = root / ".second.demucs.wav"
            _write_wav(second)
            with self.assertRaises(FileExistsError):
                _commit_wav_exclusive(second, output)
            self.assertEqual(original, _sha(output))


if __name__ == "__main__":
    unittest.main()
