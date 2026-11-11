# Global voice contribution roadmap

> Planning document, updated 2026-10-17. These are **open contribution targets, not shipped voices**. See [Vietnamese](GLOBAL_VOICES.vi.md).

## Scope and tracking

- Vietnamese and English: [#15](https://github.com/akita141188/voice-dubbing-runtime/issues/15), [#16](https://github.com/akita141188/voice-dubbing-runtime/issues/16); focused [#30–#33](https://github.com/akita141188/voice-dubbing-runtime/issues/30).
- Evaluation and contribution infrastructure: [#18](https://github.com/akita141188/voice-dubbing-runtime/issues/18), [#34](https://github.com/akita141188/voice-dubbing-runtime/issues/34), [#35](https://github.com/akita141188/voice-dubbing-runtime/issues/35).
- Language extensibility: [#17](https://github.com/akita141188/voice-dubbing-runtime/issues/17); engine capabilities: [#29](https://github.com/akita141188/voice-dubbing-runtime/issues/29).

### Global language tracks: at least five distinct reference speakers each

| Issue | Language / locale | Issue | Language / locale |
|---|---|---|---|
| [#36](https://github.com/akita141188/voice-dubbing-runtime/issues/36) | German de-DE | [#37](https://github.com/akita141188/voice-dubbing-runtime/issues/37) | French fr-FR |
| [#38](https://github.com/akita141188/voice-dubbing-runtime/issues/38) | Spanish es-ES | [#39](https://github.com/akita141188/voice-dubbing-runtime/issues/39) | Spanish es-MX |
| [#40](https://github.com/akita141188/voice-dubbing-runtime/issues/40) | Portuguese pt-BR | [#41](https://github.com/akita141188/voice-dubbing-runtime/issues/41) | Portuguese pt-PT |
| [#42](https://github.com/akita141188/voice-dubbing-runtime/issues/42) | Italian it-IT | [#43](https://github.com/akita141188/voice-dubbing-runtime/issues/43) | Polish pl-PL |
| [#44](https://github.com/akita141188/voice-dubbing-runtime/issues/44) | Russian ru-RU | [#45](https://github.com/akita141188/voice-dubbing-runtime/issues/45) | Ukrainian uk-UA |
| [#46](https://github.com/akita141188/voice-dubbing-runtime/issues/46) | Turkish tr-TR | [#47](https://github.com/akita141188/voice-dubbing-runtime/issues/47) | Modern Standard Arabic ar |
| [#48](https://github.com/akita141188/voice-dubbing-runtime/issues/48) | Hindi hi-IN | [#49](https://github.com/akita141188/voice-dubbing-runtime/issues/49) | Bengali bn-BD |
| [#50](https://github.com/akita141188/voice-dubbing-runtime/issues/50) | Urdu ur-PK | [#51](https://github.com/akita141188/voice-dubbing-runtime/issues/51) | Indonesian id-ID |
| [#52](https://github.com/akita141188/voice-dubbing-runtime/issues/52) | Thai th-TH | [#53](https://github.com/akita141188/voice-dubbing-runtime/issues/53) | Mandarin zh-CN |
| [#54](https://github.com/akita141188/voice-dubbing-runtime/issues/54) | Japanese ja-JP | [#55](https://github.com/akita141188/voice-dubbing-runtime/issues/55) | Korean ko-KR |

**Target: 20 tracks × 5 independently distinct reference speakers = at least 100 verified voice options.** This is a roadmap target, **not** a count of working or approved voices. The same speaker recorded five times counts as **one**, not five. Accent, locale and language must not be conflated.

## Definition of done for a language track

1. At least five **different authorized speakers**, with unique stable profile IDs and accurate language/locale metadata. Prefer diversity in voice characteristics; never count speed/pitch transformations as separate voices.
2. Document each reference's provenance, permission/consent, applicable licenses, compatibility, and opt-in provisioning. Never commit private/unlicensed audio, model weights or personal data. A metadata-only PR does not satisfy the five-voice gate.
3. Demonstrate actual synthesis or consent-based cloning for each voice in a supported runtime. Verify engine-language compatibility; do not assume all existing engines support every language.
4. Provide language-specific pronunciation test texts and human listening notes on intelligibility, naturalness, accent and distinctiveness. Follow [#18](https://github.com/akita141188/voice-dubbing-runtime/issues/18) for reproducible similarity metrics; do not claim an unverified 0.95 score.
5. Include deterministic automated tests for profile discovery, invalid/missing references, licensing/consent enforcement and unsupported engines. Run relevant regressions and `windows-python311` CI.
6. Preserve existing schema-v1 CLI/worker compatibility, isolation and no-silent-download policy. Document remaining limitations and explicitly distinguish partial from complete work.

## How to contribute

Comment on the relevant issue **before coding** with your proposed five distinct voice sources, rights/consent basis, engine support and test plan. Wait for scope alignment. Work in a fork or feature branch, open a focused PR targeting `develop`, link the issue and attach test evidence. Never push directly to `main` or `develop`. See [CONTRIBUTING.md](../CONTRIBUTING.md).

## Further candidates (not yet assigned)

Cantonese, Taiwanese Mandarin, Malay, Tagalog, Khmer, Lao and Burmese; additional age/register/MC styles in Japanese, Korean and Mandarin. These require separately scoped issues and engine/licensing feasibility checks; **they are not included in the 100-voice target above**.
