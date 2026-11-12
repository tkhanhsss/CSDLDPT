# Biên bản P3 — lưu đặc trưng vào SQLite

Ngày thực hiện: 04/11/2026, múi giờ Asia/Bangkok. Bản dựng bắt đầu lúc 18:49:51 +07:00. **Kết luận: P3 đạt, đủ điều kiện chuyển sang P4 tìm kiếm và xuất trace.**

Build ID: `gd2-p3-0274798c40134e5e91eb3452500cda71`.

## Đầu vào và sản phẩm

Đầu vào là bộ đặc trưng P2 tại `gd2/artifacts/p2`, metadata/nhãn đã chốt. Trước và sau khi nhập CSDL, bộ kiểm tra P2 xác nhận hash artifact, nguồn dựng, baseline và công thức đặc trưng đều đạt. Không fit lại, không thay nội dung corpus, mã/kết quả GD1 hoặc artifact đặc trưng P2. Bản dựng hiện hành dùng schema v4 và CSV ba cột theo yêu cầu người dùng; thay đổi metadata và hash tham chiếu được ghi nhận trong `docs/audit/metadata_schema_cleanup.json`.

- [CSDL hoàn chỉnh](../../gd2/database/documents.sqlite).
- [Schema SQL](../../gd2/database/schema.sql), [các truy vấn kiểm chứng](../../gd2/database/verify.sql).
- [Biên bản JSON: hash, số liệu, thời gian và phân bố nhãn](../../gd2/database/documents.verification.json).
- Mã nguồn: `gd2/src/database.py`, `build_database.py`, `verify_database.py`.
- Kiểm thử mới: `gd2/tests/test_database.py`.

## Cách lưu và nạp

CSDL có đúng năm bảng theo kế hoạch, một bản dựng cho mỗi tệp SQLite. `build_info` lưu cấu hình, phiên bản, hash corpus manifest, mã tiền xử lý, stopword, biên bản P2 và nguồn P3; chỉ có một dòng mô tả bản dựng. `documents` lưu đường dẫn TXT tương đối, metadata, hash nguyên tệp và norm trước L2. `terms` chứa vocabulary, df, IDF. `document_terms` lưu đủ số lần xuất hiện và trọng số khác 0; không lưu mỗi top-5.

Schema dùng SQLite STRICT, khóa chính/UNIQUE/CHECK, khóa ngoại và chỉ mục `idx_document_terms_term_id`. Bảng `document_terms` dùng khóa ghép `(doc_id, term_id)` với `WITHOUT ROWID`. SQLite thực tế: **3.40.1**; schema cần SQLite từ 3.37.

Mọi kết nối bật và kiểm tra `PRAGMA foreign_keys=ON` trước transaction. Tạo schema và nhập toàn bộ năm bảng trong cùng transaction, kiểm tra integrity/FK/df/công thức và đối chiếu P2 trước khi đổi trạng thái sang `complete` rồi commit. Nếu kiểm tra lỗi thì rollback cả schema lẫn dữ liệu. Chương trình dựng dùng tệp tạm; chỉ công bố CSDL sau khi mở lại tệp đã commit và kiểm tra đạt. Tên đầu ra đã tồn tại bị từ chối, không ghi đè bản dựng cũ.

Luồng đọc dùng `ORDER BY doc_id`, `ORDER BY term_id` và cặp ID tường minh để dựng CSR. `doc_id = row_index + 1`, `term_id = column_index + 1`; kiểm tra ID liên tiếp và ánh xạ đúng P2. Hàm `load_database(path)` trả về build info, danh mục nhãn và `FeatureBundle` được đọc hoàn toàn từ SQLite; không dùng NPZ để thay dữ liệu CSDL. Kết nối đọc dùng `mode=ro`, `query_only=ON` và một transaction đọc nhất quán.

## Kết quả kiểm chứng

| Nội dung | Kết quả |
|---|---:|
| `build_info` | 1 dòng, trạng thái `complete` |
| `labels` | 14 dòng |
| `documents` | 1.000 dòng |
| `terms` | 34.416 dòng |
| `document_terms` | **1.926.766 dòng**, bằng nnz(P2) |
| Kích thước ma trận đọc lại | 1.000 × 34.416 |
| `PRAGMA integrity_check` | `ok` |
| Vi phạm khóa ngoại | 0 |
| Term có df lệch số tài liệu theo GROUP BY SQL | 0 |
| df nhỏ nhất / lớn nhất | 3 / 600 |
| Vector rỗng | 0 |
| Sai lệch count lớn nhất so với P2 | **0** |
| Sai lệch trọng số lớn nhất so với P2 | **0** |
| df, IDF, norm trước L2 và ánh xạ | Khớp chính xác P2 |
| Metadata hiển thị/nhãn so với bảng nguồn | Khớp toàn bộ |
| Sai lệch norm L2 lớn nhất so với 1 | 2,7755575615628914 × 10⁻¹⁵ |
| Sai lệch lớn nhất khi tính lại công thức trọng số | 3,885780586188048 × 10⁻¹⁶ |
| Ngưỡng sai số chấp nhận | 10⁻¹⁰ |

Count lưu dưới dạng INTEGER, trọng số/IDF/norm dưới dạng REAL; không làm tròn trước khi lưu. Các sai số công thức/L2 là sai số float64 kế thừa từ P2; quá trình lưu–đọc SQLite không tạo thêm sai khác.

## Metadata

CSDL lấy tên tệp, tên sách và tác giả từ CSV ba cột; nhãn lấy từ labels.jsonl. Tên tập/phần trong title được giữ nguyên. Metadata phục vụ hiển thị và liên kết tệp, không tham gia tính trọng số.

## Dung lượng và thời gian đo thật

- Dung lượng SQLite: **67.866.624 byte**, tương đương **64,72265625 MiB**; 16.569 trang × 4.096 byte.
- Nhập dữ liệu, kiểm tra trong transaction và commit: **26,009 giây**.
- Mở lại, nạp CSR và kiểm tra toàn bộ CSDL/đối chiếu P2: **11,056 giây**.
- Tổng từ đầu lệnh đến trước khi ghi biên bản JSON: **39,871 giây**.

Đây là một lần đo P3 trên máy hiện tại. Mốc 11,056 giây bao gồm kiểm tra integrity, công thức và so sánh tham chiếu, không phải thời gian đọc SQL thuần. Chưa đo xử lý/xếp hạng truy vấn P4–P6.

SHA-256 CSDL: `46d8295c0a909a886a8880c4b2898a4f08d939a61d2fe21f1002b6cef9b922ea`.

## Kiểm thử và chạy lại

**11/11 kiểm thử đạt**, gồm 4 kiểm thử P2 và 7 kiểm thử CSDL: lưu–đọc chính xác/Unicode, khóa ngoại và ràng buộc dữ liệu, kết nối chỉ đọc, rollback khi kiểm tra lỗi, từ chối bản dựng chưa hoàn tất hoặc trọng số hỏng, bảo vệ tệp đầu ra có sẵn và phát hiện metadata thiếu/trùng khóa. Lệnh xác minh độc lập kiểm tra hash, nguồn, metadata, toàn bộ ma trận và baseline cũng đạt.

Kiểm tra bản hiện có:

```powershell
python -m unittest discover -s gd2/tests -v
python -m gd2.src.verify_database
```

Dựng lại vào một tệp mới:

```powershell
python -u -m gd2.src.build_database --out work/documents_recheck.sqlite
python -m gd2.src.verify_database --database gd2/database/documents_recheck.sqlite
```

P4 sẽ nạp CSDL này, transform TXT truy vấn bằng vocabulary/IDF cố định, tính cosine và xuất Top-3/trace theo kế hoạch. P3 chưa chạy truy vấn hoặc đo chất lượng truy hồi.

## Hoàn thiện trước P4

Schema v4 có chín trường tài liệu. Hash chuỗi token và mức tin cậy nhãn chỉ giữ trong P2/GD1. Luồng nạp tìm kiếm không chạy SQL integrity, GROUP BY df hoặc tính lại công thức; lệnh verify_database vẫn thực hiện kiểm tra đầy đủ. Cấu hình tương thích được xét trên regex, quy tắc tiền xử lý và tham số TF-IDF; bỏ qua ngày, đường dẫn corpus và ghi chú.

Lần đo luồng nạp thông thường: 3.225 giây; toàn bộ count và TF-IDF được kiểm tra khớp P2, sai lệch bằng 0. Đây là một lần đo tải kho, không phải thời gian tìm kiếm. Hai kiểm thử mới xác nhận tách luồng kiểm tra sâu và phân biệt thay đổi ghi chú với thay đổi phương pháp.
