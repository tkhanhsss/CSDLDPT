# Nội dung làm rõ GD1 để sử dụng trong báo cáo hợp nhất

Chốt ngày 04/11/2026. Tài liệu này cung cấp phần diễn đạt bổ sung cho báo cáo GD1+GD2. PDF GD1 đã nộp được giữ nguyên tại `docs/gd1/GD1-CSDLDPT-23-03.pdf`.

**Lịch xử lý:** theo yêu cầu người dùng, đây là ghi chú biên tập để dùng ở P7 khi viết báo cáo. Chưa cần xử lý thêm vào lúc bắt đầu GD2 và không phải điều kiện chặn các bước kỹ thuật P2–P6.

Phạm vi biên tập theo người dùng: danh mục từ viết tắt và Mở đầu được phép sửa/viết lại cho bản hợp nhất; nội dung Chương 1–2 cần giữ ổn định. Do đó, phần 1–2 dưới đây là nội dung giải thích bổ sung cho Chương 1; phần 3 hướng dẫn sửa trực tiếp danh mục mới. Việc giữ nguyên PDF gốc là lưu hồ sơ, không có nghĩa mọi trang phần đầu phải giữ nguyên trong bản GD1+GD2.

## 1. Đơn vị dữ liệu, tác phẩm và tập/phần

Đoạn đề xuất đưa vào phần chuyển tiếp của báo cáo:

> Bộ dữ liệu gồm 1.000 tệp văn bản tiếng Anh; đơn vị lưu trữ, biểu diễn đặc trưng và xếp hạng là tệp. Một số tệp tương ứng với các tập khác nhau của cùng tác phẩm. Cụ thể, book_0637.txt và book_0797.txt lần lượt chứa Tập I (Phần I–II) và Tập II (Phần III–IV) của Grania; book_0927.txt và book_0988.txt lần lượt chứa Tập 1 và Tập 2 của The Earl’s Promise. Tên tập/phần được bổ sung vào bảng metadata để phân biệt. Vì vậy, mô tả ở mục 1.1 GD1 cần được hiểu theo đơn vị tài liệu lưu trữ: số lượng 1.000 tệp không đồng nghĩa với 1.000 tác phẩm độc lập, và không phải mọi tệp đều chứa toàn bộ một tác phẩm nhiều tập.

Đây là điều chỉnh phạm vi diễn đạt “mỗi tệp là tác phẩm hoàn chỉnh” trong GD1 dựa trên đối chiếu nguồn. Không gộp/xóa các tập; không thay nội dung, nhãn, số từ hoặc số tệp của kho. Tên metadata không tham gia tính TF-IDF hoặc cosine.

| Filename | Title hiện hành trong bảng tác phẩm |
|---|---|
| book_0637.txt | Grania, The Story of an Island (Vol. I, Parts I-II) |
| book_0797.txt | Grania, The Story of an Island (Vol. II, Parts III-IV) |
| book_0927.txt | The Earl's Promise (Vol. 1 of 3) |
| book_0988.txt | The Earl's Promise (Vol. 2 of 3) |

Nguồn đối chiếu: [Grania, Gutenberg #58443](https://www.gutenberg.org/ebooks/58443), [The Earl’s Promise tập 1, #70755](https://www.gutenberg.org/ebooks/70755), [tập 2, #70756](https://www.gutenberg.org/ebooks/70756). Phương pháp và bằng chứng chi tiết: [bản đối chiếu](DOI_CHIEU_CAC_TAP_TAC_PHAM.md).

Khi chọn truy vấn ngoài kho, kiểm tra ở cấp tác phẩm. Một tập khác của tác phẩm đã có trong kho không đáp ứng điều kiện “tác phẩm chưa có trong bộ dữ liệu”.

## 2. Mã hóa UTF-8 và BOM

Đoạn đề xuất:

> Các tệp của bộ dữ liệu hiện tại được mã hóa UTF-8 và không có BOM ở đầu tệp. Chương trình sử dụng bộ giải mã utf-8-sig, vốn đọc được cả UTF-8 có BOM và không có BOM. Trường encoding trong kết quả thống kê GD1 ghi bộ giải mã đọc thành công, không phải kết quả phát hiện BOM. Do đó, cụm “UTF-8 có BOM” trong GD1 được làm rõ thành “UTF-8, đọc bằng bộ giải mã utf-8-sig”.

Bằng chứng: kiểm tra trực tiếp byte đầu của cả 1.000 tệp cho kết quả 0 tệp có BOM; nội dung đọc được và số từ khớp GD1. Không thêm BOM vào dữ liệu.

## 3. Nguồn danh sách từ dừng

Sửa trực tiếp dòng NLTK trong danh mục từ viết tắt của bản hợp nhất thành:

> NLTK — Natural Language Toolkit — Bộ công cụ xử lý ngôn ngữ tự nhiên; trong đề tài dùng cho Porter Stemmer.

Nguồn danh sách từ dừng vẫn là ENGLISH_STOP_WORDS từ scikit-learn, kết hợp EXTRA_STOP định nghĩa trong mã GD1. Không cần giữ mô tả sai trong danh mục rồi tạo một mục đính chính riêng. Danh sách từ dừng, thứ tự lọc và thuật toán stemming được giữ đúng như lần GD1.

Mốc trước GD2 lưu riêng ba danh sách `english_stop_words`, `extra_stop`, `stop_all`, cùng cấu hình và phiên bản thư viện. Không thay sang danh sách stopword của NLTK.

## 4. Những thành phần giữ đúng GD1

- 1.000 tệp, 34.344.608 từ, nhỏ nhất 12.072 từ và lớn nhất 53.913 từ.
- Nhãn 14 nhóm; không dùng nhãn, tên tác phẩm hoặc tác giả để tính điểm.
- Tokenizer, chuẩn hóa dấu nháy, lọc từ trước Porter stemming.
- TF logarit; IDF làm trơn; `min_df=3`, `max_df=0.6`; chuẩn hóa L2.
- Truy vấn dùng vocabulary/IDF học từ kho; cosine trên từng tệp, trả Top-3.

34.416 chiều là mốc kết quả GD1 cần tái lập ở bước đầu GD2. Lần chuẩn bị này chưa fit lại TF-IDF và chưa tạo CSDL tìm kiếm.

## 5. Trạng thái chuẩn bị

Đã hoàn thành bổ sung bốn tên tập/phần, chốt phần làm rõ, lưu mốc dữ liệu/cấu hình và sắp xếp thư mục. Mốc lưu tại `baselines/pre_gd2_2026-11-04`; kiểm tra bằng `python tools/verify_baseline.py` từ thư mục dự án. Bước tiếp theo là P2 trong kế hoạch: tái lập đặc trưng theo GD1.
