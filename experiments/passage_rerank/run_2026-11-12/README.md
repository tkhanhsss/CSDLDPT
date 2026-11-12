# Chấm thử nghiệm theo đoạn

Đã chạy Q01–Q12 và gộp Top-3 của hai phương pháp thành **58 cặp riêng biệt**.
Có 14 cặp cùng xuất hiện và 22 cặp mới so với Top-3 chính thức.

## Hai thành viên chấm độc lập

1. Gửi riêng `reviewers/reviewer_A.html` cho người A và `reviewers/reviewer_B.html` cho người B. Mỗi HTML tự chứa đầy đủ văn bản.
2. Mỗi người chấm toàn bộ 58 cặp trên phiếu của mình, kể cả các cặp đã gặp ở P6. ID E là của đợt này, không phải ID P cũ.
3. Đọc cả truy vấn và phần cần thiết của tài liệu. Mức 2 sát chủ đề hoặc tình huống trung tâm, mức 1 liên quan một phần hoặc chung bối cảnh, mức 0 không liên quan đáng kể. Chỉ trùng tên hoặc từ không đủ để chọn mức 2.
4. Điền hai trích dẫn nguyên văn và lý do cho mỗi cặp, kể cả mức 0. Phiếu để trống, không dùng lại điểm cũ.
5. Nhập tên và bấm tải CSV thường xuyên. Dùng nút nạp CSV để tiếp tục. Trình duyệt không tự lưu khi đóng trang.
6. Gửi lại hai CSV. Sau đó đối chiếu bất đồng và chốt consensus, rồi tính P@3 cho cả hai phương pháp trên cùng bộ điểm.

Phiếu chỉ hiển thị mã cặp, mã truy vấn và nội dung. Trước khi nộp, không xem thư mục `coordinator`, bảng xếp hạng, điểm cũ hoặc phiếu của người kia.

## Dành cho người tổng hợp sau khi chấm

`coordinator/pair_map.csv` là danh sách các cặp cần chấm và ánh xạ vào Top-3 hai phương pháp.
`top3_all.csv` lưu 72 vị trí xếp hạng. `comparison.csv` đếm phần trùng theo truy vấn.
`candidates.csv` lưu 30 ứng viên mỗi truy vấn. `passage_scores.csv` lưu tất cả điểm đoạn.
`passages/` chứa đoạn tốt nhất cho từng cặp trong pool, dành cho kiểm tra kỹ thuật sau khi chấm.
`consensus.csv` để trống cho kết quả chốt. Tọa độ từ bắt đầu từ 1 và bao gồm hai đầu, tọa độ ký tự bắt đầu từ 0 và không bao gồm cuối.

P@3 của mỗi truy vấn bằng số tài liệu mức 2 trong Top-3 chia 3. Lấy trung bình cả 12 truy vấn, đồng thời đếm số truy vấn có ít nhất một tài liệu mức 2.
Chưa có P@3 mới khi chưa chấm xong. Điểm cosine của hai cách có biểu diễn khác nhau, không dùng việc điểm tăng để kết luận chất lượng tốt hơn.
Q01–Q12 là bộ thử nghiệm đã được xem kết quả. Cần bộ truy vấn mới nếu muốn xác nhận khả năng khái quát sau khi chọn cấu hình.

Thông số là Top-30, đoạn 1000 từ, bước trượt 500 từ. Giữ nguyên vocabulary, IDF và tiền xử lý GD2.
Kết quả này nằm ngoài kết quả GD2 chính thức. Chỉ xếp hạng lại Top-30, chưa tìm đoạn trên toàn bộ kho.
Số đo thời gian là một lượt chạy có tái sử dụng cache, không so trực tiếp với benchmark P6.
