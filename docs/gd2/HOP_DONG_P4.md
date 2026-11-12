# Hợp đồng P4 đã chốt

Ngày chốt: 04/11/2026. Đã triển khai và kiểm chứng P4; xem BIEN_BAN_P4.md. Đặc tả dưới đây là hành vi của chương trình hiện tại.

## Đầu vào và vòng đời

CLI:

```powershell
python -m gd2.src.search --query input.txt --out work/run01
python -m gd2.src.search --query Q01.txt Q02.txt --out work/run02 --trace
```

`--query` nhận một hoặc nhiều đường dẫn TXT; `--database` mặc định là `gd2/database/documents.sqlite`. Một lần chạy nạp CSDL một lần rồi xử lý tuần tự các tệp. Chương trình dùng vocabulary/IDF đã nạp và tokenizer chung, không fit lại, không cần đọc artifact P2 để tìm kiếm. Ghi thời gian nạp kho riêng với thời gian từng truy vấn.

`load_database()` kiểm tra schema, trạng thái hoàn tất, cấu hình đặc trưng, số hàng/cột/phần tử, ánh xạ và giá trị vector trong RAM. Kiểm tra sâu SQL integrity, khóa ngoại, df/công thức và đối chiếu P2 nằm trong `python -m gd2.src.verify_database`. Khi đưa một bản dựng vào sử dụng, chạy lệnh này trước phiên tìm kiếm. Kiểm tra nhanh không thay thế phép kiểm chứng toàn bộ trọng số.

## Kết quả mặc định

- In bảng Top-3: thứ hạng, filename, tên sách, tác giả, nhãn và cosine.
- Ghi `results.json`, `results.csv` và ba bản sao TXT theo đúng thứ hạng cho mỗi truy vấn hợp lệ có vector khác 0. Tên bản sao có tiền tố hạng; kiểm tra SHA-256 với `raw_sha256` trước khi công bố kết quả. Không sửa tệp corpus.
- Ghi build ID, đường dẫn/hash truy vấn, số từ, số chiều khác 0, trạng thái, điểm đầy đủ và thời gian; chỉ làm tròn khi hiển thị.
- Mỗi truy vấn có thư mục riêng theo mã chạy tuần tự Q01, Q02… và manifest ánh xạ tới đường dẫn đầu vào, tránh trùng tên khi hai tệp cùng basename. Mã này chỉ định danh lần chạy, không tự xác nhận truy vấn thuộc bộ đánh giá chính thức.
- Thư mục đầu ra đã tồn tại bị từ chối; không ghi đè kết quả cũ. Truy vấn lỗi không tạo bản sao TXT giả.

## Trace tùy chọn

`--trace` bổ sung bảng token/giữ-bỏ/stem, trọng số term truy vấn, toàn bộ 1.000 điểm và đóng góp term của từng kết quả Top-3. Tổng đóng góp term phải bằng cosine trong sai số 1e-10. Ghi rõ term ngoài vocabulary và cách tính TF/IDF/L2. Dùng chế độ này cho Q01 và các ca kiểm chứng/báo cáo; tìm kiếm thông thường không cần xuất mọi bảng trung gian.

## Xếp hạng và ngoại lệ

- Sắp theo cosine giảm dần bằng độ chính xác đầy đủ; phá hòa bằng filename tăng dần. Không dùng nhãn/tên sách/tác giả để điều chỉnh điểm.
- TXT đọc bằng UTF-8-sig. Tệp không tồn tại, không đọc được, sai mã hóa, rỗng hoặc không tạo raw token: báo lỗi cụ thể.
- Có raw token nhưng không có term thuộc vocabulary: trạng thái `empty_vector`, không có Top-3.
- Vector hợp lệ nhưng chỉ một/hai tài liệu có điểm dương: vẫn trả ba theo quy tắc xếp hạng; ghi rõ những kết quả điểm 0.
- Chấp nhận truy vấn ngắn để kiểm thử. Khoảng 950–1.050 từ trước lọc chỉ là điều kiện của bộ thực nghiệm chính thức P5; không dùng làm điều kiện chặn CLI.
- Một truy vấn lỗi không dừng các truy vấn khác trong lô. Kết thúc với mã 1 nếu có lỗi đọc/xử lý, mã 0 nếu tất cả được xử lý (bao gồm trạng thái empty_vector). CSDL không hợp lệ thì dừng cả lô trước xử lý.
- Nguồn truy vấn chính thức vẫn được ghi riêng để chứng minh tác phẩm ngoài kho; việc bỏ trường nguồn khỏi bảng documents không thay đổi yêu cầu này.

## Điều kiện hoàn thành P4

Kiểm chứng transform với vocabulary/IDF cố định; thứ tự điểm và phá hòa; vector rỗng; lỗi đầu vào; TXT trả về đúng hash; tổng đóng góp term; xử lý nhiều truy vấn nhưng chỉ nạp một lần. Không coi điểm cosine là xác suất đúng hoặc phần trăm giống nhau. Giao diện, phương pháp mới và chấm chất lượng thuộc các bước sau.
