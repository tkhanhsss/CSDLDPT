# Chấm và tổng hợp P6

Trạng thái 06/11/2026: chạy đủ 12 truy vấn, kiểm tra 12.000 điểm và 36 bản sao đã đạt. Đã có đủ hai phiếu độc lập và điểm thống nhất; Mean P@3 = 11,11%. P034 = 1, P003 = 1 đã chốt theo phản hồi người dùng (P304 được hiểu là lỗi gõ P034, đã ghi trong consensus_decision.json). Kết quả chính thức ở `grading_final/metrics.json` và `grading_final/precision_at_3.csv`.

## Dành cho hai thành viên

1. Người thứ nhất mở `reviewer_A.html`, người thứ hai mở `reviewer_B.html` bằng trình duyệt. Mỗi tệp tự chứa đủ nguyên văn, không cần Internet.
2. Nhập tên thật hoặc tên thống nhất của thành viên. Đọc truy vấn và tài liệu; chấm đủ 36 cặp bằng mức 0/1/2 theo hướng dẫn trên phiếu.
3. Mỗi cặp nhập một đoạn nguyên văn từ truy vấn, một đoạn nguyên văn từ tài liệu, cùng lý do. Không gõ dấu `...` thay phần bị lược giữa trích dẫn. Có thể dùng các đoạn liên tục ngắn và đọc thêm ngữ cảnh.
4. Bấm **Tải CSV điểm đã nhập** để lưu; có thể xuất thường xuyên rồi dùng **Nạp lại CSV đang chấm** để tiếp tục. Trang không tự lưu khi đóng/tải lại.
5. Giữ hai phiếu riêng cho đến khi cả hai đã nộp. Gửi đường dẫn hai CSV đã xuất cho người tổng hợp. Không xem `pair_map.csv`, bảng Top-3 hoặc phân tích ca trước khi chấm xong.

Mức 2: liên quan rõ với chủ đề/tình huống trung tâm; mức 1: chỉ liên quan một phần hoặc chung bối cảnh; mức 0: không liên quan nội dung đáng kể. Trùng tên hoặc cùng nhãn không đủ. Phải có bằng chứng cả với mức 0. Chỉ mức 2 tính vào tử số P@3.

## Dành cho người tổng hợp

`reviewer_A.csv`, `reviewer_B.csv` và `consensus.csv` ban đầu trống. Giữ bản gốc hai CSV đã nộp; đưa bản sao đúng tên vào thư mục này. Chạy lệnh dưới đây với thư mục mới để lưu ảnh chụp phiếu và lập `comparison.csv`:

```powershell
python -m gd2.src.evaluate grade --out work/grading_recheck
```

Hai thành viên xem các bất đồng rồi thống nhất `consensus.csv`, cùng schema với hai phiếu. Cột `reviewer` ở phiếu thống nhất dùng một tên chung, ví dụ `Thanh vien A + Thanh vien B`; trích dẫn và lý do vẫn bắt buộc. Không sửa điểm ban đầu của A/B. Lần cuối đã lưu ở `grading_final`; khi kiểm tra lại dùng tên mới như `grading_recheck`, không ghi đè thư mục đã có.

Nếu còn điểm trống, lệnh trả `awaiting_human_judgments`, P@3 là `null`, không tự tính ô trống thành 0. Nếu phiếu có lỗi, lệnh dừng và báo ID cặp để sửa. Bản tổng hợp hoàn chỉnh có P@3 từng câu, Mean P@3 trên 12 câu, phân bố ba mức, đồng thuận ban đầu và tỷ lệ câu có ít nhất một kết quả mức 2.

## Bằng chứng thực nghiệm

- `../../results/p6_official`: 12 kết quả, 36 TXT, trace đầy đủ và 12.000 điểm.
- `top3_all.csv`, `query_statistics.csv`: bảng tổng hợp dùng cho P7.
- `Q01/`: bảng rút gọn 15 token, 15 term, Top-10 và đóng góp có tổng phần còn lại.
- `technical_verification.json`, `evaluation_manifest.json`: kiểm tra điểm, file, CSDL và hash.
- `performance_final/`: phép đo dùng cho báo cáo, một lần làm nóng và năm lần đo mỗi truy vấn, cùng ca vector rỗng riêng.
- `case_analysis.json`, `case_excerpts.md`: nhận xét kỹ thuật và trích dẫn có vị trí, do Codex; không phải chấm người thật.
- `consensus_decision.json`: phản hồi chốt hai cặp và cách xử lý lỗi gõ ID.
- `grading_final/`: đủ 36 mức cuối, bảng đối chiếu, P@3 và hash ba phiếu.

Xem [biên bản P6](../../../docs/gd2/BIEN_BAN_P6.md) để biết số đo, phạm vi và kết luận thực nghiệm.
