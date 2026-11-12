# Nguồn cho bộ truy vấn P5

Các `pg*.txt` được tải từ URL Plain Text chính thức của Project Gutenberg, giữ nguyên byte và phần thông tin/giấy phép đi kèm. `source_catalog.csv` ghi nguồn, hash, dung lượng và thời điểm tải. Đây là tài liệu nguồn ngoài kho; không đưa vào bước dựng TF-IDF.

Đoạn truy vấn liên tục được lưu riêng trong `gd2/queries`; offset trong manifest tính trên chuỗi UTF-8-sig đã giải mã, giữ CRLF, bắt đầu từ 0 và kết thúc không bao gồm ký tự ở chỉ số cuối. Không xóa header/footer của bản nguồn: chỉ lựa chọn đoạn nằm trong phần nội dung.
