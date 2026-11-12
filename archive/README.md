# Lịch sử chuẩn bị trước GD2

`preparation_2026-11-04.zip` lưu 31 tệp tạm của các bước kiểm tra và chỉnh metadata: bản trích/render PDF, mã kiểm tra một lần, ba nguồn TXT Project Gutenberg, bản CSV trước khi sửa tên và ảnh kiểm tra ô CSV. ZIP đã được đọc lại và đối chiếu SHA-256 từng tệp.

Đợt dọn ngày 07/11/2026 đã đóng gói bản thư mục chuẩn bị thành `preparation_files_snapshot_2026-11-07.zip`, kiểm tra CRC và SHA256 đủ 31 tệp. Một số script trong bản thư mục khác ZIP ban đầu, vì vậy giữ cả hai ZIP để bảo toàn lịch sử. Bản thư mục đã được chuyển ra thư mục tạm ngoài dự án; vị trí khôi phục ghi trong `docs/audit/project_cleanup_2026-11-07.json`.

Không đóng gói thư viện `node_modules` liên kết tới runtime của Codex vào ZIP. Junction đã đi cùng bản thư mục ra ngoài dự án; thư viện runtime đích không bị chỉnh sửa. Không đưa thư viện này vào bộ dữ liệu.

Các script trong ZIP phản ánh đường dẫn ở thời điểm chuẩn bị và được giữ để tra cứu lịch sử, không phải công cụ chạy hiện hành. Dùng `tools/verify_baseline.py` và hướng dẫn trong README gốc để làm việc với bố cục mới.

Không dùng các nguồn TXT hoặc snapshot trong archive làm văn bản kho. Corpus chính chỉ nằm ở `data/corpus`.
