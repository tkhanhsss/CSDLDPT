# Báo cáo hợp nhất GD1 và GD2

P7 hoàn tất ngày 07/11/2026. Dùng [PDF](GD1-GD2-CSDLDPT-23-03.pdf) để nộp; [DOCX](GD1-GD2-CSDLDPT-23-03.docx) là bản chỉnh sửa. Bản PDF có 40 trang, 30 bảng và 7 hình. Biên bản và các giới hạn kiểm tra nằm ở [BIEN_BAN_P7.md](../../docs/gd2/BIEN_BAN_P7.md).

## Các tệp hỗ trợ

- `build_report.py`: đọc DOCX GD1 và bằng chứng P2–P6, dựng hình và báo cáo; kiểm tra nội dung GD1 trước khi lưu.
- `render_word.ps1`: mở bản báo cáo do P7 tạo trong Word ẩn, cập nhật field, lưu và xuất PDF. Không mở nguồn GD1 để ghi.
- `verify_report.py`: đối chiếu nội dung GD1, công thức/ảnh, toàn văn Q01, 36 dòng điểm chấm, hash P6, số trang và caption.
- `assets`: ba sơ đồ của Chương 3–4.
- `work`: hợp đồng mẫu, inventory và các manifest kiểm tra. Các PNG, PDF tham chiếu, bản trích văn bản và script cập nhật một lần đã được dọn ra ngoài dự án ngày 07/11/2026; xem `../../docs/audit/project_cleanup_2026-11-07.json` để khôi phục nếu cần.
- `../artifacts/p7/verification.json`: kết quả kiểm tra và hash sản phẩm cuối.

## Dựng lại

Dùng Python của bộ runtime tài liệu có `python-docx`, Pillow, lxml và pypdf; dùng Microsoft Word trên Windows để xuất. Môi trường soạn báo cáo độc lập với môi trường Python 3.10.11 đã khóa cho tìm kiếm. Không cài các thư viện tài liệu vào môi trường tìm kiếm chỉ để xuất báo cáo.

Từ thư mục gốc dự án, với `$ReportPython` trỏ đến Python có các thư viện trên:

```powershell
& $ReportPython gd2/report/build_report.py
& ./gd2/report/render_word.ps1
& $ReportPython gd2/report/verify_report.py
```

Lệnh dựng ghi lại DOCX/PDF cùng tên, vì vậy hãy giữ riêng các chỉnh sửa thủ công trước khi dựng lại. Chạy verifier sau khi đã xuất PDF. Một bản dựng mới phải render và kiểm tra hình thức lại; kết quả kiểm tra hình thức cũ chỉ áp dụng cho hash PDF đã ghi trong `work/visual_review.json`.

Các số liệu đến từ `grading_final`, `performance_final`, lần chạy `p6_official`, CSDL và biên bản P2/P3. Markdown của các mốc trước có thể được cập nhật tiến độ; hash dữ liệu, mã và bằng chứng tính toán P6 vẫn phải khớp. Không dựng lại đặc trưng hay chạy lại thực nghiệm khi chỉ soạn báo cáo.
