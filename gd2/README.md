# GD2 — hoàn tất P2–P7

P7 đã có [PDF hợp nhất](report/GD1-GD2-CSDLDPT-23-03.pdf) và [bản Word](report/GD1-GD2-CSDLDPT-23-03.docx), 40 trang, 30 bảng, 7 hình. Xem [hướng dẫn báo cáo](report/README.md) và [biên bản P7](../docs/gd2/BIEN_BAN_P7.md).

P3 đã tạo `database/documents.sqlite`: 1.000 tài liệu, 34.416 term, 1.926.766 trọng số; ma trận đọc lại khớp P2 hoàn toàn. Xem [biên bản P3](../docs/gd2/BIEN_BAN_P3.md).

Kiểm tra CSDL hiện có bằng `python -m gd2.src.verify_database`. Dựng bản mới bằng `python -u -m gd2.src.build_database --out work/documents_recheck.sqlite`. Tham số `--p2` cho phép chỉ định thư mục tham chiếu P2 khác đã qua kiểm chứng.

`database/schema.sql` định nghĩa năm bảng; `database/verify.sql` chứa truy vấn kiểm chứng thủ công. `database/documents.verification.json` lưu hash CSDL, nguồn, số liệu và thời gian. SQLite phải từ 3.37 để hỗ trợ STRICT; bản hiện tại dùng 3.40.1.

CSV metadata hiện có đúng ba cột `new_filename`, `title`, `author`; CSDL dùng schema v4 tương ứng. Thay đổi cấu trúc ngày 04/11/2026 được ghi nhận theo các lần cập nhật tại `docs/audit/metadata_schema_cleanup.json`, `database_schema_simplification.json` và `pre_p4_cleanup.json`; các artifact đặc trưng P2 không thay đổi.

Đầu vào P4:

Xem [hợp đồng P4](../docs/gd2/HOP_DONG_P4.md) về một/nhiều TXT, ba tệp kết quả, `--trace` và xử lý ngoại lệ. CLI đã triển khai; xem [biên bản P4](../docs/gd2/BIEN_BAN_P4.md).

```python
from pathlib import Path
from gd2.src.database import load_database

index = load_database(Path("gd2/database/documents.sqlite"))
X = index.features.tfidf
idf = index.features.idf
terms = index.features.terms
documents = index.features.documents
```

Hàm đọc kiểm tra schema, trạng thái, tham số đặc trưng, kích thước, ánh xạ và giá trị vector trong RAM rồi trả dữ liệu từ SQLite. Kiểm tra sâu integrity/FK/df/công thức và đối chiếu P2 nằm trong lệnh verify_database; không chạy lại trong mỗi phiên tìm kiếm. Metadata đã nối theo filename. Hàm không đọc ma trận NPZ. Các tệp P2 bên dưới vẫn được giữ làm tham chiếu để kiểm chứng CSDL.

## P2: tái lập đặc trưng

Chạy các lệnh dưới đây từ thư mục gốc `CSDLDPT`, bằng Python 3.10.11. Các phiên bản thư viện nằm trong `requirements.txt` và baseline; môi trường hiện tại đã có đủ phiên bản. Khi cài môi trường mới, dùng `python -m pip install -r gd2/requirements.txt`.

```powershell
python tools/verify_baseline.py
python -m unittest discover -s gd2/tests -v
python -m gd2.src.verify_features
```

Để dựng lại đặc trưng, dùng `python -u -m gd2.src.build_features --out work/p2_recheck`. Chọn một thư mục đầu ra mới cho mỗi lần chạy. Đặc trưng chính thức nằm ở `gd2/artifacts/p2`.

## Quy trình

1. Xác minh baseline, bản sao cấu hình/stopword và phiên bản Python, NumPy, SciPy, scikit-learn, NLTK.
2. Đọc đúng 1.000 TXT theo manifest, kiểm tra hash nguyên tệp, hash chuỗi token và số từ. Hàng sắp theo filename tăng dần.
3. Chuẩn hóa ba dấu nháy, chữ thường, regex GD1, lấy base trước dấu nháy, loại base ngắn và stopword trước Porter. Bộ nhớ đệm kết quả Porter chỉ giảm tính toán lặp, không đổi số lượng/thứ tự token.
4. `CountVectorizer` dựng count nguyên với `min_df=3`, `max_df=0.6`; `TfidfTransformer` tính log TF, smooth IDF và L2 bằng float64. Cột sắp theo term tăng dần.
5. Kiểm tra kích thước, tọa độ khác 0, df, công thức IDF, norm trước/sau L2 và công thức từng trọng số.
6. Dựng độc lập toàn bộ ma trận bằng `TfidfVectorizer` với hàm `content_tokens` và Porter không cache của mã GD1 gốc. So sánh vocabulary, IDF, toàn bộ trọng số và CSV top-5 lịch sử của 1.000 tệp.
7. Lưu–đọc lại dữ liệu, xác nhận không mất độ chính xác, kiểm tra baseline lần cuối rồi ghi biên bản có hash và thời gian thực chạy.

Không gọi `main()` thống kê GD1 và không ghi vào corpus, baseline hoặc kết quả GD1. Không dựng SVD/KMeans trong P2.

## Sản phẩm

| Tệp trong `artifacts/p2` | Nội dung |
|---|---|
| `counts.npz` | CSR int64: số lần stem xuất hiện, chỉ giữ vocabulary sau lọc df |
| `tfidf.npz` | CSR float64: toàn bộ trọng số TF-IDF đã chuẩn hóa L2 |
| `documents.csv` | `row_index`, `doc_id`, filename, đường dẫn, hash nguyên tệp và số từ |
| `terms.csv` | `column_index`, `term_id`, term, df và IDF đầy đủ độ chính xác |
| `df.npy`, `idf.npy`, `l2_raw.npy` | df/IDF theo cột và norm trước L2 theo hàng |
| `top5_comparison.csv` | Đối chiếu 5 term nổi bật với GD1 ở từng tệp |
| `preprocess_sample.csv` | 30 token đầu của `book_0001.txt`, quyết định giữ/bỏ và stem; không phải Q01 |
| `term_samples.csv` | Các term nội dung mẫu, df, IDF và trạng thái có trong vocabulary |
| `verification.json` | Số liệu, phiên bản, đối chiếu, thời gian, hash nguồn và từng artifact |

`doc_id = row_index + 1`, `term_id = column_index + 1`. Chỉ số ma trận bắt đầu từ 0, ID dành cho CSDL bắt đầu từ 1. `counts` và `tfidf` có cùng tọa độ khác 0. Công thức đối chiếu là `weight = (1 + ln(count)) * idf / l2_raw`. Không làm tròn dữ liệu lưu; không dùng pickle.

Các tệp trong `config` là bản sao nguyên byte từ baseline. Trường `tfidf_rebuilt: false` bên trong bản sao là trạng thái tại thời điểm chốt baseline; trạng thái bản dựng hiện tại nằm trong `artifacts/p2/verification.json`.

## Đầu vào cho P3

`from gd2.src.features import load_features` trả về `FeatureBundle` gồm count, TF-IDF, df, IDF, norm và ánh xạ. Kiểm tra bundle bằng `python -m gd2.src.verify_features` trước khi dùng. Metadata/nhãn sẽ được nối qua filename ở P3.

Các NPZ này là dữ liệu tham chiếu để kiểm tra việc lưu–đọc SQLite ở P3. Chương trình tìm kiếm P4 sẽ đọc đặc trưng từ CSDL theo kế hoạch.

GD1 không lưu ma trận gốc, nên đối chiếu lịch sử chỉ có số chiều và top-5 term. Phép so sánh toàn bộ trọng số là giữa hai lần dựng mới dùng mã GD2 và mã GD1 gốc, không phải bằng chứng khôi phục từng bit của ma trận lịch sử.

## Tìm kiếm P4

Từ thư mục gốc, chạy `python -m gd2.src.search --query gd2/queries/Q01.txt --out work/search_q01 --trace`. Bỏ `--trace` khi chỉ cần Top-3 và ba TXT. Truyền nhiều đường dẫn sau `--query` để nạp kho một lần cho cả lô. Chọn một thư mục đầu ra mới cho mỗi lần chạy.

Kiểm chứng kỹ thuật bằng `python -m gd2.src.verify_search --out work/p4_recheck`. Bằng chứng cuối nằm tại `gd2/artifacts/p4_final`.

## Bộ truy vấn P5

Đã khóa Q01–Q12 trong `gd2/queries`, gồm 12 tác phẩm ngoài kho, sáu nhóm, 965–1.025 từ/tệp. Nguồn toàn văn nằm ngoài corpus tại `gd2/sources`. Kiểm tra bằng `python -m gd2.src.verify_queries`; thêm `--deep` để quét lại nội dung. Đã chạy bộ chính thức ở P6, không sửa khóa lịch sử P5. Xem [biên bản P5](../docs/gd2/BIEN_BAN_P5.md).

## Thực nghiệm P6

Đã chạy đủ 12 truy vấn tại `results/p6_official`, mỗi câu có Top-3, ba TXT và trace. Đối chiếu độc lập 12.000 điểm và hash của 36 bản sao đều đạt; 27 kiểm thử Python đạt. `evaluation/p6/Q01` chứa bảng rút gọn cho báo cáo; trace đầy đủ giữ trong lần chạy gốc.

Hai thành viên chấm riêng bằng `evaluation/p6/reviewer_A.html` và `reviewer_B.html`, xuất CSV rồi đối chiếu và điền `consensus.csv`. Xem [hướng dẫn chấm](evaluation/p6/README.md). Đã chốt hai bất đồng P034 = 1 và P003 = 1 theo phản hồi người dùng. Kết quả cuối tại `evaluation/p6/grading_final`: Mean P@3 = 11,11%, 3/12 truy vấn có kết quả mức 2; P6 đã nghiệm thu. Hai phiếu độc lập vẫn nguyên byte.

```powershell
python -m gd2.src.evaluate prepare --run gd2/results/p6_official --out work/p6_new
python -m gd2.src.benchmark --out work/performance_new
python -m gd2.src.evaluate grade --out work/grading_recheck
node gd2/tests/check_grading_forms.cjs
```

Chỉ chạy `prepare` khi cần một bộ phiếu mới; không tạo lại bộ phiếu đang chấm. Lệnh `grade` đọc ba CSV trong `evaluation/p6`, giữ ảnh chụp điểm ban đầu và bảng so sánh, chỉ xuất chỉ số đầy đủ khi đủ 36 cặp ở cả ba phiếu. Không ghi đè thư mục kết quả.

Phép đo báo cáo ở `evaluation/p6/performance_final`: năm lần nạp SQLite, một lần làm nóng + năm lần đo mỗi truy vấn. Trung vị nạp 4,110522 giây; trung vị 60 lượt truy vấn đã nạp X là 6,943200 ms, không gồm trace/sao chép/khởi động Python. Ca vector rỗng nằm riêng, không tham gia bộ 12 câu. Xem [biên bản P6](../docs/gd2/BIEN_BAN_P6.md) để biết phạm vi và ca hạn chế có bằng chứng.
