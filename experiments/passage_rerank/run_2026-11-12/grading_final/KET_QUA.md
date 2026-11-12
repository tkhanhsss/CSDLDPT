# Kết quả chốt thử nghiệm theo đoạn

Đã chốt 58/58 cặp theo hai phiếu độc lập và bảng thống nhất do người dùng gửi. Đã xử lý toàn bộ 10 bất đồng.

| Chỉ số | Cách hiện tại | Xếp hạng theo đoạn |
|---|---:|---:|
| Mean P@3 | 5.56% | 0.00% |
| Kết quả mức 2 | 2/36 | 0/36 |
| Truy vấn có ít nhất một kết quả mức 2 | 2/12 | 0/12 |

Cấu hình Top-30, đoạn 1.000 từ, bước trượt 500 từ không cải thiện kết quả trên bộ truy vấn này. Mean P@3 giảm 5,56 điểm phần trăm.
Hai cặp mức 2 là E051 ở Q04 và E038 ở Q11. Cả hai có trong Top-3 cách hiện tại và bị loại khỏi Top-3 sau xếp hạng theo đoạn.
Giữ thuật toán hiện tại cho hệ thống. Kết quả này chỉ áp dụng cho cấu hình đã thử và bộ Q01–Q12 đã xem trước, không chứng minh mọi cách tìm theo đoạn đều kém hơn.

## Phạm vi điểm chấm

Mốc 11,11% của P6 thuộc đợt chấm trước và giữ nguyên. Mốc 5,56% ở đây là chấm lại cách hiện tại trong pool chung của thử nghiệm. So sánh hai phương pháp bằng cùng bộ consensus mới.
Hai phiếu đầu thống nhất 48/58 cặp, tương đương 82,76%. Việc chốt bất đồng không làm thay đổi tỷ lệ đồng thuận ban đầu.

## Hồ sơ

`consensus.csv` có đủ 58 mức cuối. `comparison.csv` lưu điểm A/B, mức chốt, nguồn quyết định, nguồn trích dẫn và lý do.
`consensus_decision.json` giữ nguyên bảng quyết định và lý do người dùng. Các tỷ lệ nội dung ước lượng trong lý do là nhận xét của người chấm, không phải số đo tính lại.
`precision_at_3.csv` lưu kết quả từng truy vấn. `metrics.json` lưu tổng hợp. `manifest.json` khóa hash đầu ra.
Phiếu A/B gốc, hồ sơ đối chiếu lần 1, CSDL, kết quả chính thức và báo cáo GD2 giữ nguyên.
