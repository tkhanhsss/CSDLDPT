# Bằng chứng chuẩn bị GD2

Hồ sơ chuẩn bị gồm ảnh đối chiếu, mã kiểm tra một lần và ba TXT Gutenberg. Bản ZIP đã kiểm tra đủ 31 tệp nằm tại [archive](archive/preparation_files_snapshot_2026-11-07.zip). Các đường dẫn cũ trong nhật ký mô tả vị trí tại thời điểm lập hồ sơ.

- `project_cleanup_2026-11-07.json`: dọn cache và tệp trung gian báo cáo sau P7, vị trí bản khôi phục ngoài dự án, ZIP đã xác minh và kết quả kiểm tra baseline/báo cáo sau dọn.

- `pre_p4_cleanup.json`: schema v4, kết quả đối chiếu, thời gian nạp thông thường và kiểm thử trước P4.
- `database_schema_simplification.json`: lần thu gọn schema v3.
- `KHAO_SAT_TRUOC_P2.md`: khảo sát lịch sử được tách khỏi kế hoạch hiện hành.

- `GD2_planning_audit.json`: kiểm tra kho ngày 03/11/2026.
- `GD2_metadata_audit.json`: bảng tác phẩm khi vừa tìm lại, trước khi bổ sung tên tập/phần; số nhóm trùng và source hash là của phiên bản lịch sử đó.
- `GD2_volume_verification.json`: đối chiếu nội dung bốn tệp với các tập Project Gutenberg.
- `GD2_metadata_title_changes.json`: bốn title đã bổ sung tập/phần; chỉ số dòng tính cả header CSV.
- `project_reorganization.json`: đường dẫn cũ/mới và hash của 1.033 tệp được chuyển thư mục; tất cả giữ nguyên byte trong lúc di chuyển.
- `pre_gd2_readiness.json`: kết quả kiểm tra cuối sau khi cập nhật metadata, lưu mốc và dọn thư mục.
- `metadata_schema_cleanup.json`: thay đổi cấu trúc metadata theo yêu cầu người dùng ngày 04/11/2026; hash trước/sau, kiểm tra giữ nguyên ba cột còn lại và bản dựng SQLite thay thế.

Các trường đường dẫn/tên nguồn trong nhật ký cũ ghi hiện trạng tại thời điểm kiểm tra, có thể còn dùng bố cục thư mục trước khi dọn. Dùng `project_reorganization.json` để tra vị trí mới. Không dùng các bản kiểm tra lịch sử thay cho `python tools/verify_baseline.py` khi xác minh trạng thái hiện tại.

Các hash nguồn và vị trí cột trong nhật ký sửa title trước đây mô tả thời điểm thực hiện. Sau thay đổi cấu trúc metadata, cột `title` ở vị trí 2, `author` ở vị trí 3. Những CSV lưu trữ đã được thu gọn theo yêu cầu; hash hiện tại của chúng nằm trong nhật ký thay đổi cấu trúc. Các số đo lịch sử được giữ riêng, không dùng làm hash kiểm tra tệp hiện hành.
