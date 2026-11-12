# Biên bản P7 — Báo cáo hợp nhất GD1 và GD2

Hoàn tất ngày 07/11/2026. Báo cáo được soạn từ số liệu P2–P6 đã chốt, xuất PDF bằng Microsoft Word và kiểm tra đủ 40 trang.

## Sản phẩm

- [Bản Word có thể chỉnh sửa](../../gd2/report/GD1-GD2-CSDLDPT-23-03.docx).
- [PDF hợp nhất để nộp](../../gd2/report/GD1-GD2-CSDLDPT-23-03.pdf).
- [Bằng chứng kiểm tra và SHA256](../../gd2/artifacts/p7/verification.json).
- [Cách dựng lại báo cáo](../../gd2/report/README.md).

PDF có 40 trang, 30 bảng được đánh số và 7 hình. Trang 1–6 là phần đầu; Chương 1–2 ở trang 7–15; Chương 3 ở trang 16–20; Chương 4 ở trang 21–33; kết luận, tham khảo và phụ lục ở trang 34–40. Phần bổ sung từ Chương 3 đến hết phụ lục là 25 trang, phù hợp mức dung lượng biên tập trong kế hoạch.

## Nội dung đã thực hiện

Giữ nội dung Chương 1–2 từ DOCX GD1, gồm văn bản, bảng, công thức và hình; không sửa PDF GD1 đã nộp. Cập nhật bìa, mục lục, danh mục hình/bảng, từ viết tắt và Mở đầu cho bốn chương. Phần đầu Chương 3 làm rõ đơn vị tệp/tập tác phẩm, khác biệt ba token tiêu đề Grania và việc đọc bằng UTF-8-sig không đồng nghĩa tệp có BOM. Danh mục mới mô tả NLTK dùng Porter; nguồn stopword là scikit-learn cộng EXTRA_STOP của GD1.

Chương 3 trình bày năm bảng SQLite, khóa và ràng buộc, quy trình dựng, số bản ghi thật, ví dụ SQL và kiểm chứng lưu–nạp. Chương 4 trình bày CLI, I/O module, nguồn 12 truy vấn, trace Q01 từ token đến đóng góp term, metadata ba tệp đầu ra, đủ 36 kết quả với điểm của hai người và điểm chốt, P@3, hiệu năng cùng ca hạn chế có trích dẫn nội dung. Phụ lục giữ toàn văn Q01, nguồn và vị trí 12 đoạn, cấu hình, đường dẫn bằng chứng và schema SQL.

Mean P@3 = 11,11%; 3/12 truy vấn có kết quả mức 2; đồng thuận ban đầu 34/36 = 94,44%. Điểm chốt P034 và P003 đều là 1. Số đo chính lấy từ `performance_final`: trung vị truy vấn 6,943200 ms khi đã nạp chỉ mục, trung vị nạp 4,110522 giây. Báo cáo tách rõ tính đúng kỹ thuật và chất lượng liên quan, nêu phạm vi phép đo và giới hạn bộ thử.

## Kiểm tra

- So sánh các phần tử nội dung Chương 1–2 khi dựng; sau Word lưu lại, đối chiếu văn bản, bảng và công thức theo thứ tự đều khớp.
- Bảo toàn 19 đối tượng công thức và hash 5 ảnh gốc gồm logo cùng bốn hình GD1.
- Đối chiếu đủ 36 dòng chấm với `grading_final/comparison.csv` và điểm cosine của lần chạy chính thức.
- Toàn văn Q01 trong phụ lục giữ nguyên nội dung, chỉ dàn lại dòng; đối chiếu sau chuẩn hóa khoảng trắng đạt.
- 15 tệp dữ liệu/mã/bằng chứng đóng băng được kiểm tra theo hash của P6. Các Markdown trong bản chụp P6 là lịch sử; README và kế hoạch được cập nhật trạng thái P7, không sửa bản chụp P6 để làm khớp lịch sử.
- `python tools/verify_baseline.py`: `ok: true`, kiểm tra 1.000 tệp corpus, 26 tài sản GD1 và 33 tệp baseline; không có vấn đề.
- Mục lục, danh mục hình/bảng đã cập nhật; số trang liên tục. Quét lỗi field, placeholder và các trường metadata đã bỏ đều đạt.
- Render PDF thành 40 PNG, xem từng trang: không có chữ bị cắt, bảng tràn, công thức vỡ hay nhãn sơ đồ đè nhau. Bảng mới nhiều trang lặp lại tiêu đề cột. Mục lục đã gọn trong một trang.

Trình render đóng gói không chạy được vì môi trường Windows thiếu `soffice.exe`; dùng Microsoft Word 16.0 COM để cập nhật field, lưu DOCX và xuất chính DOCX đó thành PDF. Poppler dựng PNG để kiểm tra hình thức. Đây là thay đổi công cụ xuất, không phải tạo một bản PDF có nội dung độc lập.

## Kết luận

P7 đạt checklist báo cáo. CSDL, mã tìm kiếm, corpus, truy vấn khóa và hai phiếu chấm gốc giữ nguyên. Phạm vi GD2 đã hoàn tất; giao diện demo thuộc GD3 và chưa được triển khai trong P7.
