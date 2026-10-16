# Lộ trình đóng góp giọng đọc đa ngôn ngữ

> Tài liệu kế hoạch, cập nhật 17/10/2026. Các mục dưới đây là **task cần triển khai, không phải giọng đã có**. Bản tiếng Anh: [GLOBAL_VOICES.md](GLOBAL_VOICES.md).

## Tổng quan

- Giọng Việt và Anh: [#15](https://github.com/akita141188/voice-dubbing-runtime/issues/15), [#16](https://github.com/akita141188/voice-dubbing-runtime/issues/16), các task nhỏ [#30–#33](https://github.com/akita141188/voice-dubbing-runtime/issues/30).
- Chuẩn đánh giá và đóng góp profile: [#18](https://github.com/akita141188/voice-dubbing-runtime/issues/18), [#34](https://github.com/akita141188/voice-dubbing-runtime/issues/34), [#35](https://github.com/akita141188/voice-dubbing-runtime/issues/35).
- Mở rộng ngôn ngữ và engine: [#17](https://github.com/akita141188/voice-dubbing-runtime/issues/17), [#29](https://github.com/akita141188/voice-dubbing-runtime/issues/29).

## 20 task quốc tế — tối thiểu 5 reference voice độc lập mỗi task

| Issue | Ngôn ngữ | Issue | Ngôn ngữ |
|---|---|---|---|
| [#36](https://github.com/akita141188/voice-dubbing-runtime/issues/36) | Đức | [#37](https://github.com/akita141188/voice-dubbing-runtime/issues/37) | Pháp |
| [#38](https://github.com/akita141188/voice-dubbing-runtime/issues/38) | Tây Ban Nha (Spain) | [#39](https://github.com/akita141188/voice-dubbing-runtime/issues/39) | Tây Ban Nha (Mexico/Mỹ Latinh) |
| [#40](https://github.com/akita141188/voice-dubbing-runtime/issues/40) | Bồ Đào Nha (Brazil) | [#41](https://github.com/akita141188/voice-dubbing-runtime/issues/41) | Bồ Đào Nha (Portugal) |
| [#42](https://github.com/akita141188/voice-dubbing-runtime/issues/42) | Ý | [#43](https://github.com/akita141188/voice-dubbing-runtime/issues/43) | Ba Lan |
| [#44](https://github.com/akita141188/voice-dubbing-runtime/issues/44) | Nga | [#45](https://github.com/akita141188/voice-dubbing-runtime/issues/45) | Ukraine |
| [#46](https://github.com/akita141188/voice-dubbing-runtime/issues/46) | Thổ Nhĩ Kỳ | [#47](https://github.com/akita141188/voice-dubbing-runtime/issues/47) | Ả Rập chuẩn |
| [#48](https://github.com/akita141188/voice-dubbing-runtime/issues/48) | Hindi | [#49](https://github.com/akita141188/voice-dubbing-runtime/issues/49) | Bengal |
| [#50](https://github.com/akita141188/voice-dubbing-runtime/issues/50) | Urdu | [#51](https://github.com/akita141188/voice-dubbing-runtime/issues/51) | Indonesia |
| [#52](https://github.com/akita141188/voice-dubbing-runtime/issues/52) | Thái | [#53](https://github.com/akita141188/voice-dubbing-runtime/issues/53) | Trung phổ thông |
| [#54](https://github.com/akita141188/voice-dubbing-runtime/issues/54) | Nhật | [#55](https://github.com/akita141188/voice-dubbing-runtime/issues/55) | Hàn |

**Mục tiêu: 20 task × 5 người nói khác nhau = ít nhất 100 lựa chọn giọng đã kiểm chứng.** Đây là chỉ tiêu tương lai, **không phải số giọng đã hoạt động**. Năm file của cùng một người chỉ tính là một giọng. Không đánh đồng ngôn ngữ với vùng miền hoặc accent.

## Điều kiện nghiệm thu bắt buộc

1. Tối thiểu **5 người nói độc lập** có quyền sử dụng hợp lệ; mỗi người có profile ID riêng, metadata ngôn ngữ/vùng miền rõ ràng. Không tính chỉnh pitch/speed thành giọng mới.
2. Có bằng chứng nguồn reference, consent, giấy phép, tương thích engine và cách người dùng chủ động cung cấp tài nguyên. **Không commit** âm thanh riêng tư/chưa được phép, model weights hoặc dữ liệu cá nhân. Chỉ thêm metadata chưa được tính hoàn thành.
3. Kiểm chứng **tổng hợp hoặc clone giọng thực sự chạy được** với từng profile trên engine tương thích. Không mặc định engine hiện tại hỗ trợ tất cả ngôn ngữ.
4. Có bộ câu kiểm thử phát âm riêng cho ngôn ngữ, đánh giá nghe về độ rõ, tự nhiên, accent và độ khác biệt giọng. Tham chiếu [#18](https://github.com/akita141188/voice-dubbing-runtime/issues/18), không tự nhận đạt 0,95 nếu chưa có phép đo hợp lệ.
5. Có test tự động cho phát hiện profile, reference thiếu/sai, quyền sử dụng và engine không hỗ trợ; chạy regression và CI `windows-python311`.
6. Giữ tương thích CLI/worker schema v1, cách ly process, không tự tải model. Nêu rõ phần còn thiếu nếu PR mới hoàn thành một phần.

## Cách contributor nhận việc

Bình luận vào issue trước khi code, nêu **nguồn của 5 người nói khác nhau**, quyền sử dụng, engine dự kiến và kế hoạch test. Chờ thống nhất phạm vi, sau đó mở PR nhỏ vào `develop`, liên kết issue và đính kèm kết quả kiểm thử. Không push trực tiếp `main`/`develop`. Xem [CONTRIBUTING.md](../CONTRIBUTING.md).

## Đề xuất mở rộng tiếp (chưa tạo task)

Tiếng Quảng Đông, Quan thoại Đài Loan, Malay, Tagalog, Khmer, Lào, Myanmar; các phong cách giọng MC/hội thoại và đa độ tuổi cho Trung, Nhật, Hàn. Các mục này cần issue và kiểm tra engine/license riêng; **chưa tính trong mục tiêu 100 giọng**.
