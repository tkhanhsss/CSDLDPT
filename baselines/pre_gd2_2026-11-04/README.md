# Mốc trước GD2 — 04/11/2026

Mốc được chốt sau khi bổ sung tên tập/phần cho bốn tệp 0637, 0797, 0927, 0988 và trước khi triển khai GD2.

- `corpus_manifest.json`: đủ 1.000 filename, đường dẫn hiện hành, số byte, SHA-256 nguyên tệp, SHA-256 chuỗi token chuẩn hóa và số từ.
- `asset_manifest.json`: 26 tệp metadata, nhãn, mã nguồn, kết quả thống kê/hình, PDF và nhật ký nhãn GD1; có hash và đường dẫn snapshot.
- `configuration.json`: quy trình tiền xử lý, tham số TF-IDF, cấu hình truy vấn, thứ tự hàng và phiên bản thư viện.
- `stopwords.json`: danh sách stopword tiếng Anh, EXTRA_STOP và hợp của hai danh sách theo mã GD1.
- `status.json`: số liệu đối chiếu và lịch sử bốn title đã sửa.
- `snapshots/`: bản sao nguyên byte của 26 tài sản trong asset manifest.
- `integrity.json`: hash các tệp trong mốc, ngoại trừ chính tệp integrity.

Các phiên bản lúc chốt khớp GD1: Python 3.10.11; NumPy 2.2.6; pandas 2.3.3; matplotlib 3.10.9; scikit-learn 1.7.2; SciPy 1.15.3; NLTK 3.10.3.

Kho có tổng 34.344.608 từ, nhỏ nhất 12.072, lớn nhất 53.913; số từ từng tệp khớp `gd1/results/doc_stats.csv`. Bảng tác phẩm và nhãn đều phủ đủ 1.000 tệp. Bốn title thay đổi không tác động nội dung TXT.

Mốc này ghi nhận dữ liệu đã chốt, không phải bản sao đầy đủ 1.000 TXT. Corpus được giữ tại `data/corpus`; hash dùng phát hiện thay đổi, không tự phục hồi tệp nếu tệp bị mất. Snapshot đã lưu đầy đủ các tài sản GD1 và metadata nhỏ hơn.

Chưa lưu vocabulary, IDF hoặc ma trận TF-IDF mới. Số 34.416 là kết quả GD1 phải đối chiếu khi tái lập ở GD2.

Kiểm tra từ thư mục gốc: `python tools/verify_baseline.py`. Không ghi đè mốc này để che khác biệt; nếu có thay đổi dữ liệu được quyết định sau này, tạo mốc mới với lý do rõ ràng.

## Cập nhật cấu trúc metadata theo yêu cầu người dùng

Ngày 04/11/2026, đã bỏ cột tên tệp trước đổi tên. CSV hiện hành và bản snapshot chỉ còn `new_filename`, `title`, `author`; 1.000 khóa, tên sách và tác giả được giữ nguyên. Asset manifest và integrity được cập nhật có ghi nhận tại `metadata_schema_revision.json`. Nội dung corpus, cấu hình và số liệu đặc trưng không thay đổi.
