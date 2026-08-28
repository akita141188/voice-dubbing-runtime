# Voice Dubbing Runtime

[![CI](https://github.com/akita141188/voice-dubbing-runtime/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/akita141188/voice-dubbing-runtime/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20x64-lightgrey)
![License](https://img.shields.io/badge/License-Apache--2.0-green)
![Contributions](https://img.shields.io/badge/Contributions-welcome-brightgreen)

> Local, CPU-first voice cloning and speech synthesis runtime with a standalone PySide6 desktop GUI, isolated TTS engines and explicit voice/model license gates.

**Status:** public alpha / active development  
**Target:** Windows x64, Python 3.11, CPU-first  
**First-party code:** Apache-2.0  
**Important:** the current viXTTS/XTTS-v2 model snapshots use separate model terms; open-source code does not automatically grant commercial model or voice rights.

**English** | [Tiếng Việt](README.vi.md)

---

## Why this project?

Voice Dubbing Runtime is being built as a **standalone voice-cloning and dubbing application first**, with a stable runtime contract that other apps can integrate later.

The project focuses on a few practical problems that are often mixed together in one fragile ML environment:

- creating and managing reusable voice profiles;
- selecting short 8–15 second voice references from audio/video;
- optionally separating vocals from background audio with Demucs;
- requiring technical checks **and human listening approval** before a new reference is committed;
- synthesizing speech with multiple TTS engines behind one runtime contract;
- keeping incompatible ML stacks isolated in separate environments/processes;
- exposing a CLI/JSON worker protocol and a thin PySide6 desktop GUI;
- running locally and CPU-first instead of requiring a GPU-first deployment.

The runtime originally grew out of the Voice Dubbing work in FrameExtract Studio, but this repository is intentionally standalone. FrameExtract Studio should integrate later through a stable adapter/protocol rather than becoming a dependency here.

---

## What works today

- Standalone PySide6 GUI in `voice_dubbing_app/`.
- Voice profile create/list/update/delete flows.
- Profile revisions, integrity locks and history.
- Profile-specific voice-rights consent.
- FFmpeg source normalization.
- Automatic or manual 8–15 second reference selection.
- Two-phase reference workflow:
  - `prepare_profile_reference`;
  - `commit_profile_reference` after listening approval and single-speaker confirmation.
- Optional Demucs/htdemucs source separation in an isolated environment.
- `vixtts_vi` CPU runtime for Vietnamese.
- `xtts_v2_multilingual` isolated runtime with a persistent child worker.
- Durable job artifacts and machine-readable `@@VOICE_DUB|` progress markers.
- Safe standalone storage migration from the legacy FrameExtract Studio namespace.
- Windows/Python 3.11 GitHub Actions CI.
- Reproducible dev/CPU bootstrap scripts and a read-only `doctor` command.

### Not released yet

This is still a **public alpha research/development preview**. There is no end-user installer/portable release yet. Before packaged releases, the project still needs manual desktop acceptance, real-model acceptance and clean-machine packaging tests.

A visual GUI demo is tracked in [good first issue #5](https://github.com/akita141188/voice-dubbing-runtime/issues/5).

---

## Quick start for contributors

### 1. Clone

```powershell
git clone https://github.com/akita141188/voice-dubbing-runtime.git
cd voice-dubbing-runtime
```

### 2. Bootstrap the self-contained dev/GUI/test environment

Python 3.11 x64 is required.

```powershell
& .\scripts\bootstrap_dev.ps1 -PythonExecutable C:\path\to\python.exe
```

If `python` already points to Python 3.11, `-PythonExecutable` can be omitted.

### 3. Run the GUI

```powershell
& .\.venv-dev\Scripts\python.exe -m voice_dubbing_app
```

The GUI is a thin client. Starting it does not silently download or load heavy models.

### 4. Run diagnostics and tests

```powershell
& .\.venv-dev\Scripts\python.exe -m voice_dubbing_runtime doctor --json
& .\scripts\run_tests.ps1
```

### 5. Bootstrap the viXTTS CPU runtime when needed

```powershell
& .\scripts\bootstrap_cpu.ps1 -PythonExecutable C:\path\to\python.exe
```

Model weights are provisioned separately after their own license gates; they are not bundled in the source repository.

---

## Architecture

```text
Standalone Desktop GUI / CLI / external client
                |
                v
      voice_dubbing_runtime
                |
     +----------+-----------+
     |          |           |
     v          v           v
 Profiles   Reference     Engine Registry
 Manager    Pipeline           |
                |              +--------------------+
                |              |                    |
                v              v                    v
         FFmpeg + Demucs    viXTTS              XTTS-v2
                |          .venv-cpu            .venv-xtts
                |                                   |
                v                                   v
     .venv-source-separation              persistent child worker
```

The parent runtime intentionally avoids importing every ML dependency into one process. Engine-specific stacks remain isolated behind subprocess adapters.

---

## Runtime environments

| Purpose | Environment | Main stack |
|---|---|---|
| Dev / GUI / tests | `.venv-dev` | PySide6 + project test/runtime dependencies |
| Vietnamese TTS | `.venv-cpu` | viXTTS, PyTorch CPU, pinned vendored TTS source |
| Multilingual XTTS | `.venv-xtts` | `coqui-tts==0.27.5`, XTTS-v2, PyTorch CPU |
| Source separation | `.venv-source-separation` | Demucs/htdemucs, PyTorch CPU |

Provisioning scripts intentionally keep model download/license acceptance separate from the base bootstrap.

---

## CLI / worker contract

```powershell
& .\.venv-cpu\Scripts\python.exe -u -m voice_dubbing_runtime capabilities --json
& .\.venv-cpu\Scripts\python.exe -u -m voice_dubbing_runtime profiles list --json
& .\.venv-dev\Scripts\python.exe -m voice_dubbing_runtime storage status --json
& .\.venv-dev\Scripts\python.exe -m voice_dubbing_runtime storage migrate --json
& .\.venv-cpu\Scripts\python.exe -u -m voice_dubbing_runtime worker --job <job.json>
& .\.venv-cpu\Scripts\python.exe -u -m voice_dubbing_runtime worker --jobs-jsonl <jobs.jsonl>
```

Current worker actions:

```text
create_profile
prepare_profile_reference
commit_profile_reference
synthesize
```

The runtime uses machine-readable markers prefixed with:

```text
@@VOICE_DUB|
```

---

## Storage and backward compatibility

The canonical standalone Windows data root is:

```text
%LOCALAPPDATA%\VoiceDubbingRuntime\
```

Legacy data under `%LOCALAPPDATA%\FrameExtractStudio\VoiceDubbing\` is supported through a copy + SHA-256 verification migration with legacy fallback. The migration does not move, rename or delete the legacy source store.

---

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) first.

Canonical contribution flow:

```text
fork / feature branch
        ↓
pull request into develop
        ↓
Windows/Python 3.11 CI + review
        ↓
merge into develop
        ↓
owner release review
        ↓
develop → main
```

**Do not open contributor PRs directly against `main`.**

Good places to start:

- [#5 — Add standalone GUI screenshots and a short demo GIF](https://github.com/akita141188/voice-dubbing-runtime/issues/5) — `good first issue`, documentation/UI.
- [#6 — Centralize Windows path-equivalence assertions for CI](https://github.com/akita141188/voice-dubbing-runtime/issues/6) — `good first issue`, tests.
- [#7 — Add a small public Python API](https://github.com/akita141188/voice-dubbing-runtime/issues/7) — `help wanted`, API design.
- [#14 — Community roadmap: voices, languages, cloning quality and desktop UX](https://github.com/akita141188/voice-dubbing-runtime/issues/14) — umbrella roadmap, `help wanted`.
- [#15 — Expand Vietnamese voice diversity to 10–20 distinct voices](https://github.com/akita141188/voice-dubbing-runtime/issues/15) — Vietnamese TTS/voice work.
- [#16 — Expand English voice diversity to 10–20 distinct voices](https://github.com/akita141188/voice-dubbing-runtime/issues/16) — English TTS/voice work.
- [#17 — Add extensible support for additional languages](https://github.com/akita141188/voice-dubbing-runtime/issues/17) — multilingual architecture.
- [#18 — Define a reproducible voice-clone fidelity benchmark with a 0.95 target](https://github.com/akita141188/voice-dubbing-runtime/issues/18) — ML/audio evaluation.
- [#19 — Redesign the standalone desktop workflow](https://github.com/akita141188/voice-dubbing-runtime/issues/19) — UI/UX and PySide6.
- [#20 — Add dubbing timing and duration adaptation](https://github.com/akita141188/voice-dubbing-runtime/issues/20) — dubbing/audio workflow.
- [#21 — Analyze source speakers and recommend matching voices](https://github.com/akita141188/voice-dubbing-runtime/issues/21) — speaker analysis and voice matching.

Browse all [open issues](https://github.com/akita141188/voice-dubbing-runtime/issues) or join [GitHub Discussions](https://github.com/akita141188/voice-dubbing-runtime/discussions) for questions, ideas and roadmap conversations.

---

## Roadmap

Near-term priorities:

1. Add screenshots/demo media and improve first-run UX.
2. Stabilize the public runtime/API surface.
3. Expand Vietnamese and English voice diversity toward 10–20 distinct voices per language.
4. Add more languages through a clean language/engine capability architecture.
5. Define reproducible voice-clone quality evaluation, with a long-term speaker-similarity target of `>= 0.95` under the agreed benchmark plus human listening acceptance.
6. Improve reference candidate ranking and quality evaluation.
7. Improve the standalone UI/UX, including first-run flow, profile/reference management, synthesis and Windows DPI/scaling.
8. Add dubbing workflow features: segment/subtitle input, batch synthesis, timing adaptation and track assembly.
9. Explore automatic source-speaker analysis and matching voice recommendations.
10. Build a clean Windows packaging/release pipeline.
11. Integrate FrameExtract Studio only after the standalone runtime/API is stable.

The community roadmap and independently claimable workstreams are tracked in [#14](https://github.com/akita141188/voice-dubbing-runtime/issues/14) and child issues [#15](https://github.com/akita141188/voice-dubbing-runtime/issues/15)–[#21](https://github.com/akita141188/voice-dubbing-runtime/issues/21).

The project remains CPU-first and keeps model provisioning separate from the source distribution.

---

## License, models and voice rights

First-party source is licensed under **Apache License 2.0**. See [LICENSE](LICENSE).

Third-party source and models keep their own terms:

- vendored TTS source: MPL-2.0;
- Demucs: MIT according to the pinned project evidence;
- current viXTTS and XTTS-v2 model snapshots: CPML with non-commercial scope according to the pinned model evidence;
- PySide6/Qt and other dependencies: their respective third-party terms.

See [LICENSE_STATUS.md](LICENSE_STATUS.md), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [docs/MODEL_LICENSES.md](docs/MODEL_LICENSES.md).

```text
CODE LICENSE != MODEL LICENSE != WEIGHTS/DATA/VOICE RIGHTS
```

Voice cloning can produce audio resembling a real person. Users and contributors are responsible for the rights and consent required for reference voices, generated content and intended use.

---

## Community

- [Issues](https://github.com/akita141188/voice-dubbing-runtime/issues) — bugs and scoped engineering work.
- [Discussions](https://github.com/akita141188/voice-dubbing-runtime/discussions) — questions, ideas, feedback and roadmap conversations.
- [Security policy](SECURITY.md) — vulnerability reporting guidance.
- [Contributing guide](CONTRIBUTING.md) — development workflow and PR requirements.

If the project is useful to you, testing it, opening a focused issue, contributing a PR, sharing it with other developers, or starring the repository all help the project grow.
