# Voice Dubbing Runtime

[![CI](https://github.com/akita141188/voice-dubbing-runtime/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/akita141188/voice-dubbing-runtime/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20x64-lightgrey)
![License](https://img.shields.io/badge/License-Apache--2.0-green)
![Contributions](https://img.shields.io/badge/Contributions-welcome-brightgreen)

> Runtime clone giọng và tổng hợp giọng nói chạy cục bộ, ưu tiên CPU, có GUI desktop PySide6 độc lập, nhiều TTS engine cô lập và các gate rõ ràng cho voice/model license.

**Trạng thái:** public alpha / đang phát triển  
**Mục tiêu hiện tại:** Windows x64, Python 3.11, CPU-first  
**First-party code:** Apache-2.0  
**Lưu ý:** viXTTS/XTTS-v2 model dùng điều khoản model riêng; open-source code không tự động cấp quyền thương mại đối với model, dữ liệu hay giọng nói.

[English](README.md) | **Tiếng Việt**

---

## Vì sao có dự án này?

Voice Dubbing Runtime được phát triển theo hướng **ứng dụng clone giọng/dubbing độc lập trước**, sau đó mới cung cấp runtime contract ổn định để ứng dụng khác tích hợp.

Dự án tập trung giải quyết một số vấn đề thực tế thường bị trộn vào cùng một ML environment khó bảo trì:

- tạo và quản lý voice profile có thể tái sử dụng;
- chọn đoạn reference ngắn 8–15 giây từ audio/video;
- tách giọng khỏi nhạc/nền bằng Demucs khi cần;
- chỉ commit reference mới sau technical checks **và human listening approval**;
- tổng hợp speech qua nhiều TTS engine phía sau cùng một runtime contract;
- cô lập các ML stack xung đột trong environment/process riêng;
- cung cấp CLI/JSON worker protocol và GUI PySide6 dạng thin client;
- ưu tiên chạy local/CPU thay vì bắt buộc GPU.

Runtime ban đầu được tách từ luồng Voice Dubbing của FrameExtract Studio, nhưng repo này chủ ý đứng độc lập. Về sau FrameExtract Studio chỉ nên tích hợp qua adapter/protocol ổn định.

---

## Hiện tại đã có gì?

- GUI standalone PySide6 trong `voice_dubbing_app/`.
- Tạo/list/update/delete voice profile.
- Profile revision, integrity lock và history.
- Consent riêng cho từng voice profile.
- FFmpeg source normalization.
- Auto/manual reference 8–15 giây.
- Hai-phase reference workflow:
  - `prepare_profile_reference`;
  - `commit_profile_reference` sau listening approval và single-speaker confirmation.
- Optional Demucs/htdemucs source separation trong environment riêng.
- `vixtts_vi` CPU runtime cho tiếng Việt.
- `xtts_v2_multilingual` runtime riêng với persistent child worker.
- Durable job artifacts và machine-readable marker `@@VOICE_DUB|`.
- Safe storage migration từ namespace cũ của FrameExtract Studio.
- GitHub Actions CI trên Windows/Python 3.11.
- Bootstrap dev/CPU reproducible và `doctor` command read-only.

### Chưa phát hành cho end-user

Project vẫn là **public alpha research/development preview**. Chưa có installer/portable release. Trước khi phát hành binary cần manual desktop acceptance, real-model acceptance và clean-machine packaging test.

Phần screenshot/GIF GUI đang được mở cho contributor tại [good first issue #5](https://github.com/akita141188/voice-dubbing-runtime/issues/5).

---

## Quick start cho contributor

### 1. Clone

```powershell
git clone https://github.com/akita141188/voice-dubbing-runtime.git
cd voice-dubbing-runtime
```

### 2. Tạo dev/GUI/test environment

Yêu cầu Python 3.11 x64.

```powershell
& .\scripts\bootstrap_dev.ps1 -PythonExecutable C:\path\to\python.exe
```

Nếu `python` hiện tại đã là Python 3.11 thì có thể bỏ `-PythonExecutable`.

### 3. Chạy GUI

```powershell
& .\.venv-dev\Scripts\python.exe -m voice_dubbing_app
```

GUI là thin client; lúc mở app không tự download/load model nặng.

### 4. Chạy doctor và test

```powershell
& .\.venv-dev\Scripts\python.exe -m voice_dubbing_runtime doctor --json
& .\scripts\run_tests.ps1
```

### 5. Khi cần viXTTS CPU runtime

```powershell
& .\scripts\bootstrap_cpu.ps1 -PythonExecutable C:\path\to\python.exe
```

Model weights được provision riêng sau license gate, không bundle trong source repo.

---

## Kiến trúc

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

Runtime parent không import tất cả ML dependency vào một process. Mỗi engine nặng được cô lập phía sau subprocess adapter.

---

## Runtime environments

| Mục đích | Environment | Stack chính |
|---|---|---|
| Dev / GUI / tests | `.venv-dev` | PySide6 + project test/runtime deps |
| Vietnamese TTS | `.venv-cpu` | viXTTS, PyTorch CPU, pinned vendored TTS source |
| Multilingual XTTS | `.venv-xtts` | `coqui-tts==0.27.5`, XTTS-v2, PyTorch CPU |
| Source separation | `.venv-source-separation` | Demucs/htdemucs, PyTorch CPU |

Bootstrap base không tự download model; provisioning và license acceptance được tách riêng.

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

Worker action hiện có:

```text
create_profile
prepare_profile_reference
commit_profile_reference
synthesize
```

Machine-readable marker prefix:

```text
@@VOICE_DUB|
```

---

## Storage và backward compatibility

Canonical Windows data root:

```text
%LOCALAPPDATA%\VoiceDubbingRuntime\
```

Dữ liệu cũ tại `%LOCALAPPDATA%\FrameExtractStudio\VoiceDubbing\` được hỗ trợ bằng migration `copy + SHA-256 verify + legacy fallback`. Migration không move, rename hoặc delete legacy source store.

---

## Contributing

Mọi contribution đều được chào đón. Hãy đọc [CONTRIBUTING.md](CONTRIBUTING.md) và [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) trước.

Workflow chuẩn:

```text
fork / feature branch
        ↓
pull request vào develop
        ↓
Windows/Python 3.11 CI + review
        ↓
merge vào develop
        ↓
owner release review
        ↓
develop → main
```

**Contributor không mở PR trực tiếp vào `main`.**

Gợi ý bắt đầu:

- [#5 — Thêm screenshot và demo GIF cho GUI](https://github.com/akita141188/voice-dubbing-runtime/issues/5) — `good first issue`, docs/UI.
- [#6 — Chuẩn hóa Windows path-equivalence assertions](https://github.com/akita141188/voice-dubbing-runtime/issues/6) — `good first issue`, tests.
- [#7 — Thêm public Python API nhỏ](https://github.com/akita141188/voice-dubbing-runtime/issues/7) — `help wanted`, API design.
- [#14 — Roadmap cộng đồng: giọng, ngôn ngữ, chất lượng clone và UI/UX](https://github.com/akita141188/voice-dubbing-runtime/issues/14) — roadmap tổng, `help wanted`.
- [#15 — Mở rộng tiếng Việt lên 10–20 giọng khác biệt](https://github.com/akita141188/voice-dubbing-runtime/issues/15) — Vietnamese TTS/voice.
- [#16 — Mở rộng tiếng Anh lên 10–20 giọng khác biệt](https://github.com/akita141188/voice-dubbing-runtime/issues/16) — English TTS/voice.
- [#17 — Thêm kiến trúc mở rộng cho các ngôn ngữ khác](https://github.com/akita141188/voice-dubbing-runtime/issues/17) — multilingual architecture.
- [#18 — Xây benchmark clone giọng tái lập được với target 0.95](https://github.com/akita141188/voice-dubbing-runtime/issues/18) — ML/audio evaluation.
- [#19 — Thiết kế lại và cải thiện workflow desktop](https://github.com/akita141188/voice-dubbing-runtime/issues/19) — UI/UX và PySide6.
- [#20 — Thêm timing và duration adaptation cho dubbing](https://github.com/akita141188/voice-dubbing-runtime/issues/20) — dubbing/audio workflow.
- [#21 — Phân tích speaker nguồn và đề xuất giọng phù hợp](https://github.com/akita141188/voice-dubbing-runtime/issues/21) — speaker analysis/voice matching.

Xem toàn bộ [open issues](https://github.com/akita141188/voice-dubbing-runtime/issues) hoặc tham gia [GitHub Discussions](https://github.com/akita141188/voice-dubbing-runtime/discussions) để hỏi đáp, đề xuất ý tưởng và trao đổi roadmap.

---

## Roadmap gần

1. Thêm screenshot/demo media và cải thiện first-run UX.
2. Ổn định public runtime/API surface.
3. Mở rộng tiếng Việt và tiếng Anh lên khoảng 10–20 giọng khác biệt cho mỗi ngôn ngữ.
4. Thêm nhiều ngôn ngữ khác qua kiến trúc language/engine capability rõ ràng.
5. Xây quality benchmark tái lập được cho clone giọng, với mục tiêu dài hạn speaker similarity `>= 0.95` theo benchmark đã thống nhất và vẫn phải qua human listening acceptance.
6. Cải thiện reference candidate ranking và quality evaluation.
7. Cải thiện UI/UX standalone: first-run flow, profile/reference management, synthesis và Windows DPI/scaling.
8. Phát triển dubbing workflow: segment/subtitle input, batch synthesis, timing adaptation và track assembly.
9. Nghiên cứu source-speaker analysis và tự đề xuất voice/profile phù hợp.
10. Xây Windows packaging/release pipeline sạch.
11. Chỉ tích hợp FrameExtract Studio sau khi standalone runtime/API ổn định.

Roadmap cho contributor được theo dõi tại [#14](https://github.com/akita141188/voice-dubbing-runtime/issues/14), với các workstream độc lập tại [#15](https://github.com/akita141188/voice-dubbing-runtime/issues/15)–[#21](https://github.com/akita141188/voice-dubbing-runtime/issues/21).

Project tiếp tục theo hướng CPU-first và không bundle model restricted vào source distribution.

---

## License, model và quyền sử dụng giọng

First-party source dùng **Apache License 2.0**. Xem [LICENSE](LICENSE).

Third-party source và model giữ điều khoản riêng:

- vendored TTS source: MPL-2.0;
- Demucs: MIT theo pinned project evidence;
- viXTTS và XTTS-v2 model snapshot hiện tại: CPML với non-commercial scope theo pinned model evidence;
- PySide6/Qt và dependency khác: theo license tương ứng.

Xem [LICENSE_STATUS.md](LICENSE_STATUS.md), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) và [docs/MODEL_LICENSES.md](docs/MODEL_LICENSES.md).

```text
CODE LICENSE != MODEL LICENSE != WEIGHTS/DATA/VOICE RIGHTS
```

Voice cloning có thể tạo audio giống giọng người thật. User/contributor phải tự bảo đảm quyền và consent phù hợp đối với reference voice, generated content và mục đích sử dụng.

---

## Community

- [Issues](https://github.com/akita141188/voice-dubbing-runtime/issues) — bug và engineering task có scope rõ.
- [Discussions](https://github.com/akita141188/voice-dubbing-runtime/discussions) — hỏi đáp, ý tưởng, feedback và roadmap.
- [Security policy](SECURITY.md) — hướng dẫn báo vulnerability.
- [Contributing guide](CONTRIBUTING.md) — workflow phát triển và PR requirements.

Nếu project hữu ích với bạn, việc test, mở issue rõ ràng, gửi PR, chia sẻ project với developer khác hoặc star repo đều giúp dự án phát triển.
