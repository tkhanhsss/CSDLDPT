# Biên bản P2 — tái lập đặc trưng GD2

Ngày thực hiện: 04/11/2026, múi giờ Asia/Bangkok. Bản dựng hoàn tất lúc 17:37:06 +07:00. **Kết luận: P2 đạt, đủ điều kiện chuyển sang P3 lưu SQLite.**

Cập nhật cấu trúc metadata ngày 04/11/2026: CSV đã thu gọn còn `new_filename`, `title`, `author` theo yêu cầu người dùng. Các ma trận, ánh xạ, df/IDF và norm P2 vẫn nguyên byte; chỉ cập nhật tham chiếu hash integrity trong biên bản JSON, có ghi nhận `maintenance`. Số liệu và thời gian dưới đây thuộc lần chạy P2 ban đầu.

## Phạm vi và đầu vào

Thực hiện P2 theo `KE_HOACH_GD2.md`: tái lập tiền xử lý và toàn bộ đặc trưng của 1.000 tệp, tạo dữ liệu tham chiếu cho bước lưu CSDL. Mã mới nằm trong `gd2/src`; cấu hình và 402 stopword được sao chép nguyên byte từ `baselines/pre_gd2_2026-11-04`. Mã nguồn, dữ liệu, metadata, nhãn và kết quả GD1 giữ nguyên.

Kiểm tra baseline trước và sau khi dựng đều `ok: true`: 1.000 tệp corpus, 26 tài sản GD1, 32 tệp baseline, 1.000 dòng metadata và 1.000 dòng nhãn. Mỗi tệp còn được kiểm tra SHA-256 nguyên byte, SHA-256 chuỗi token chuẩn hóa và số từ trong luồng dựng. Tổng số từ trước lọc là **34.344.608**, khớp baseline.

Môi trường xử lý thực tế khớp baseline: Python 3.10.11, NumPy 2.2.6, SciPy 1.15.3, scikit-learn 1.7.2 và NLTK 3.10.3.

## Cách dựng và đối chiếu

- Tiền xử lý giữ đúng chuẩn hóa dấu nháy, regex, lowercase, lấy base, lọc stopword trước Porter của GD1. Chỉ bổ sung bộ nhớ đệm stem để tránh tính lại cùng base.
- Dựng count nguyên bằng `CountVectorizer`, áp dụng `min_df=3`, `max_df=0.6`, unigram; tính TF-IDF bằng `TfidfTransformer` với log TF, smooth IDF, L2 và float64.
- Kiểm tra lại df và công thức `idf = ln((1+N)/(1+df)) + 1`, sau đó tính độc lập `weight = (1+ln(count)) × idf / l2_raw` cho mọi phần tử khác 0.
- Dựng độc lập cả 1.000 tệp bằng `TfidfVectorizer` gọi trực tiếp tokenizer/Porter không cache từ mã `gd1/gd1_stats.py`, không sửa mã nguồn GD1. Đối chiếu vocabulary, IDF và toàn bộ ma trận với GD2.
- So sánh 5 term nổi bật ở từng tệp với `gd1/results/doc_top_terms.csv`; lưu từng dòng đối chiếu. Lưu và đọc lại các ma trận/array, rồi kiểm tra lại công thức và ánh xạ.

## Kết quả thực chạy

| Kiểm tra | Kết quả |
|---|---:|
| Kích thước ma trận | **1.000 × 34.416** |
| Số phần tử khác 0 — nnz | **1.926.766** |
| Hàng vector rỗng | 0 |
| df nhỏ nhất / lớn nhất | 3 / 600 |
| IDF nhỏ nhất | 1,510159844780013 |
| IDF lớn nhất | 6,52246041819533 |
| Norm L2 nhỏ nhất | 0,9999999999999972 |
| Norm L2 lớn nhất | 1,0000000000000016 |
| Sai lệch norm L2 lớn nhất so với 1 | 2,7755575615628914 × 10⁻¹⁵ |
| Sai lệch lớn nhất khi tính lại công thức trọng số | 3,885780586188048 × 10⁻¹⁶ |
| Vocabulary so với bản dựng mã GD1 | Khớp chính xác cả 34.416 term |
| Sai lệch IDF so với bản dựng mã GD1 | 0 |
| Sai lệch TF-IDF lớn nhất so với bản dựng mã GD1 | 3,885780586188048 × 10⁻¹⁶ |
| Top-5 term so với CSV GD1 lịch sử | **1.000/1.000 tệp khớp đúng thứ tự** |
| Sai lệch sau lưu–đọc NPZ | 0, với cả count và TF-IDF |
| Ngưỡng sai số chấp nhận | 10⁻¹⁰ |

Các sai số float64 đều nhỏ hơn ngưỡng. Khác biệt cỡ 10⁻¹⁶ giữa hai đường dựng phù hợp với sai số cộng/tính chuẩn theo thứ tự phần tử thưa; không có sai khác vocabulary hoặc IDF.

Ví dụ term được giữ: `detect` có df = 503, IDF = 1,686178511243852; `ocean` có df = 496, IDF = 1,700164753218592. Tệp `term_samples.csv` ghi cả trạng thái không có trong vocabulary của những term mẫu khác; trạng thái đó không được hiểu là term chắc chắn không xuất hiện trong corpus.

Thời gian trên máy đang chạy: dựng GD2 **28,290 giây**; dựng và đối chiếu mã GD1 độc lập **179,861 giây**; tổng trước khi ghi biên bản JSON **212,166 giây**. Đây là số đo một lần chạy P2, có cả kiểm tra đầu vào; chưa phải phép đo hiệu năng tìm kiếm P6 hoặc thời gian dựng CSDL P3.

Dung lượng thực của `counts.npz`: **4.495.059 byte**; `tfidf.npz`: **13.631.922 byte**. Đây là tệp CSR nén, không phải dung lượng SQLite.

## Sản phẩm và cách kiểm tra lại

- [Hướng dẫn chạy và hợp đồng dữ liệu](../../gd2/README.md).
- [Biên bản máy đọc được, hash và số liệu đầy đủ](../../gd2/artifacts/p2/verification.json).
- [Ánh xạ tài liệu](../../gd2/artifacts/p2/documents.csv), [ánh xạ term, df và IDF](../../gd2/artifacts/p2/terms.csv).
- [Đối chiếu top-5 của 1.000 tệp](../../gd2/artifacts/p2/top5_comparison.csv).
- [Mẫu tiền xử lý từ corpus](../../gd2/artifacts/p2/preprocess_sample.csv), [term mẫu](../../gd2/artifacts/p2/term_samples.csv).
- `gd2/artifacts/p2/counts.npz`, `tfidf.npz`, `df.npy`, `idf.npy`, `l2_raw.npy`: dữ liệu đầy đủ để P3 kiểm chứng lưu–đọc CSDL.

Ánh xạ được cố định: filename tăng dần, `doc_id = row_index + 1`; term tăng dần, `term_id = column_index + 1`. Các trọng số và IDF lưu đủ độ chính xác, chỉ làm tròn khi trình bày.

```powershell
python -m unittest discover -s gd2/tests -v
python -m gd2.src.verify_features
```

Đã chạy: **4/4 kiểm thử đạt**, gồm tiền xử lý các dấu nháy/từ viết tắt/stopword, tính tay TF-IDF, hàng rỗng và lưu–đọc, phát hiện trọng số/count/ánh xạ lỗi. Lệnh kiểm tra artifact riêng cũng đạt: kiểm tra hash 10 tệp đầu ra, hash nguồn dựng, baseline và toàn bộ công thức trên dữ liệu đã lưu.

Để tái lập từ corpus vào thư mục mới:

```powershell
python -u -m gd2.src.build_features --out work/p2_recheck
```

## Giới hạn bằng chứng và bước tiếp theo

GD1 không lưu vocabulary, IDF hoặc ma trận gốc. Vì vậy không tuyên bố khôi phục từng bit của ma trận lịch sử: đối chiếu lịch sử gồm số chiều và top-5 term; đối chiếu toàn bộ trọng số là giữa hai lần dựng mới từ cùng corpus bằng mã GD1 gốc và mã GD2.

P3 tiếp nhận bundle đã kiểm chứng này để tạo năm bảng SQLite theo kế hoạch, nạp đủ 1.926.766 dòng `document_terms`, rồi đọc lại ma trận và so sánh với `tfidf.npz`. P2 chưa thực hiện lưu CSDL, tìm kiếm hoặc đánh giá chất lượng truy hồi. Những công việc đó tiếp tục theo P3–P6.
