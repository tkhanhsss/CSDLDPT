# Phác thảo chi tiết phần báo cáo GD2

Cập nhật 07/11/2026: P7 đã hoàn tất theo khung này. Sản phẩm hiện hành là [Word/PDF hợp nhất](../../gd2/report/README.md); xem [biên bản P7](BIEN_BAN_P7.md). Nội dung bên dưới được giữ làm khung soạn thảo.

Ngày lập: 03/11/2026. Cập nhật: 04/11/2026 sau khi hoàn tất chuẩn bị, chốt metadata và sắp xếp thư mục. Dùng cùng `KE_HOACH_GD2.md`.

Tài liệu này là khung viết và danh sách bằng chứng cần thu thập. Mọi vị trí `[ĐIỀN SAU KHI CHẠY]` phải được thay bằng dữ liệu đã kiểm chứng. Những đoạn có nhãn “đoạn dẫn dự kiến” chỉ được dùng như mô tả hệ thống đã hoàn thành sau khi phần tương ứng thực sự được xây và kiểm tra.

Kế hoạch triển khai đã chốt tại mục 0 của `KE_HOACH_GD2.md`. Các ghi chú làm rõ diễn đạt GD1 và phần đầu báo cáo được xử lý ở P7; trước mắt tập trung hoàn thành P2–P6 và thu thập số liệu thật theo khung này.

## A. Bố cục bản PDF hợp nhất

1. Bìa báo cáo hợp nhất, giữ đúng thông tin nhóm và học phần.
2. Một mục lục và các danh mục hình/bảng cho toàn bộ GD1+GD2, cập nhật số trang sau dàn trang.
3. Danh mục từ viết tắt được chỉnh sửa, bổ sung theo nội dung báo cáo mới.
4. Mở đầu viết lại cho phạm vi GD1+GD2 và bố cục bốn chương.
5. Chương 1 và Chương 2: kế thừa nội dung GD1; giữ ổn định số liệu, công thức, phương pháp và kết luận.
6. Phần chuyển tiếp ngắn: đối chiếu kế thừa và làm rõ các điểm thuộc nội dung GD1 cần giải thích thêm.
7. Chương 3. Xây dựng CSDL lưu trữ đặc trưng văn bản.
8. Chương 4. Xây dựng và đánh giá hệ thống tìm kiếm văn bản.
9. Kết luận giai đoạn 2.
10. Tài liệu tham khảo và phụ lục chọn lọc: cấu hình, schema SQL, truy vấn mẫu, trace và phiếu chấm.

Người dùng cho phép thay đổi danh mục từ viết tắt và Mở đầu. Vì vậy, không ghép nguyên 14 trang GD1 theo phương án cũ; giữ bản gốc làm hồ sơ đối chiếu và bảo toàn nội dung Chương 1–2 trong bản hợp nhất. Số trang được tính theo bố cục mới, không cố định Chương 3 bắt đầu ở trang 15.

Mở đầu mới cần nêu bài toán, phạm vi kho tiếng Anh, truy vấn ngoài kho, mục tiêu CSDL đặc trưng và tìm kiếm Top-3, cách tiếp cận kế thừa GD1, phạm vi kết quả thực hiện và giới thiệu bốn chương. Chỉ đưa số liệu kết quả GD2 sau khi chạy thật. Trong danh mục từ viết tắt, mô tả NLTK là bộ công cụ dùng cho Porter Stemmer; bổ sung SQL, CSR, OOV, P@3 hoặc các thuật ngữ khác khi thực sự sử dụng trong báo cáo.

Không cần thêm Chương 5 để demo ở lần nộp này. Khi làm GD3 có thể bổ sung hướng dẫn chạy/demo theo đúng chương trình đã dùng để tạo số liệu GD2.

Độ dài tham khảo phần mới: đối chiếu 1–2 trang; Chương 3 khoảng 5–6 trang; Chương 4 khoảng 9–12 trang; kết luận, tài liệu và phụ lục khoảng 3–5 trang. Co giãn theo chất lượng bằng chứng, không làm đủ số trang bằng cách lặp Chương 2.

## B. Phần chuyển tiếp và giải thích tính nhất quán

### B.1 Đoạn dẫn dự kiến

> Phần bổ sung giai đoạn 2 tiếp tục sử dụng bộ 1.000 tệp văn bản tiếng Anh và phương pháp biểu diễn đã trình bày ở Chương 1–2. Mỗi tệp được biểu diễn bằng một vector TF-IDF với TF điều chỉnh logarit, IDF làm trơn và chuẩn hóa L2. Truy vấn được xử lý trên từ vựng và IDF cố định của kho; các văn bản được xếp hạng theo độ tương đồng cosine. Nội dung bổ sung tập trung vào thiết kế CSDL đặc trưng, hiện thực hóa quy trình tìm kiếm và đánh giá kết quả.

### B.2 Bảng đối chiếu phải có

| Nội dung ở GD1 | Thực hiện ở GD2 | Cách chứng minh |
|---|---|---|
| Kho 1.000 TXT và số liệu độ dài | Dùng lại nguyên kho | Manifest, hash và kiểm tra số từ |
| Quy trình tiền xử lý, Bảng 4 | Module tiền xử lý dùng chung | Bảng token thật và cấu hình |
| TF-IDF, Bảng 5 | Dựng và lưu vocabulary/IDF/vector | Schema, số dòng, kiểm tra ma trận |
| Ma trận thưa 1.000×34.416 | Nạp từ CSDL để tính điểm | Kích thước tái lập và đối chiếu giá trị |
| Cosine, Top-3, mục 2.4 | Module tính điểm và trả tệp | Toàn bộ 1.000 điểm, Top-3, file xuất |
| Tên tác phẩm–tác giả | Bảng gốc selected_stories.csv, nối bằng new_filename | Đủ 1.000 ánh xạ; kiểm chứng riêng nguồn/tập/ấn bản khi cần |

### B.3 Ghi chú làm rõ đã chốt để đưa vào bản hợp nhất

Dùng các đoạn đã soạn trong [LAM_RO_GD1_TRUOC_GD2.md](LAM_RO_GD1_TRUOC_GD2.md); chưa sửa PDF GD1 đã nộp.

1. **Bảng ánh xạ đã tìm lại:** dùng `data/metadata/selected_stories.csv`, có đủ 1.000 dòng tên tệp phân biệt khớp kho, không trống title/author. Không cần trình bày sự cố thất lạc trong báo cáo. Đã xác minh `book_0637.txt`/`book_0797.txt` là Grania Tập I (Phần I–II)/Tập II (Phần III–IV); `book_0927.txt`/`book_0988.txt` là The Earl's Promise Tập 1/3 và Tập 2/3. Bổ sung mô tả: một số tệp là từng tập của cùng tác phẩm, đơn vị biểu diễn và tìm kiếm vẫn là tệp. Không tiếp tục khẳng định mọi tệp là một tác phẩm độc lập hoàn chỉnh. Xem bằng chứng nguồn trong `DOI_CHIEU_CAC_TAP_TAC_PHAM.md`.
2. **BOM:** làm rõ `utf-8-sig` là bộ giải mã; kiểm tra bộ tệp hiện tại cho thấy không có BOM. Đây là sửa mô tả kỹ thuật, không thay nội dung hay quy trình tạo đặc trưng.
3. **Stopword:** danh sách thực tế là scikit-learn ENGLISH_STOP_WORDS cộng EXTRA_STOP; NLTK dùng cho Porter Stemmer. Sửa trực tiếp mô tả NLTK trong danh mục từ viết tắt mới; không thay danh sách từ dừng khi triển khai.
4. **Bố cục:** viết lại Mở đầu để giới thiệu bốn chương; dùng mục lục và danh mục thống nhất cho bản hợp nhất. Không cần giữ câu “2 chương” rồi thêm giải thích.

Nếu xác minh được vấn đề về nguồn hoặc tính toàn vẹn tác phẩm khi đối chiếu, bổ sung sự kiện cụ thể và ảnh hưởng; không đưa nghi ngờ chưa kiểm chứng thành kết luận. Chỉ ghi Gutenberg ID khi có bằng chứng nguồn.

## C. Chương 3. Xây dựng CSDL lưu trữ đặc trưng văn bản

Chương này trả lời trực tiếp yêu cầu số 3. Không chỉ giới thiệu lý thuyết CSDL; phải cho thấy các đặc trưng của toàn bộ kho đã được lưu và có thể nạp lại.

### 3.1 Mục tiêu và yêu cầu lưu trữ

Nêu ba nhóm dữ liệu: thông tin định danh/metadata của văn bản; vocabulary và IDF; trọng số TF-IDF thưa của từng văn bản. Nêu dữ liệu nào trên đĩa, dữ liệu nào trong CSDL và dữ liệu nào trong RAM khi tìm kiếm.

Đoạn dẫn dự kiến:

> CSDL được xây dựng nhằm lưu trữ thống nhất thông tin văn bản và các tham số cần thiết để tái tạo không gian đặc trưng của kho. Thay vì lưu mọi phần tử của một ma trận đặc, hệ thống lưu các cặp văn bản–term có trọng số khác 0. Các tệp TXT gốc được giữ trên đĩa và liên kết với bản ghi văn bản bằng tên tệp, đường dẫn tương đối và mã băm. Khi tìm kiếm, chương trình nạp các trọng số từ CSDL để tạo ma trận thưa theo đúng thứ tự văn bản và term.

**Bằng chứng cần có:** sơ đồ các thành phần lưu trữ; bảng kê dữ liệu; giải thích vì sao không chỉ lưu 5 từ nổi bật của GD1.

### 3.2 Lựa chọn hệ quản trị và mô hình dữ liệu

Đề xuất SQLite cho hệ thống cục bộ. Viết ngắn về sự phù hợp với phạm vi bài tập và cách mang theo một CSDL cùng dữ liệu; không tuyên bố SQLite nhanh hơn mọi hệ quản trị nếu chưa đo.

**Hình 5:** sơ đồ quan hệ `labels → documents → document_terms ← terms`; `build_info` là bảng thông tin bản dựng độc lập.

**Bảng 6:** danh sách bảng và vai trò.

| Bảng | Dữ liệu lưu | Quy mô sau chạy |
|---|---|---|
| build_info | Cấu hình, phiên bản, hash và số liệu bản dựng | 1 bản dựng |
| labels | 14 nhãn nội dung giữ từ GD1 | 14 dòng |
| documents | Mã, đường dẫn, hash, độ dài, metadata, nhãn, chuẩn trước L2 | 1.000 dòng |
| terms | Stem, df và IDF | `[ĐIỀN SAU KHI CHẠY; đối chiếu 34.416]` |
| document_terms | Count và trọng số chuẩn hóa cho cặp doc–term khác 0 | `[ĐIỀN SAU KHI CHẠY: nnz]` |

Nêu rõ chỉ một bản dựng trong CSDL hiện tại; thay cấu hình/kho tạo bản dựng mới. Metadata bổ sung để hiển thị không được đưa vào text dùng xây vector.

### 3.3 Thiết kế bảng, khóa và ràng buộc

**Bảng 7:** từ điển dữ liệu. Với mỗi trường nêu kiểu, ý nghĩa, NULL/NOT NULL, khóa và ràng buộc quan trọng. Dùng cấu trúc chi tiết ở mục 5 của kế hoạch.

Trình bày kỹ ba điểm:

1. Khóa `(doc_id, term_id)` biểu diễn đúng một giá trị của ma trận; không có bản ghi cho trọng số 0.
2. `term_count` khác với `weight`: count là số lần xuất hiện stem, weight đã áp dụng TF, IDF và L2.
3. `term_id`/`doc_id` có ánh xạ tường minh tới cột/hàng X; giá trị ID không được đoán từ thứ tự đọc tự nhiên của SQL.

Phần schema SQL đầy đủ đưa phụ lục. Trong thân chương chỉ trình bày ví dụ ngắn và khóa chính/khóa ngoại dễ đọc; không chụp một màn hình code nhỏ tới mức không đọc được.

### 3.4 Quy trình tạo và nạp đặc trưng

**Hình 6:** `đọc kho → tiền xử lý GD1 → đếm term/df → lọc vocabulary → tính TF-IDF/L2 → nạp transaction → kiểm tra → bản dựng sẵn sàng`.

Liệt kê I/O của quy trình: đầu vào 1.000 TXT, labels, metadata, cấu hình; đầu ra CSDL và biên bản xây dựng. Dẫn lại công thức Chương 2 thay vì viết lại cả phần lý thuyết.

Nhấn mạnh:

- Fit chỉ trên 1.000 văn bản của kho, không có truy vấn.
- Vocabulary được lọc theo df trên toàn kho, không phải tổng số lần xuất hiện của term.
- Với N=1.000, term có df từ 3 đến 600 được giữ, kể cả df=600.
- Ma trận sau L2 được lưu đủ các phần tử khác 0, không cắt chỉ top-k term của từng tài liệu.
- Chỉ làm tròn số khi trình bày; CSDL giữ độ chính xác phục vụ tính điểm.

**Bảng 8:** kết quả xây CSDL.

| Chỉ tiêu | Giá trị cần điền | Nguồn |
|---|---|---|
| Số văn bản đã nạp | `[ĐO THỰC; kỳ vọng 1.000]` | COUNT(documents) |
| Số term | `[ĐO THỰC; đối chiếu 34.416]` | COUNT(terms) |
| Số trọng số khác 0 | `[ĐIỀN SAU KHI CHẠY]` | COUNT(document_terms) |
| Kích thước X | `[ĐIỀN SAU KHI CHẠY]` | Dữ liệu đọc lại |
| Mật độ | `nnz / (N×V)` với số liệu thật | Tính từ ba số đã đo |
| Dung lượng CSDL | `[ĐIỀN SAU KHI CHẠY]` | Kích thước file |
| Thời gian dựng/nạp | `[ĐIỀN SAU KHI CHẠY]` | Log đo trên máy thử |

### 3.5 Minh họa dữ liệu thực và thao tác truy vấn

Chọn một tệp sau khi đã xác minh metadata; có thể trùng với một kết quả của Q01 để mạch trình bày liên tục.

**Bảng 9:** một bản ghi documents và 5–10 term thực của tệp đó, nối sang df/IDF. Giải thích cách tính lại một `weight` từ count, IDF và `l2_raw`.

Các câu hỏi SQL cần minh họa bằng kết quả thật:

- Kho chứa bao nhiêu văn bản/term/trọng số?
- Một tệp có những term nào và trọng số ra sao?
- Một term xuất hiện ở bao nhiêu văn bản; có khớp df đã lưu không?
- Có bản ghi mất liên kết hoặc mã trùng không?

Không cần đưa mọi truy vấn kiểm tra vào thân chương; giữ 2–3 ví dụ tiêu biểu, còn lại phụ lục/log.

### 3.6 Kiểm chứng CSDL và khả năng nạp lại

**Bảng 10:** tiêu chí, kết quả, kết luận.

| Kiểm tra | Điều kiện | Kết quả |
|---|---|---|
| Đủ dữ liệu | 1.000 documents; đủ vocabulary theo lần dựng | `[ĐIỀN]` |
| Toàn vẹn | Không FK lỗi, filename/term duy nhất | `[ĐIỀN]` |
| df/IDF | Khớp đếm tài liệu và công thức GD1 | `[ĐIỀN]` |
| Chuẩn L2 | Hàng khác 0 có norm xấp xỉ 1 | `[ĐIỀN]` |
| Nạp lại | X từ DB khớp X tham chiếu trong sai số cho phép | `[ĐIỀN]` |
| Liên kết tệp | Hash/path khớp các TXT dùng xây dựng | `[ĐIỀN]` |

Kết thúc bằng dẫn sang Chương 4: đặc trưng và ánh xạ đã nạp lại sẽ được dùng trực tiếp để tìm kiếm, không fit lại mỗi lần nhận truy vấn.

## D. Chương 4. Xây dựng và đánh giá hệ thống tìm kiếm văn bản

### 4.1 Phát biểu bài toán và điều kiện đầu vào

Nêu input một TXT tiếng Anh khoảng 1.000 từ, trích từ tác phẩm ngoài kho; output ba TXT trong kho theo cosine giảm dần, kèm filename/metadata/score. Một tệp kho vẫn là một đơn vị xếp hạng.

Đoạn dẫn dự kiến:

> Hệ thống nhận một đoạn văn bản mới làm truy vấn và tìm các tệp trong kho có mức trùng khớp từ vựng có trọng số cao nhất. Mục tiêu không phải nhận diện tệp gốc của đoạn trích, bởi tác phẩm nguồn của truy vấn không nằm trong kho. Nhãn nội dung và metadata được sử dụng khi mô tả kết quả, không tham gia tính điểm.

Nêu riêng trạng thái truy vấn không tạo được vector và quy tắc phá hòa. Khoảng 950–1.050 từ là quy ước chọn bộ thử của nhóm, không phải ngưỡng cứng của đề bài.

### 4.2 Sơ đồ khối và quy trình tổng thể — đáp ứng 4a

**Hình 7:** dùng sơ đồ hai luồng của kế hoạch: dựng CSDL offline và xử lý truy vấn online. Có mũi tên từ CSDL tới vocabulary/IDF và X; có nhánh kiểm tra vector rỗng.

Mô tả các bước liên tiếp:

1. Nạp bản dựng CSDL hợp lệ, X và ánh xạ tài liệu/term.
2. Đọc file truy vấn, ghi nhận số từ và thông tin nguồn.
3. Tiền xử lý bằng cùng hàm của kho.
4. Đếm term thuộc vocabulary cố định, dùng IDF từ kho, chuẩn hóa L2.
5. Nếu vector khác 0, tính Xqᵀ để thu 1.000 điểm.
6. Sắp xếp giảm dần, phá hòa theo filename, chọn ba tệp.
7. Trả tệp và bảng kết quả; xuất các bảng trung gian để giải thích.

Phân biệt rõ CSDL là nơi lưu bền vững; RAM chứa ma trận tạm phục vụ phép tính. Từ “online” ở đây là lúc xử lý truy vấn, không có nghĩa phải có Internet hay website.

### 4.3 Thiết kế module và dữ liệu vào/ra — đáp ứng phần đầu 4b

**Bảng 11:** I/O M1–M10 theo kế hoạch; nếu cần tiết kiệm trang, phần dựng kho dẫn sang Chương 3 và chỉ mô tả kỹ M5–M10 ở đây.

Với mỗi module, dùng cùng cấu trúc: mục đích → đầu vào → xử lý → đầu ra → tình huống lỗi. Có kích thước dữ liệu tại các điểm quan trọng: `X: N×V`, `q: 1×V`, `scores: N phần tử`.

Đoạn giải thích thuật toán truy vấn:

> Với mỗi term thuộc từ vựng đã lưu, hệ thống đếm số lần xuất hiện trong truy vấn và tính TF logarit. IDF không được ước lượng lại mà được lấy từ CSDL của kho. Sau chuẩn hóa L2, vector truy vấn có cùng số chiều và cùng thứ tự term với các vector tài liệu. Phép nhân ma trận thưa Xqᵀ cho điểm cosine giữa truy vấn và toàn bộ 1.000 văn bản.

Nếu trình bày giả mã, chỉ cần quy trình ngắn dưới đây; khi hoàn thiện phải khớp mã chạy:

```text
load database -> vocabulary, idf, X, doc_mapping
read query -> normalized content tokens
count tokens in fixed vocabulary
apply log-TF and stored IDF -> normalize L2 -> q
if q has no nonzero feature: return empty_vector
scores = X * transpose(q)
sort by (-full_precision_score, filename)
return first 3 source files, metadata, scores and trace
```

### 4.4 Chuẩn bị dữ liệu truy vấn ngoài kho

**Bảng 12:** nguồn của 12 truy vấn.

| Mã | Tác phẩm/tác giả | Nguồn và vị trí trích | Số từ | Bằng chứng ngoài kho |
|---|---|---|---:|---|
| Q01 | `[CHƯA CHỌN]` | `[URL + chương/điểm bắt đầu–kết thúc]` | `[ĐO]` | `[KIỂM CHỨNG]` |
| Q02–Q12 | `[LẬP TỪ NGUỒN THẬT]` | `[ĐIỀN]` | `[ĐO]` | `[KIỂM CHỨNG]` |

Không ghi tên một tác phẩm cụ thể vào bản chính chỉ vì nổi tiếng hoặc dễ lấy. Trước hết phải xác minh nguồn đó chưa có trong 1.000 tệp, kể cả dưới tên khác hoặc trong tuyển tập.

Giải thích cách chọn nội dung, quy tắc trích liên tục và giới hạn phạm vi bộ thử. Tách các ca rỗng/ngoài từ vựng khỏi tập truy vấn hợp lệ dùng đo P@3. Nếu có truy vấn tự cắt từ kho để kiểm thử kỹ thuật, đánh dấu rõ “kiểm thử nội bộ, không tính thực nghiệm chính”.

### 4.5 Minh họa đầy đủ một lần tìm kiếm — phần trọng tâm 4b

Nên dành 4–6 trang cho mục này, ưu tiên bảng đọc được hơn ảnh chụp terminal dày chữ. Toàn bộ số liệu phải dùng cùng Q01, cùng build và cùng một lần chạy có log.

#### 4.5.1 Văn bản đầu vào

Nêu tên file, số từ, nguồn, vị trí trích và 1–2 đoạn ngắn làm rõ chủ đề. Toàn bộ file khoảng 1.000 từ có thể để phụ lục hoặc bộ dữ liệu đi kèm; không cần chèn hai trang truy vấn vào thân chương nếu khiến mất cân đối.

**Hình 8:** ảnh đầu vào/đầu ra thực của chương trình dòng lệnh, có filename và build; ảnh này hỗ trợ bằng chứng, không thay thế các bảng trung gian.

#### 4.5.2 Tiền xử lý

**Bảng 13:** mẫu biến đổi token từ Q01.

| Token nguyên văn | Sau chuẩn hóa/base | Giữ/bỏ | Lý do | Stem cuối |
|---|---|---|---|---|
| `[token thật]` | `[giá trị thật]` | `[giữ/bỏ]` | `[stopword/một ký tự/cấu trúc/giữ]` | `[stem thật hoặc –]` |

**Bảng 14:** số token qua các bước. Phân biệt “lượt token” và “số stem phân biệt”; không trộn hai đơn vị vào một cột.

| Chỉ số | Đơn vị | Kết quả |
|---|---|---:|
| Số từ theo regex trước lọc | Lượt token | `[ĐO]` |
| Số token sau lọc và stemming | Lượt token | `[ĐO]` |
| Số stem phân biệt sau xử lý | Loại stem | `[ĐO]` |
| Số stem phân biệt thuộc vocabulary | Loại stem = nnz(q) | `[ĐO]` |
| Số stem phân biệt ngoài vocabulary | Loại stem | `[ĐO]` |

Nếu báo tỷ lệ OOV, ghi rõ mẫu số là số loại stem sau xử lý hay lượt stem; không thay đổi mẫu số giữa các bảng.

#### 4.5.3 Vector truy vấn

**Bảng 15:** 10–15 term có trọng số cao trong Q01.

| Term | f trong q | TF log | df ở kho | IDF ở kho | TF×IDF | Trọng số sau L2 |
|---|---:|---:|---:|---:|---:|---:|
| `[term thật]` | `[ĐO]` | `[TÍNH]` | `[DB]` | `[DB]` | `[TÍNH]` | `[TÍNH]` |

Lấy một term thật để thay số vào công thức Chương 2. Ghi `||q_raw||2`, kích thước q và nnz(q); phần mẫu số L2 tính trên toàn bộ term có mặt trong vocabulary, không chỉ những dòng được trưng bày.

#### 4.5.4 Điểm tương đồng và Top-3

**Bảng 16:** Top-10 score, làm nổi ba dòng đầu. Nêu toàn bộ 1.000 điểm được xuất ra CSV và cùng tham gia xếp hạng.

**Bảng 17:** kết quả đầu ra chính.

| Hạng | Tệp văn bản | Tác phẩm/tác giả đã xác minh | Nhãn mô tả | Cosine |
|---:|---|---|---|---:|
| 1 | `[KẾT QUẢ CHẠY]` | `[METADATA]` | `[NHÃN GD1]` | `[ĐO]` |
| 2 | `[KẾT QUẢ CHẠY]` | `[METADATA]` | `[NHÃN GD1]` | `[ĐO]` |
| 3 | `[KẾT QUẢ CHẠY]` | `[METADATA]` | `[NHÃN GD1]` | `[ĐO]` |

Xác nhận `score1 ≥ score2 ≥ score3`, kiểm tra cả hạng 4; xếp hạng dùng số đầy đủ, số hiển thị có thể làm tròn. Chỉ nêu điểm cosine, không đổi thành “độ chính xác x%”.

#### 4.5.5 Giải thích sự tương đồng

**Bảng 18:** đóng góp term cho từng kết quả; có thể dùng ba bảng nhỏ 18a–18c với nhãn rõ ràng.

| Term chung | Trọng số q | Trọng số tài liệu | Tích hai trọng số |
|---|---:|---:|---:|
| `[term thực]` | `[ĐO]` | `[DB]` | `[TÍNH]` |
| Tổng các term trình bày | | | `[TÍNH]` |
| Tổng đóng góp các term còn lại | | | `[TÍNH]` |
| Tổng toàn bộ | | | `[KHỚP COSINE]` |

**Hình 9, tùy chọn:** biểu đồ thanh đóng góp của 8–10 term cho kết quả hạng 1. Tên trục và chú thích phải ghi đây là đóng góp vào cosine, không phải TF đơn thuần.

Sau bảng, viết 1 đoạn cho từng kết quả: những term chung thể hiện chủ đề gì; đoạn nội dung thực tế có liên quan ra sao; có dấu hiệu tên riêng làm tăng điểm không. Không chỉ lặp câu “điểm cao nên giống”.

#### 4.5.6 Trường hợp khó và truy vấn không có đặc trưng

Đưa một ca hợp lệ có kết quả chưa tốt để minh họa giới hạn. Tách một ca thử lỗi như tệp rỗng hoặc nội dung không có term trong vocabulary; trình bày thông báo chương trình thực sự trả về. Không gộp ca lỗi vào mẫu số 12 truy vấn chất lượng nếu bộ đánh giá đã xác định chỉ gồm ca hợp lệ.

### 4.6 Đánh giá kết quả — đáp ứng 4c

#### 4.6.1 Thiết lập đánh giá

Nêu số truy vấn, số tác phẩm nguồn, cách chọn, quy tắc ngoài kho, cấu hình máy, phiên bản thư viện, bản dựng và người chấm. Chốt rubric 0/1/2 và ngưỡng liên quan mức 2 như kế hoạch.

**Bảng 19:** độ liên quan các cặp truy vấn–kết quả: mã q, filename, điểm của từng người, điểm thống nhất, bằng chứng/lý do. Thân chương đưa mẫu, phụ lục hoặc file lưu đầy đủ 36 cặp.

Không dùng cùng nhãn làm đáp án tự động. Nhãn của GD1 vốn để mô tả, có thể rộng và mất cân bằng; phải đọc nội dung để chấm.

#### 4.6.2 Chất lượng Top-3

Trình bày công thức P@3 và Mean P@3, định nghĩa tử số bằng các kết quả mức 2. Nêu người chấm không dùng cosine làm tiêu chí quyết định.

**Bảng 20:** tổng hợp theo truy vấn.

| Truy vấn | Mức liên quan hạng 1/2/3 | Số mức 2 | P@3 | Nhận xét |
|---|---|---:|---:|---|
| Q01 | `[CHẤM]` | `[TÍNH]` | `[TÍNH]` | `[BẰNG CHỨNG]` |
| ... | ... | ... | ... | ... |
| Trung bình | | | `[TÍNH TỪ TOÀN BỘ BỘ THỬ]` | |

Có thể thêm tỷ lệ truy vấn có ít nhất một kết quả mức 2, tỷ lệ đồng thuận người chấm và phân bố mức 0/1/2. Không đưa Recall/MAP/nDCG chuẩn nếu không có bộ phán xét đủ cho các mẫu số/thứ hạng lý tưởng tương ứng.

**Hình 10, tùy chọn:** P@3 theo truy vấn; với 12 điểm, bảng có thể đã đủ và không cần hình lặp lại.

#### 4.6.3 Đúng kỹ thuật và hiệu năng

**Bảng 21:** kiểm thử các trường hợp bình thường, hòa điểm, vector rỗng, tệp không đọc được, mở đúng tệp Top-3, tính điểm từ DB khớp bản tham chiếu.

**Bảng 22:** thời gian và tài nguyên.

| Công đoạn | Cách đo | Kết quả |
|---|---|---|
| Dựng đặc trưng và nạp DB | Chạy xây kho; nêu gồm những bước nào | `[ĐO]` |
| Khởi động/nạp DB vào RAM | Chương trình mới | `[ĐO]` |
| Tiền xử lý và vector hóa q | Chỉ xử lý truy vấn | `[ĐO]` |
| Tính 1.000 điểm và lấy Top-3 | Không tính thời gian đọc của con người | `[ĐO]` |
| Tổng truy vấn khi X đã nạp | Một lần làm nóng, 5 lần đo/q, trung vị | `[ĐO]` |

Không viết “tìm kiếm thời gian thực” chỉ dựa vào cảm giác. Gắn nhận xét tốc độ với số đo và máy thử cụ thể.

### 4.7 Nhận xét, giới hạn và hướng hoàn thiện

Liên hệ kết quả đo với phương pháp đã chọn:

- TF-IDF/cosine có thể hiệu quả khi hai đoạn/tài liệu dùng các từ chủ đề giống nhau; chỉ kết luận mức độ trên bộ thử thực tế.
- Tên nhân vật, địa danh hoặc thuật ngữ hiếm có thể có đóng góp lớn; chứng minh bằng bảng term thay vì phỏng đoán.
- Tìm kiếm từ vựng chưa xử lý tốt từ đồng nghĩa hoặc diễn đạt khác; vector cả tệp có thể làm loãng một chủ đề cục bộ.
- Nhãn mất cân bằng và bộ thử nhỏ ảnh hưởng phạm vi kết luận.
- Metadata còn giới hạn nào về nguồn, tập/ấn bản hay tính đầy đủ thì nêu cụ thể, đặc biệt ảnh hưởng đến xác minh truy vấn ngoài kho và hiển thị.

Hướng GD3 trước mắt: hoàn thiện thao tác chọn file, hiển thị và mở ba tệp, hiển thị trace để demo. Các phương pháp khác chỉ nêu là hướng nghiên cứu sau; nếu chưa có thử nghiệm thì không viết thành kết quả so sánh hoặc thay thuật toán chính.

## E. Kết luận giai đoạn 2

Viết khoảng nửa trang đến một trang sau khi có kết quả, theo trật tự:

1. CSDL đã lưu được gì, quy mô đo thực.
2. Hệ thống đã nhận truy vấn và trả ba tệp theo đúng cơ chế nào.
3. Chất lượng/hiệu năng đo trên bộ thử nào, giá trị bao nhiêu.
4. Hạn chế quan trọng nhất và phần chuẩn bị cho demo GD3.

Khung câu, chưa phải kết quả:

> Trên bộ 1.000 văn bản kế thừa từ GD1, nhóm đã xây dựng CSDL lưu trữ [số term] term và [nnz] trọng số TF-IDF khác 0. Hệ thống xử lý tệp truy vấn bằng cùng quy trình tiền xử lý, sử dụng từ vựng/IDF đã cố định và xếp hạng toàn kho theo cosine. Với [số truy vấn] truy vấn từ [số tác phẩm] ngoài kho, kết quả đánh giá đạt [chỉ số và giá trị], trong điều kiện [phạm vi thử nghiệm]. Các trường hợp [dẫn chứng] cho thấy hạn chế [cụ thể]. Phần hiện thực này là cơ sở cho demo ở giai đoạn 3.

Không điền “hoàn thành đầy đủ”, “độ chính xác cao”, “tối ưu” nếu bằng chứng chưa đủ.

## F. Tài liệu tham khảo và phụ lục

Tài liệu tham khảo cần có nguồn thực đã dùng: trang tác phẩm truy vấn và nguồn đối chiếu metadata; tài liệu TfidfVectorizer/TfidfTransformer phù hợp phiên bản; tài liệu SQLite cho schema/FK; tài liệu Porter nếu giải thích sâu thêm. URL và ngày truy cập phải là lần kiểm tra thật, không tự đặt ngày.

Phụ lục đề xuất:

- **A. Cấu hình tái lập:** versions, regex, nguồn stopword, EXTRA_STOP, tham số TF-IDF, thứ tự tài liệu, hash bản dựng.
- **B. Schema và truy vấn kiểm tra:** SQL ngắn có chú thích, kết quả đo chính.
- **C. Nguồn truy vấn:** bảng manifest và vị trí trích; tình trạng kiểm chứng ngoài kho.
- **D. Trace Q01:** bảng trọng số mở rộng và điểm cần thiết; lưu toàn bộ 1.000 điểm ở tệp riêng để kiểm tra, không cần in dài.
- **E. Phiếu chấm:** rubric, hai lượt chấm độc lập và kết quả thống nhất.
- **F. Nhật ký metadata:** dùng bảng gốc 1.000 dòng, kèm đối chiếu hai nhóm trùng tên–tác giả và nguồn/ấn bản đã xác minh; bảng đầy đủ có thể lưu ngoài PDF, phần PDF tóm tắt và mẫu bằng chứng.

Vì giảng viên chỉ nhận PDF ở GD2, các bằng chứng quyết định phải có trong PDF: schema, số dòng, một ca trace đầy đủ, Top-3 và đánh giá. Các tệp ngoài PDF giúp tái lập, nhưng không được dùng câu “xem file ngoài” để bỏ những mục 3/4a/4b/4c bắt buộc khỏi báo cáo.

## G. Ma trận kiểm tra bao phủ đề bài

| Yêu cầu | Vị trí dự kiến | Bằng chứng không được thiếu |
|---|---|---|
| 1. Bộ dữ liệu và mô tả | GD1 Chương 1 + phần làm rõ | Giữ số liệu/kho, metadata có trạng thái |
| 2. Nguyên lý đặc trưng/tìm kiếm | GD1 Chương 2 | Giữ đúng pipeline, TF/IDF/L2/cosine |
| 3. Xây CSDL lưu đặc trưng toàn kho | Chương 3.1–3.6 | ERD, schema, đặc trưng thực, số dòng, nạp lại |
| 4. Đầu vào ngoài kho, đầu ra Top-3 | 4.1, 4.4, 4.5 | Nguồn truy vấn, số từ, ba tệp thật |
| 4a. Sơ đồ và quy trình | 4.2 | Hai luồng, CSDL, nhánh vector rỗng |
| 4b. Module và I/O | 4.3 | Bảng I/O, kích thước, trạng thái |
| 4b. Kết quả trung gian cụ thể | 4.5 | Token → trọng số → 1.000 điểm → Top-3 → đóng góp term |
| 4c. Đánh giá | 4.6–4.7 | Rubric, người chấm, P@3, hiệu năng, ca hạn chế |
| 5. Demo | GD3 | Tái dùng DB/search; không phải phần kết quả cần tuyên bố đã làm trong GD2 |

## H. Thứ tự viết để tránh viết lại

1. Chốt bảng đối chiếu và các vấn đề nguồn/metadata.
2. Viết thiết kế Chương 3.1–3.3 và 4.1–4.3 theo kế hoạch.
3. Chạy dựng đặc trưng/CSDL, điền 3.4–3.6.
4. Chốt nguồn truy vấn, điền 4.4.
5. Chạy Q01, xuất bảng và điền 4.5; không chép điểm thủ công từ nhiều lần chạy khác nhau.
6. Chạy/chấm toàn bộ bộ thử, viết 4.6–4.7 và kết luận.
7. Hoàn thiện Mở đầu và danh mục từ viết tắt mới; cập nhật mục lục hợp nhất, danh mục hình/bảng, phụ lục và số trang.
8. Render và đọc lại PDF hợp nhất, đối chiếu mỗi con số với log/CSV gốc.

Điểm quyết định trước khi bắt đầu là khóa được phạm vi: giữ đúng GD1, sử dụng metadata và phần làm rõ đã chốt, thực hiện một hệ thống tối thiểu chạy thật và dành đủ công sức cho bằng chứng trung gian cùng đánh giá.
