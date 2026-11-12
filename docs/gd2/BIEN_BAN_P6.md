# Biên bản P6 — thực nghiệm trên bộ truy vấn đã khóa

Ngày thực hiện: 06/11/2026, múi giờ Asia/Bangkok. **P6 đã hoàn tất: chạy thực nghiệm, kiểm chứng kỹ thuật, trace, đo hiệu năng, nhận hai phiếu chấm và thống nhất đủ 36 mức cuối.** Mean P@3 = **11,11%** theo quy tắc chỉ mức 2 là liên quan. Đây là kết quả đo trên bộ 12 truy vấn đã khóa, không phải độ chính xác chung của hệ thống.

## 1. Đầu vào và lần chạy

- Giữ đúng Q01–Q12 đã khóa ở P5; 12 tác phẩm, sáu nhóm, mỗi đoạn 965–1.025 từ. Không đổi truy vấn sau khi xem điểm.
- CSDL: `gd2/database/documents.sqlite`, schema v4, build `gd2-p3-0274798c40134e5e91eb3452500cda71`.
- SHA256 CSDL: `46d8295c0a909a886a8880c4b2898a4f08d939a61d2fe21f1002b6cef9b922ea`.
- Đã kiểm tra khóa P5 và kiểm tra sâu CSDL trước thực nghiệm. Kho, đặc trưng, metadata và nhãn GD1 giữ nguyên.
- Lần chính thức: `gd2/results/p6_official`, nhật ký ghi thời điểm 06/11/2026 lúc 01:12:43 +07:00 sau khi xử lý lô. Nạp CSDL một lần, xử lý đủ 12 truy vấn, bật trace cho cả 12.
- 12/12 trạng thái `ok`; đủ 36 bản sao TXT. Nhật ký lần chạy ghi 4,999 giây tổng, trong đó 4,246 giây nạp chỉ mục. Đây là số đo một lần có xuất trace và tệp, không thay cho benchmark lặp lại bên dưới.

Các giá trị `retrieval_run=false` trong khóa/biên bản P5 mô tả thời điểm chốt P5, không bị sửa hồi tố. Kết quả P6 ghi ở thư mục riêng.

## 2. Đúng kỹ thuật

`gd2/src/evaluate.py` kiểm tra lại vector bằng công thức độc lập: đếm stem, dựng vector đặc với TF log và IDF cố định từ SQLite, chuẩn hóa L2, nhân với X. Không fit trên truy vấn. Đối chiếu tất cả 12.000 điểm, thứ tự filename khi hòa, ánh xạ và metadata Top-3; kiểm tra hash cả nguồn lẫn bản sao; kiểm tra tổng đóng góp term của 36 cặp.

| Kiểm tra | Kết quả |
|---|---:|
| Điểm đã đối chiếu | 12.000/12.000 |
| Sai lệch điểm lớn nhất | 5,551115123125783 × 10⁻¹⁷ |
| Sai lệch tổng đóng góp lớn nhất | 5,551115123125783 × 10⁻¹⁷ |
| Ngưỡng chấp nhận | 10⁻¹⁰ |
| Bản sao khớp SHA256 | 36/36 |
| Kiểm thử Python P2–P6 | 27/27 đạt |
| Phiếu A/B: xuất và nạp CSV | Đạt với tiếng Việt, dấu phẩy, dấu nháy, xuống dòng và điểm còn trống |

Bằng chứng: [technical_verification.json](../../gd2/evaluation/p6/technical_verification.json), [evaluation_manifest.json](../../gd2/evaluation/p6/evaluation_manifest.json). Manifest giữ hash mã đánh giá, khóa P5, toàn bộ lần chạy và các phiếu/nội dung cố định. Các CSV người chấm được phép điền; mỗi lần tổng hợp lưu bản sao và hash riêng, không ghi đè lần tổng hợp cũ.

## 3. Q01 xuyên suốt

Nguồn và vị trí đã có trong P5: *A Study in Scarlet*, Arthur Conan Doyle, Part I, Chapter III. Đoạn mô tả Holmes cùng cảnh sát khảo sát hiện trường và thi thể trong căn nhà ở Lauriston Gardens.

| Bước | Số liệu |
|---|---:|
| Token nguyên văn theo regex GD1 | 991 |
| Token sau lọc và stemming | 426 |
| Stem phân biệt | 345 |
| Stem phân biệt thuộc vocabulary / nnz(q) | 149 |
| Stem phân biệt ngoài vocabulary | 196 |
| Số lần xuất hiện của stem ngoài vocabulary | 265 |
| Chuẩn L2 trước chuẩn hóa | 38,400771824172914 |

OOV ở đây nghĩa là ngoài vocabulary cuối cùng; có thể do ngưỡng df hoặc không xuất hiện trong kho, không đồng nghĩa tất cả đều là từ chưa từng có trong corpus.

Ví dụ token thật: `Gardens → gardens → garden`, `omened → omened → omen`, `minatory → minatory → minatori`; `an`, `and` bị loại vì stopword. Bảng 15 token đầu, 15 term trọng số cao, Top-10 và đóng góp Top-10 + phần còn lại được trích tại [thư mục Q01](../../gd2/evaluation/p6/Q01). Trace đầy đủ, 1.000 điểm và ba TXT nằm ở [lần chạy Q01](../../gd2/results/p6_official/Q01).

| Hạng | Tệp | Tên sách | Cosine |
|---|---|---|---:|
| 1 | book_0733.txt | THE CLUB OF QUEER TRADES | 0,086442 |
| 2 | book_0659.txt | “To let” | 0,086162 |
| 3 | book_0638.txt | The Thirty-Nine Steps | 0,080474 |
| 4 | book_0164.txt | A DOUBLE BARRELLED DETECTIVE STORY | 0,078451 |

Khoảng cách hạng 3–4 là 0,00202307657959777. Điểm lưu đầy đủ độ chính xác trong JSON/CSV; số hiển thị làm tròn sáu chữ số. Cosine không phải phần trăm nội dung giống nhau hoặc xác suất đúng.

Với mỗi kết quả, `contributions_top10_remainder.csv` có mười term đóng góp lớn nhất, dòng `REMAINDER` và `TOTAL`; tổng cuối khớp cosine. Nội dung trích dẫn có filename, dòng, offset và hash trong [case_analysis.json](../../gd2/evaluation/p6/case_analysis.json); bản dễ đọc ở [case_excerpts.md](../../gd2/evaluation/p6/case_excerpts.md). Đây là phân tích kỹ thuật do Codex, không thay cho hai phiếu chấm.

## 4. Ca hạn chế từ kết quả thật

**Tên riêng trong Q01 → book_0659.txt:** `gregson` xuất hiện ba lần trong Q01, có df=3 và IDF=6,52246041819533. Trọng số truy vấn là 0,35645417880271674; trọng số tài liệu là 0,09774240775365489. Tích bằng 0,03484068969002935, chiếm **40,4363%** cosine 0,08616183541680224 của cặp này.

Q01 nhắc Gregson trong vai thám tử tại hiện trường (dòng 43–45); `book_0659.txt` dòng 3273–3285 giới thiệu **Daniel Gregson**, một political agent đi dự Delhi durbar. Đây là hai nhân vật khác nhau cùng tên. TF-IDF unigram cộng điểm cho stem chung mà không phân biệt thực thể. Tỷ lệ trên là tỷ trọng đóng góp vào điểm, không phải tỷ lệ sai hoặc kết luận tài liệu hoàn toàn không liên quan. Điểm thống nhất của cặp này là mức 0; hai thành viên đều chấm 0 ngay từ đầu. Các bằng chứng và lý do của họ được lưu trong hai phiếu gốc.

**Q12 thăm dò:** đoạn Darwin bàn về biến dị, chọn lọc tự nhiên và đấu tranh sinh tồn. Top-3 là `book_0977.txt` (*The Coming Race*, 0,097409), `book_0938.txt` (*The Dawn of Reason*, 0,094440), `book_0389.txt` (*That Very Mab*, 0,079664; cách viết metadata gốc giữ nguyên). Trong kết quả đầu, các stem `speci`, `parasit`, `organis`, `genera`, `variat` đóng góp nhiều; dòng 1055–1076 thực sự nói tới nghiên cứu và côn trùng ký sinh trong bối cảnh thế giới giả tưởng. Có liên hệ từ vựng sinh học thật, nhưng mô hình không tự phân biệt mục đích lập luận khoa học với mô tả hư cấu. Điểm cuối của Q12 theo thứ tự hạng là 1, 2, 1: P@3 = 1/3. Hai thành viên đánh giá kết quả đầu chỉ liên quan một phần, kết quả thứ hai sát chủ đề đấu tranh sinh tồn; giữ nguyên lý do và trích dẫn trong phiếu. Q12 vì vậy có một kết quả liên quan rõ, không được mô tả là thất bại hoàn toàn.

Các hạn chế tổng quát cần giữ khi viết P7: một vector cho cả tệp có thể làm loãng đoạn phù hợp; không mô hình hóa trực tiếp đồng nghĩa hay vai trò ngữ cảnh; df loại một phần từ; bộ 12 truy vấn có chủ đích không đại diện toàn bộ tiếng Anh hay cả 14 nhãn. Không thay thuật toán để làm đẹp lần chạy này.

## 5. Hiệu năng và dung lượng

Bản đo dùng cho báo cáo: [performance_final/performance.json](../../gd2/evaluation/p6/performance_final/performance.json), đo riêng không chạy kiểm thử song song. Thư mục `performance` là lượt đầu trong phiên có kiểm thử chạy đồng thời, chỉ giữ để truy nguyên, không dùng số đó trong báo cáo.

Máy: Intel Core i5-12400F, 6 nhân/12 luồng, RAM hệ thống báo 17.013.252.096 byte (khoảng 15,84 GiB). `Win32_OperatingSystem` xác nhận Windows 11 Pro, phiên bản 10.0.26200; chuỗi platform của Python ghi `Windows-10-10.0.26200-SP0`. Python 3.10.11; SQLite 3.40.1; NumPy 2.2.6, SciPy 1.15.3, scikit-learn 1.7.2, NLTK 3.10.3.

Phương pháp: nạp SQLite năm lần; với mỗi truy vấn làm nóng một lần rồi đo năm lần, luân phiên thứ tự truy vấn giữa các vòng. Giữ nguyên IDF, X và Top-3; 60 lượt đo cho cùng vector/điểm/thứ tự. Ghi riêng đọc TXT, transform, nhân Xqᵀ, xếp hạng và tổng.

| Phép đo | Giá trị |
|---|---:|
| Trung vị nạp SQLite, năm lần | 4,110522 giây |
| Trung vị thời gian truy vấn, 60 lượt | 6,943200 ms |
| Nhỏ nhất / lớn nhất của 60 lượt | 5,994300 / 8,073300 ms |
| Trung vị riêng Q01, năm lượt | 7,332000 ms |
| SQLite | 67.866.624 byte ≈ 64,723 MiB |
| Toàn bộ corpus TXT | 192.171.854 byte ≈ 183,269 MiB |
| 12 truy vấn TXT | 68.338 byte |
| Các mảng của X dạng CSR | 23.125.196 byte ≈ 22,054 MiB |

Thời gian truy vấn đo khi X và cache stem đã ở RAM; gồm đọc/giải mã TXT nhưng không gồm sao chép kết quả, xuất trace hay khởi động Python. Nạp SQLite gồm tái tạo chỉ mục và kiểm tra nhẹ; không xóa cache hệ điều hành, nên không gọi là phép đo đọc đĩa lạnh. Các mảng CSR không phải RAM đỉnh hay toàn bộ RAM của DatabaseIndex. Trung vị từng thành phần không nhất thiết cộng thành trung vị tổng.

Thời gian xây dựng kế thừa nhật ký đo thật: P2 `gd2_build` 28,290226 giây; đối chiếu GD1 độc lập 179,860591 giây; tổng P2 trước báo cáo 212,165871 giây. P3 transaction nhập + kiểm tra 26,008830 giây; mở lại/nạp/kiểm tra sâu 11,055640 giây; tổng trước báo cáo 39,871201 giây. Không dựng lại kho ở P6, không gọi các số lịch sử này là phép đo vừa chạy.

## 6. Ca vector rỗng

Đầu vào riêng `performance_final/empty_vector.txt`: `the and or is a chapter i ii iii`. Sau tiền xử lý không có đặc trưng; chương trình trả `empty_vector`, Top-3 rỗng, không tạo bản sao kết quả. Có trace tại `performance_final/empty_vector/Q01`. Q01 trong thư mục kiểm thử này chỉ là số thứ tự cục bộ của CLI; không phải Q01 chính thức. Ca này không tham gia mẫu số 12 của P@3.

## 7. Hai người chấm và P@3

Đã nhận đủ hai phiếu của **Khanh** và **Trong**, mỗi phiếu 36 cặp. Mọi dòng có mức 0/1/2, tên, lý do và trích dẫn từ cả truy vấn lẫn tài liệu; trích dẫn khớp nguyên văn sau chuẩn hóa khoảng trắng. Hai phiếu đã nộp được giữ nguyên byte tại `reviewer_A.csv`, `reviewer_B.csv` và bản sao trong `grading_final`.

Hai phiếu trùng điểm **34/36 cặp = 94,44%**. Hai bất đồng là P034 (Q03, hạng 3) và P003 (Q06, hạng 2): Khanh chấm 1, Trong chấm 0. Người dùng chốt cả hai mức **1**. Tin nhắn ghi `P304 = 1; P003 = 1`; do P304 không tồn tại và chỉ P034/P003 đang chờ chốt, P304 được hiểu là lỗi gõ P034, đã thông báo cách hiểu và lưu nguyên phản hồi tại [consensus_decision.json](../../gd2/evaluation/p6/consensus_decision.json).

`consensus.csv` giữ 34 điểm giống nhau và hai quyết định trên. Trích dẫn/lý do trong bảng cuối được kế thừa từ phiếu Khanh, nơi mức chấm trùng với quyết định cuối; không viết lại lý do để làm đẹp kết quả. Lý do khác của Trong vẫn nằm trong phiếu ban đầu và bảng đối chiếu. Chỉ mức 2 là liên quan; mức 0 và mức 1 đều không vào tử số P@3.

| Chỉ số | Kết quả |
|---|---:|
| Tổng cặp đã chốt | 36 |
| Mức 0 / mức 1 / mức 2 | 11 / 21 / 4 |
| Mean P@3 trên 12 truy vấn | 0,111111… = **11,11%** |
| Truy vấn có ít nhất một kết quả mức 2 | 3/12 = **25%** |
| Đồng thuận ban đầu theo ba mức | 34/36 = **94,44%** |

| Truy vấn | Mức cuối theo hạng 1–2–3 | Số kết quả mức 2 | P@3 |
|---|---|---:|---:|
| Q01 | 1 – 0 – 1 | 0 | 0 |
| Q02 | 0 – 0 – 1 | 0 | 0 |
| Q03 | 0 – 1 – 1 | 0 | 0 |
| Q04 | 2 – 1 – 1 | 1 | 1/3 = 0,333333… |
| Q05 | 1 – 1 – 0 | 0 | 0 |
| Q06 | 1 – 1 – 1 | 0 | 0 |
| Q07 | 0 – 1 – 0 | 0 | 0 |
| Q08 | 1 – 0 – 0 | 0 | 0 |
| Q09 | 1 – 1 – 1 | 0 | 0 |
| Q10 | 1 – 0 – 0 | 0 | 0 |
| Q11 | 2 – 2 – 1 | 2 | 2/3 = 0,666666… |
| Q12 | 1 – 2 – 1 | 1 | 1/3 = 0,333333… |

**Nhận xét chất lượng:** chỉ 4/36 kết quả đạt mức liên quan rõ; 21/36 chỉ liên quan một phần. Hệ thống thực hiện đúng công thức nhưng chất lượng truy hồi còn hạn chế trên bộ thử và tiêu chí đã chốt. Có chín truy vấn không đạt mức 2 trong Top-3; không loại các câu này hoặc đổi cách tính để tăng chỉ số. Do k=3 cố định cho mọi câu, Mean P@3 cũng bằng 4/36; không gọi tỷ lệ này là accuracy phân loại.

Q01 có điểm cuối 1–0–1 và P@3 = 0: minh họa kỹ thuật vẫn đầy đủ, nhưng chủ đề trinh thám chung chưa đủ để người chấm coi là sát tình huống trung tâm. Q04 có một kết quả mức 2 về tổ chức/đời sống thủy thủ tàu buôn. Q11 đạt 2/3 với hai văn bản của Thoreau về quan sát thiên nhiên; hai kết quả cùng tác giả là đặc điểm của ca này, không phải bằng chứng hệ thống hiểu ngữ nghĩa tổng quát. Q12 đạt 1/3 với văn bản khảo cứu động vật và đấu tranh sinh tồn. Các kết luận này dựa trên phiếu đã nộp, không suy ra từ cosine hoặc nhãn.

Bằng chứng cuối gồm [metrics.json](../../gd2/evaluation/p6/grading_final/metrics.json), [P@3 từng truy vấn](../../gd2/evaluation/p6/grading_final/precision_at_3.csv) và [bảng so sánh hai phiếu/điểm cuối](../../gd2/evaluation/p6/grading_final/comparison.csv). Các bản trung gian trước khi chốt có thể xem ở commit `17e25f9`. Không báo Recall/MAP/nDCG vì chưa có phán xét toàn kho.

## 8. Tái chạy và nghiệm thu

Chạy từ thư mục gốc dự án, dùng thư mục đích mới:

```powershell
python -m gd2.src.verify_queries
python -m gd2.src.verify_database
python -m gd2.src.search --query gd2/queries/Q01.txt gd2/queries/Q02.txt gd2/queries/Q03.txt gd2/queries/Q04.txt gd2/queries/Q05.txt gd2/queries/Q06.txt gd2/queries/Q07.txt gd2/queries/Q08.txt gd2/queries/Q09.txt gd2/queries/Q10.txt gd2/queries/Q11.txt gd2/queries/Q12.txt --out work/p6_recheck --trace
python -m gd2.src.evaluate prepare --run work/p6_recheck --out work/evaluation_recheck
python -m gd2.src.benchmark --out work/performance_recheck
python -m unittest discover -s gd2/tests -v
node gd2/tests/check_grading_forms.cjs
```

Khi có phiếu đã điền tại `gd2/evaluation/p6/reviewer_A.csv`, `reviewer_B.csv`, `consensus.csv`:

```powershell
python -m gd2.src.evaluate grade --out work/grading_recheck
```

Lệnh lưu ảnh chụp dữ liệu CSV, bảng so sánh và `metrics.json`; chỉ tạo `precision_at_3.csv` khi đủ toàn bộ điểm/bằng chứng. Từ chối ghi đè thư mục đầu ra, sai hash, thiếu/trùng ID cặp, mức không hợp lệ, bằng chứng không có trong văn bản hoặc hai phiếu mang cùng tên người chấm.

**Nghiệm thu P6: hoàn tất.** Đã đủ hai phiếu, điểm thống nhất, bằng chứng nội dung, P@3, trace, số đo và ca hạn chế. Bước tiếp theo là P7: viết báo cáo hợp nhất, giữ kết quả chất lượng thấp đúng như thực nghiệm và phân biệt rõ đúng kỹ thuật với hiệu quả truy hồi.
