# Hợp đồng biên tập báo cáo GD1 và GD2

Tham chiếu: docs/gd1/GD1-CSDLDPT-23-03.docx và PDF cùng tên, 14 trang, hai section. Bản Word GD2 ban đầu có cùng 149 đoạn, sáu bảng và năm ảnh. Đã xuất Word sang work/reference.pdf và xem đủ 14 ảnh trang. Hash và kiểm kê package lưu trong source_inventory.json khi dựng.

Trang A4 dọc, lề trên/dưới 2 cm, trái 2,501 cm, phải 1,801 cm. Hai section dùng footer khác nhau; bìa không hiện số trang, phần sau đánh số liên tục. Bìa có khung, logo PTIT, tên trường/khoa, học phần INT1418, nhóm 23 lớp 03, hai sinh viên và giảng viên TS. Nguyễn Đình Hóa. Giữ thông tin và hình bìa; thêm nhãn giai đoạn vào đoạn trống.

Thân GD1 dùng Times New Roman 13, thụt đầu dòng khoảng 0,8 cm, CTDT-Text. CTDT-H1 là chương có đánh số, CTDT-H2/H3 là đề mục. Bảng cũ có nền trắng, viền đen; giữ nguyên. Chú thích CTDT-Bang và CTDT-Hinh đánh số tự động. Có 19 khối công thức OMML, bốn hình nội dung và một logo; giữ dữ liệu ảnh và nội dung công thức. CTDT-H1/2, CTDT-Bang/Hinh được đưa vào các danh mục mới.

Vùng sửa: đoạn 32 đến trước đoạn 87 của bản gốc là phần mục lục, danh mục, mở đầu; thay bằng một bộ danh mục hợp nhất và mở đầu bốn chương. Bảng viết tắt đầu tiên được thay, sửa NLTK chỉ dùng Porter; nguồn stopword là scikit-learn + EXTRA_STOP. Đoạn 87 đến hết Chương 2, gồm các bảng 1–5 và hình 1–4, giữ toàn bộ nội dung, công thức, bảng và hình. Cho phép dàn lại trang, thêm bookmark và cập nhật trường/số trang. Các làm rõ về tập tác phẩm và BOM đặt ở mục 3.1, không sửa câu gốc Chương 1.

Phần mới dùng Times New Roman 13, bảng 10,5–11,5; heading đen. Bảng mới viền xám, đầu bảng xanh nhạt, cột có độ rộng theo dữ liệu; không cố định chiều cao hàng, lặp hàng tiêu đề và tránh cắt ngang hàng. Hình mới vẽ bằng mã với chữ rõ. Số hình nối từ 5, bảng nối từ 6. Chương 3–4, kết luận, tài liệu tham khảo và phụ lục bổ sung đầy đủ bằng chứng trong PDF.

Giữ package nguồn nguyên trạng. Làm việc trên bản sao, sử dụng lại toàn bộ relationship ảnh/kiểu/numbering gốc. Thêm style riêng cho phần mới, không sửa style CTDT dùng ở Chương 1–2. So sánh văn bản, bảng, OMML, dữ liệu media trước và sau; Word có thể chuẩn hóa XML khi cập nhật trường nên không dùng hash toàn XML sau Word làm điều kiện bảo toàn nội dung.

Môi trường không có LibreOffice; render_docx.py đã chạy và báo thiếu soffice.exe. Microsoft Word COM đã xuất được bản tham chiếu đúng 14 trang. Dùng Word để cập nhật TOC/PAGE và xuất PDF thật; Poppler bundled tạo PNG để xem toàn bộ trang. Không thay bằng PDF tự dàn tách rời DOCX.
