# Khảo sát lịch sử trước P2

Nội dung dưới đây mô tả thời điểm chuẩn bị, không phải hiện trạng hệ thống.

## 2. Những gì đã được kiểm tra

Đã đọc đủ 14 trang báo cáo GD1, kiểm tra trực quan sơ đồ và các trang công thức, đọc mã `gd1/gd1_stats.py`, các kết quả trong `gd1/results`, tệp nhãn và nhật ký rà soát nhãn. Đã đọc lại toàn bộ 1.000 tệp để kiểm tra số từ, BOM và trùng chuỗi token. Chưa chạy lại việc xây dựng TF-IDF, chưa xây CSDL hoặc thực hiện truy vấn GD2.

| Nội dung | Bằng chứng hiện có | Kết luận phục vụ kế hoạch |
|---|---|---|
| Kho văn bản | 1.000 tệp `book_0001.txt` đến `book_1000.txt` | Giữ nguyên tệp và mã định danh |
| Số từ tính lại | Tổng 34.344.608; nhỏ nhất 12.072; lớn nhất 53.913 | Khớp `doc_stats.csv` ở cả 1.000 tệp; không tệp nào dưới 12.000 từ |
| Nhãn | 1.000 dòng, 1.000 tên tệp phân biệt, 14 nhóm | Phân bố khớp GD1; không thiếu hay thừa tên tệp |
| Trùng nội dung | Không có nhóm trùng SHA-256 của chuỗi token đã chuẩn hóa trong lần kiểm tra này | Không suy rộng thành đã chứng minh mọi tệp là tác phẩm hoàn chỉnh hoặc không cùng tác phẩm |
| Đặc trưng | GD1 ghi 34.416 chiều; mã nguồn dùng đúng cấu hình đã mô tả | Đây là mốc cần tái lập; lần chuẩn bị này chưa xác nhận lại số chiều bằng chạy TF-IDF |
| Lưu đặc trưng | Có CSV chứa 5 term nổi bật/tệp, không thấy CSDL, vocabulary, vectorizer hoặc ma trận được lưu ra đĩa | Phải xây và lưu toàn bộ vector; 5 term/tệp không thay thế được ma trận |
| Tác phẩm–tác giả | Đã tìm lại `data/metadata/selected_stories.csv`: 1.000 dòng, đủ tên/tác giả, ánh xạ đúng tập 1.000 filename, không thiếu/thừa/trùng mã | Dùng bảng gốc; nối qua `new_filename`; đã xác minh tập/phần của hai nhóm cùng tác phẩm |
| Mã hóa | 1.000 tệp đọc được bằng UTF-8; cả 1.000 không có ba byte BOM ở đầu | `utf-8-sig` là cách đọc chấp nhận cả tệp có và không có BOM; câu GD1 nói “có BOM” chưa chính xác |
| Nguồn soạn báo cáo | Hiện chỉ thấy PDF GD1, chưa thấy DOCX/LaTeX | Ưu tiên giữ nguyên PDF đã nộp và ghép phần bổ sung có cấu trúc |

Chi tiết kiểm tra kho ngày 03/11 được lưu tại `docs/audit/GD2_planning_audit.json`; kiểm tra bảng vừa tìm lại ngày 04/11 tại `docs/audit/GD2_metadata_audit.json`. Đây là kiểm tra hiện trạng, không phải kết quả thực nghiệm tìm kiếm. Báo cáo kiểm tra ngày 03/11 được giữ làm mốc lịch sử.

