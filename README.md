# Hệ CSDL lưu trữ và tìm kiếm văn bản

Trạng thái ngày 07/11/2026: **hoàn tất P2–P7; đã có báo cáo hợp nhất Word và PDF 40 trang**. Đã tái lập TF-IDF 1.000 × 34.416 và lưu đủ 1.926.766 trọng số khác 0 vào `gd2/database/documents.sqlite`. Ma trận đọc lại khớp P2 hoàn toàn; CSDL có đủ metadata và 14 nhãn, kiểm tra khóa và công thức đều đạt. Nội dung kho và đặc trưng được bảo toàn; metadata hiện có ba cột theo yêu cầu người dùng. P6 đã chạy đủ 12 truy vấn, kiểm chứng 12.000 điểm và 36 tệp Top-3, xuất trace và đo hiệu năng. Đã chốt 36 điểm liên quan: Mean P@3 = 11,11%; 3/12 truy vấn có ít nhất một kết quả mức 2. Hai phiếu ban đầu và quyết định thống nhất được giữ riêng.

## Cấu trúc dự án

```text
CSDLDPT/
  data/
    corpus/                  # 1.000 book_*.txt, giữ nguyên nội dung và filename
    metadata/
      selected_stories.csv   # tác phẩm/tác giả; khóa new_filename
      labels.jsonl           # nhãn GD1; khóa filename
    provenance/              # nhật ký rà soát nhãn GD1
  gd1/
    gd1_stats.py              # mã nguồn GD1 nguyên gốc
    results/                  # CSV, JSON và hình GD1 nguyên gốc
  gd2/
    src/                      # tiền xử lý, đặc trưng, dựng/đọc/kiểm tra SQLite
    config/                   # bản sao cấu hình/stopword từ baseline
    artifacts/p2/             # count, TF-IDF, df/IDF, ánh xạ và biên bản
    database/                 # documents.sqlite, schema, SQL kiểm tra, biên bản P3
    tests/                    # kiểm thử tiền xử lý và công thức
  docs/
    gd1/                     # PDF đã nộp
    gd2/                     # kế hoạch, phác thảo, đối chiếu và phần làm rõ
    audit/                   # bằng chứng kiểm tra, nhật ký đổi tên/chuyển thư mục
  baselines/
    pre_gd2_2026-11-04/       # manifest/hash, cấu hình, stopword, snapshot GD1
  tools/
    verify_baseline.py        # kiểm tra mốc; chỉ đọc
  archive/                   # ZIP và thư mục tạm đã chuyển vào lưu trữ
```

Chỉ `data/corpus/book_*.txt` tham gia xây đặc trưng. Không quét mọi TXT đệ quy trong dự án: snapshot, dữ liệu nguồn đối chiếu và truy vấn tương lai không thuộc corpus.

## Tài liệu cần đọc

- [Kế hoạch GD2 đã chốt — đọc mục 0 để bắt đầu](docs/gd2/KE_HOACH_GD2.md).
- [Kết quả và biên bản P2](docs/gd2/BIEN_BAN_P2.md).
- [Kết quả và biên bản P3](docs/gd2/BIEN_BAN_P3.md).
- [Kết quả, cách chạy và biên bản P4](docs/gd2/BIEN_BAN_P4.md).
- [Bộ truy vấn và biên bản P5](docs/gd2/BIEN_BAN_P5.md).
- [Thực nghiệm và biên bản P6](docs/gd2/BIEN_BAN_P6.md).
- [Báo cáo hợp nhất P7 và bản Word/PDF](gd2/report/README.md).
- [Biên bản nghiệm thu P7](docs/gd2/BIEN_BAN_P7.md).
- [Hướng dẫn hai thành viên chấm P6](gd2/evaluation/p6/README.md).
- [Hợp đồng CLI và đầu ra P4 đã chốt](docs/gd2/HOP_DONG_P4.md).
- [Cách chạy, kiểm tra và đọc dữ liệu P2](gd2/README.md).
- [Phác thảo báo cáo GD2](docs/gd2/PHAC_THAO_BAO_CAO_GD2.md).
- [Ghi chú diễn đạt GD1 — dùng khi viết báo cáo ở P7](docs/gd2/LAM_RO_GD1_TRUOC_GD2.md).
- [Đối chiếu các tập tác phẩm](docs/gd2/DOI_CHIEU_CAC_TAP_TAC_PHAM.md).
- [PDF GD1 đã nộp](docs/gd1/GD1-CSDLDPT-23-03.pdf).
- [Mốc dữ liệu và cấu hình trước GD2](baselines/pre_gd2_2026-11-04/README.md).

## Kiểm tra trước khi làm GD2

Chạy từ thư mục gốc:

```powershell
python tools/verify_baseline.py
```

Kết quả `ok: true` xác nhận hash corpus, metadata, nhãn, mã và kết quả GD1 khớp mốc đã lưu, đồng thời kiểm tra bản snapshot và độ phủ metadata/nhãn. Script không sửa hay tái tạo baseline. Nếu phát hiện khác biệt, xem danh sách `problems` trước khi tiếp tục.

## Chạy lại thống kê GD1 khi cần

```powershell
python gd1/gd1_stats.py --data_dir data/corpus --labels data/metadata/labels.jsonl --out work/gd1_recheck
```

Dùng thư mục đầu ra mới để giữ `gd1/results` là kết quả gốc đã nộp. Lệnh này chạy đầy đủ thống kê và có thể tốn thời gian; không cần chạy chỉ để xác minh hash.

Các đường dẫn cũ trong `gd1/results/summary.json` phản ánh lần chạy GD1 và được giữ nguyên như dữ liệu lịch sử. Mã GD1 nhận đường dẫn qua tham số dòng lệnh nên không cần sửa nội dung mã khi chuyển thư mục.

## Bước tiếp theo

P7 đã hoàn tất. Báo cáo Word và PDF ở `gd2/report`; đã kiểm tra đủ 40 trang và bảo toàn nội dung Chương 1–2. Điểm cuối và P@3 nằm trong `gd2/evaluation/p6/grading_final`; số đo chính ở `gd2/evaluation/p6/performance_final`. Phạm vi GD2 đã hoàn thành; bước tiếp theo thuộc GD3 là chuẩn bị giao diện demo tái sử dụng CSDL và hàm search. Muốn kiểm tra lại phép tổng hợp, dùng `python -m gd2.src.evaluate grade --out gd2/evaluation/p6/grading_recheck` với thư mục đích chưa tồn tại.

Phạm vi triển khai đã chốt: Python + SQLite, tìm kiếm bằng dòng lệnh, 12 truy vấn ngoài kho và PDF hợp nhất. Thứ tự P2 → P3 → P4, chuẩn bị P5, rồi P6 → P7. Các vấn đề diễn đạt GD1 đã được làm rõ trong phần đầu Chương 3 và danh mục từ viết tắt của báo cáo hợp nhất.
