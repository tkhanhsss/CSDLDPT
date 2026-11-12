# Thử nghiệm xếp hạng theo đoạn

Đã [chốt đủ 58 cặp](run_2026-11-12/grading_final/KET_QUA.md) theo hai phiếu và 10 quyết định thống nhất của người dùng. Mean P@3 của cách hiện tại là **5,56%**, cách theo đoạn là **0%** trên cùng bộ điểm mới. Cấu hình đã thử không cải thiện kết quả. Giữ thuật toán hiện tại cho hệ thống.

Chạy từ thư mục gốc với môi trường Python của GD2.

```powershell
python -u -m experiments.passage_rerank.run --out experiments/_work/passage_rerank
```

Đầu ra phải là thư mục mới dưới `experiments/`. Git bỏ qua các lượt chạy lại trong `experiments/_work/`. Mặc định lấy Top-30 bằng cosine toàn văn, chia từng tài liệu thành các đoạn 1.000 từ theo regex GD1 với bước trượt 500 từ. Cửa sổ cuối neo tại từ cuối và giữ đủ 1.000 từ nếu tài liệu đủ dài. Các đoạn dùng cùng vocabulary, IDF, log TF và chuẩn hóa L2 của GD2. Lấy điểm đoạn cao nhất làm điểm tài liệu. Khi hòa điểm, chọn filename tăng dần. Khi các đoạn hòa điểm, chọn đoạn sớm nhất.

Đây là thử nghiệm bổ sung được yêu cầu sau P7. Không thay thuật toán, CSDL, phiếu chấm hoặc báo cáo chính thức. Nhãn, tên sách, tác giả và điểm chấm cũ không tham gia xếp hạng.

Mỗi lượt chạy kiểm tra khóa P5 và baseline, đối chiếu 12.000 điểm chính thức bằng hàm kiểm chứng P6, xác minh hash tài liệu ứng viên, rồi kiểm tra độc lập công thức cosine của đoạn thắng ở mỗi ứng viên. Manifest lưu hash đầu vào và đầu ra. Mã không chỉnh sửa kết quả cũ.

Mở README trong thư mục kết quả để gửi hai phiếu HTML độc lập cho người chấm. CSV là dữ liệu trao đổi của chương trình, gồm danh sách cặp, điểm truy hồi và phiếu trống. Kết quả P@3 chờ chấm, dùng cùng rubric 0/1/2 của P6 và chỉ mức 2 được tính liên quan.

Chỉ thử một cấu hình đã chọn trước lượt chạy này. Q01–Q12 đã được xem kết quả nên là bộ phát triển cho thử nghiệm, chưa phải bằng chứng kiểm định trên truy vấn mới.

Lượt [12/11/2026](run_2026-11-12/README.md) tạo 58 cặp cần chấm, gồm 14 cặp chung và 22 cặp mới. Mỗi phương pháp đóng góp 36 vị trí Top-3. Hồ sơ chuẩn bị giữ nguyên trạng thái lúc xuất phiếu, kết quả chốt nằm trong `grading_final/`.

Hai HTML nhúng toàn văn có thể tạo lại từ bảng mã cặp và kho sách. Lệnh xuất đối chiếu SHA256 với phiếu gốc. Hai CSV đã nộp nằm trong `run_2026-11-12/reviewers/`.

```powershell
python -m unittest experiments.passage_rerank.test_passages -v
python -m experiments.passage_rerank.verify_output experiments/passage_rerank/run_2026-11-12
python -m experiments.passage_rerank.export_forms experiments/passage_rerank/run_2026-11-12 --out work/passage_forms
node experiments/passage_rerank/check_forms.cjs experiments/passage_rerank/run_2026-11-12 work/passage_forms
```

Các tọa độ ký tự tính trên chuỗi Unicode đọc bằng Python, đã chuẩn hóa xuống dòng CRLF thành LF. Hash nguồn vẫn tính theo toàn bộ byte tệp gốc. Thời gian truy vấn trong lượt thử bao gồm dựng đoạn cho các tài liệu chưa có trong cache, không gồm kiểm chứng độc lập hoặc xuất phiếu.

## Đối chiếu phiếu đã nộp

Đợt [chấm lần 1](run_2026-11-12/grading_round_1/DOI_CHIEU_CHAM.md) đã kiểm tra đủ 58 cặp mỗi phiếu và toàn bộ trích dẫn. Ban đầu hai người thống nhất 48 cặp và bất đồng 10 cặp. P@3 theo A là 5,56% cho cách hiện tại và 0% cho cách theo đoạn. Theo B, cả hai cách đạt 0%. Hồ sơ này giữ nguyên kết quả trước khi chốt.

`grading_round_1/consensus_draft.csv` giữ điểm và bằng chứng cho 48 cặp đồng thuận, để trống 10 bất đồng. Hai CSV đã nộp được lưu nguyên byte tại thư mục đối chiếu. Kết quả GD2 chính thức và mốc P6 11,11% giữ nguyên, thuộc đợt chấm trước.

Đã giải quyết 10 bất đồng bằng bảng người dùng gửi tại `run_2026-11-12/consensus_decision.json`. `grading_final/consensus.csv` và `coordinator/consensus.csv` có đủ 58 mức cuối, phân bố 24 mức 0, 32 mức 1 và 2 mức 2. E051 ở Q04 và E038 ở Q11 đều thuộc Top-3 cách hiện tại, không còn trong Top-3 theo đoạn. Tỷ lệ đồng thuận ban đầu vẫn là 48/58, tương đương 82,76%.

Để tái lập kết quả chốt, dùng một thư mục mới với lệnh sau.

```powershell
python -m experiments.passage_rerank.finalize --run experiments/passage_rerank/run_2026-11-12 --decisions experiments/passage_rerank/run_2026-11-12/consensus_decision.json --out experiments/_work/grading_final_recheck
```

Chạy lại đối chiếu bằng một thư mục đầu ra mới khi cần.

```powershell
python -m experiments.passage_rerank.grade --run experiments/passage_rerank/run_2026-11-12 --out experiments/_work/grading_round_2
```
