# Bộ truy vấn P5 đã khóa

12 TXT Q01–Q12 từ 12 tác phẩm ngoài kho; 965–1.025 từ/tệp, tổng 12.011 từ. Thời điểm khóa nằm trong `queries.lock.json`. Đã chạy truy hồi chính thức ngày 06/11/2026 tại `gd2/results/p6_official`; khóa và biên bản P5 giữ nguyên trạng thái lịch sử trước truy hồi.

- `query_manifest.csv`: nguồn, nhóm, chương/phần, offset ký tự và hash từng đoạn.
- `outside_corpus_audit.json`: đối chiếu metadata và dấu vết văn bản với cả 1.000 tệp.
- `evaluation_protocol.json`: quy tắc chấm 0/1/2 và P@3, chốt trước truy hồi.
- `queries.lock.json`: hash các đầu vào đã chốt. Không sửa sau khi xem Top-3.

Kiểm tra từ thư mục gốc: `python -m gd2.src.verify_queries`; thêm `--deep` để quét lại nội dung corpus. Không dùng nguồn tại `gd2/sources` để fit đặc trưng.

Q01 là ví dụ chính; Q12 là ca thăm dò được chỉ định trước, chưa phải kết quả kém đã quan sát. Xem [biên bản P5](../../docs/gd2/BIEN_BAN_P5.md) để biết phương pháp và giới hạn bằng chứng.
