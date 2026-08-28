from __future__ import annotations

import json
import os
import math
import struct
import wave
from pathlib import Path

from voice_dubbing_runtime.io_utils import sha256_file


def write_pcm_wav(
    path: Path,
    *,
    seconds: float = 8.0,
    sample_rate: int = 24000,
    amplitude: float = 0.2,
    frequency: float = 220.0,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = int(seconds * sample_rate)
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(sample_rate)
        block = bytearray()
        for index in range(frame_count):
            value = int(32767 * amplitude * math.sin(2.0 * math.pi * frequency * index / sample_rate))
            block.extend(struct.pack("<h", value))
            if len(block) >= 65536:
                writer.writeframesraw(block)
                block.clear()
        if block:
            writer.writeframesraw(block)
    return path


def write_wav(path: Path, *, frequency: float = 220.0, seconds: float = 8.0) -> Path:
    return write_pcm_wav(path, seconds=seconds, frequency=frequency, amplitude=6000 / 32767)


def json_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_broken_split_fixture(root: Path) -> tuple[Path, str, str]:
    lua = root / "lua_china_base"
    primary = write_wav(lua / "references" / "ref_primary.wav", frequency=220.0)
    duc = write_wav(lua / "references" / "reference_001.wav", frequency=310.0, seconds=10.0)
    created = "2026-08-02T00:00:00Z"
    legacy_profile = {
        "schema_version": 1,
        "profile_id": "lua_china_base",
        "created_at": created,
        "status": "TECHNICAL_PASS_PENDING_LISTENING",
        "manual_listening": "PENDING",
        "engine": "vixtts",
        "device": "cpu",
        "language": "vi",
        "reference_files": ["references/ref_primary.wav"],
        "primary_reference_sha256": sha256_file(primary),
    }
    legacy_consent = {
        "schema_version": 1,
        "voice_profile_id": "lua_china_base",
        "authorized_use_confirmed": True,
        "statement": "Phase 1 consent for Lụa only",
        "confirmed_at": created,
        "source": "fixture",
    }
    corrupted = {
        **legacy_profile,
        "display_name": "Đức bảo",
        "profile_type": "cloned",
        "source_type": "video",
        "default_language": "vi",
        "engine_preference": "vixtts_vi",
        "reference_files": [
            {
                "path": "references/reference_001.wav",
                "size_bytes": duc.stat().st_size,
                "sha256": sha256_file(duc),
            }
        ],
        "updated_at": created,
        "enabled": True,
    }
    json_write(lua / "profile.phase1.json", legacy_profile)
    json_write(lua / "consent.phase1.json", legacy_consent)
    json_write(lua / "profile.json", corrupted)
    json_write(
        lua / "consent.json",
        {**legacy_consent, "authorized": True, "profile_id": "lua_china_base"},
    )
    json_write(lua / "quality.json", {"schema_version": 1, "profile_id": "lua_china_base"})
    json_write(lua / "quality_report.json", {"schema_version": 1, "status": "historical"})
    json_write(lua / "profile.lock", {"schema_version": 1, "profile_id": "lua_china_base"})
    return primary, sha256_file(primary), sha256_file(duc)


def wave_validator(path: Path) -> dict:
    with wave.open(str(path), "rb") as reader:
        duration = reader.getnframes() / reader.getframerate()
        rate = reader.getframerate()
        channels = reader.getnchannels()
    if duration <= 0:
        raise ValueError("empty audio")
    return {
        "duration_seconds": duration,
        "sample_rate": rate,
        "channels": channels,
        "peak": 0.2,
        "rms": 0.1,
        "clipping_ratio": 0.0,
        "ffmpeg_decode": "Test double Pass",
    }


def assert_paths_equal(actual: str | Path, expected: str | Path) -> None:
    path_a = Path(actual).resolve()
    path_b = Path(expected).resolve()
    if os.name == 'nt':
        try:
            if os.path.samefile(path_a, path_b):
                return
        except FileNotFoundError:
            pass
        if str(path_a).lower() == str(path_b).lower():
            return
    if path_a != path_b:
        raise AssertionError(f"Paths differ:\nActual:   {path_a}\nExpected: {path_b}")

