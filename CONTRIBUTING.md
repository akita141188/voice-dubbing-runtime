# Contributing

Voice Dubbing Runtime hiện là research preview. First-party project source dùng
Apache License 2.0 (`Apache-2.0`); xem [LICENSE](LICENSE) và
[LICENSE_STATUS.md](LICENSE_STATUS.md). Trừ khi contributor ghi rõ khác đi,
contribution được chủ ý submit để đưa vào first-party files của project sẽ được
submit theo Apache-2.0, phù hợp Section 5 của license. Project không yêu cầu CLA.

## Workflow sau khi contribution được mở

```text
fork / feature branch
→ pull request vào develop
→ tests và CI
→ review
→ merge vào develop
→ owner release review
→ chỉ owner merge develop vào main
```

- Không push trực tiếp vào `develop` hoặc `main`.
- Contributor không tự merge vào `main`.
- Branch protection là cấu hình remote do owner bật; tài liệu này không tuyên
  bố rằng protection hiện đã active. Xem
  [docs/BRANCH_PROTECTION.md](docs/BRANCH_PROTECTION.md).
- Mỗi PR cần phạm vi nhỏ, mô tả behavior/compatibility impact và bằng chứng test.
- Contributor chỉ được submit code, tài liệu và dữ liệu mà họ có quyền cấp phép.
- Third-party code được copy phải giữ provenance, license và notice bắt buộc;
  không được gắn Apache-2.0 lên material không thuộc first-party project.
- Không đưa model weights, user recordings, voice/reference thật, private data,
  secrets hoặc runs vào repository/PR.
- Giữ các P2 compatibility identifiers và vendored TTS provenance contract.

## Thiết lập và test

Yêu cầu Windows x64 và Python 3.11:

```powershell
& .\scripts\bootstrap_dev.ps1 -PythonExecutable C:\path\to\python.exe
& .\scripts\run_tests.ps1
& .\.venv-dev\Scripts\python.exe -m voice_dubbing_runtime doctor --json
& .\.venv-dev\Scripts\python.exe -m pip check
git diff --check
```

Thay đổi viXTTS dependency/vendor cần thêm bootstrap CPU sạch và source
resolution test. Thay đổi storage cần synthetic migration tests trước khi dùng
data thật. Không dùng model synthesis như một unit-test mặc định.

## Pull request checklist

- [ ] Không có secret, PII, model weights, voice/reference hoặc runtime output.
- [ ] Full regression PASS.
- [ ] P2 compatibility `23/23` PASS.
- [ ] Doctor và `pip check` PASS trong env phù hợp.
- [ ] Docs/notices được cập nhật nếu dependency, model hoặc distribution đổi.
- [ ] Không làm sai root-license/model-license/voice-consent boundaries.

Mọi contributor phải tuân thủ [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Đóng góp giọng đọc / Voice contributions

Trước khi nhận task về voice profile hoặc ngôn ngữ mới, đọc [lộ trình tiếng Việt](docs/GLOBAL_VOICES.vi.md) hoặc [English roadmap](docs/GLOBAL_VOICES.md). Mỗi task quốc tế #36–#55 yêu cầu tối thiểu **5 reference voice của 5 người nói khác nhau** có consent/license hợp lệ, không phải 5 file của một người. Contributor phải bình luận đề xuất nguồn giọng, quyền sử dụng, engine và kế hoạch test trước khi code. Không commit audio private/chưa được cấp phép; chỉ có metadata chưa được coi là hoàn thành. Phải kiểm chứng synthesis thực tế, profile discovery và CI; nếu engine chưa hỗ trợ thì nêu rõ blocker thay vì tuyên bố task hoàn tất.
