# Đối chiếu phạm vi bốn tệp văn bản

Ngày kiểm tra: 04/11/2026. Kiểm tra nội dung cục bộ và đối chiếu toàn văn Project Gutenberg; không thay nội dung TXT.

## 1. Grania — Emily Lawless

Nguồn: [Grania, The Story of an Island (Complete), Gutenberg #58443](https://www.gutenberg.org/ebooks/58443), gồm hai tập. [Bản toàn văn](https://www.gutenberg.org/files/58443/58443-h/58443-h.htm) phân chia rõ VOL. I và VOL. II.

| Tệp | Phạm vi xác định | Số chương | Số từ theo quy tắc GD1 | Tên đã cập nhật trong CSV |
|---|---|---:|---:|---|
| book_0637.txt | Tập I: Phần I — September; Phần II — April | 7 + 9 = 16 | 41.213 | Grania, The Story of an Island (Vol. I, Parts I-II) |
| book_0797.txt | Tập II: Phần III — May to August; Phần IV — September Again | 11 + 7 = 18 | 46.812 | Grania, The Story of an Island (Vol. II, Parts III-IV) |

Đối chiếu từ câu kể đầu tiên tới câu cuối của mỗi tập, chuẩn hóa theo regex và dấu nháy của GD1:

- Tệp 0637 có một cụm tiêu đề Phần II xuất hiện thêm so với đoạn nguồn tương ứng: `PART II APRIL` (3 token). Các token còn lại trong đoạn đối chiếu khớp theo thứ tự. Tệp cũng có tiêu đề phần lặp ở đầu. Đây là khác biệt tiêu đề, không phải bằng chứng trùng hai tập.
- Tệp 0797 khớp toàn bộ 46.805 token của đoạn nguồn sau khi bỏ 7 token tiêu đề ở đầu khỏi phạm vi so sánh.

Hai ô title Grania ở dòng CSV 638 và 798 đã được sửa; hai ô The Earl’s Promise ở dòng 928 và 989 cũng đã được bổ sung tên tập trong bước chốt chuẩn bị. Giữ tên tệp, tên tác giả, mã nguồn và nội dung TXT. Bỏ chữ “Complete” khỏi tên hiển thị từng tệp để không hiểu nhầm một tệp chứa cả hai tập.

## 2. The Earl's Promise — Mrs. J. H. Riddell

Kết luận: hai tệp là Tập 1 và Tập 2 của cùng tiểu thuyết ba tập, không phải hai bản trùng toàn văn.

| Hạng mục | book_0927.txt | book_0988.txt |
|---|---|---|
| Tập xác định | Volume 1 of 3 | Volume 2 of 3 |
| Nguồn xác minh | [Gutenberg #70755](https://www.gutenberg.org/ebooks/70755) | [Gutenberg #70756](https://www.gutenberg.org/ebooks/70756) |
| Tiêu đề chương đầu | Kingslough née Ballylough | Mrs. Brady Understands Her Position |
| Chương cuối | XI — Nettie at Bay | XI — No Change |
| Số chương | 11, từ I đến XI | 11, từ I đến XI |
| Số từ theo GD1 | 51.277 | 53.226 |
| Phạm vi đối chiếu | Từ tiêu đề CHAPTER I đến câu cuối phần truyện | Từ tiêu đề CHAPTER I đến câu cuối phần truyện |
| Kết quả | Toàn bộ 51.277 token khớp chính xác đoạn nguồn | Toàn bộ 53.226 token khớp chính xác đoạn nguồn |
| Mốc cuối ở nguồn | END OF VOL. I. | END OF VOL. II. |

Phương pháp: tải bản TXT nguồn chính thức; chuyển chữ thường, chuẩn hóa ba loại dấu nháy giống GD1 và tách từ bằng `[a-z]+(?:'[a-z]+)?`; định vị đoạn nguồn bằng 60 token đầu/cuối; so sánh toàn bộ chuỗi token giữa hai mốc. Kết quả trên là khớp văn bản sau chuẩn hóa, không phải điểm cosine hoặc xác nhận hai file giống nhau từng byte. Header, mục lục, phần xuất bản và giấy phép ngoài phần truyện không nằm trong phép so sánh.

Liên hệ nội dung cũng nhất quán: cuối Tập 1 xoay quanh việc Nettie kết hôn và thái độ gia đình; Tập 2 tiếp tục hệ quả xã hội của cuộc hôn nhân đó. Chương đầu giống số I vì mỗi tập đánh số chương lại từ đầu.

Tên hiển thị đã cập nhật trong CSV ở bước chốt chuẩn bị:

- `The Earl's Promise (Vol. 1 of 3)` cho `book_0927.txt`.
- `The Earl's Promise (Vol. 2 of 3)` cho `book_0988.txt`.

## 3. Tác động tới báo cáo GD2

Đơn vị lưu trữ và tìm kiếm vẫn là tệp: mỗi tệp có một vector TF-IDF. Việc bổ sung tên tập/phần chỉ phục vụ mô tả và hiển thị, không thay cách tính điểm.

Không nên tiếp tục diễn đạt mọi tệp đều là một tác phẩm hoàn chỉnh. Có thể làm rõ trong phần bổ sung:

> Bộ dữ liệu gồm 1.000 tệp văn bản. Đơn vị lưu trữ và tìm kiếm là tệp; một số tệp tương ứng với các tập khác nhau của cùng tác phẩm. Tên tập/phần được bổ sung vào metadata để phân biệt. Các tệp này có nội dung khác nhau và vẫn được biểu diễn, xếp hạng độc lập theo phương pháp của GD1.

Câu này cần được ghi như phần làm rõ mô tả GD1, không chỉnh âm thầm PDF đã nộp. Khi chọn tác phẩm ngoài kho làm truy vấn, loại trừ ở cấp tác phẩm: một tập khác của Grania hoặc The Earl's Promise không được xem là tác phẩm mới ngoài kho.

Bằng chứng chi tiết: `docs/audit/GD2_volume_verification.json`; nhật ký bốn ô CSV đã sửa: `docs/audit/GD2_metadata_title_changes.json`. Bảng kiểm tra metadata trước khi sửa tên vẫn được giữ làm ảnh chụp hiện trạng cũ.
