# Hệ CSDL lưu trữ và tìm kiếm văn bản

Dự án tìm ba văn bản tiếng Anh phù hợp nhất trong kho 1.000 tệp bằng TF-IDF và cosine. Đặc trưng được lưu trong SQLite. GD1 và GD2 đã hoàn thành, với 12 truy vấn đánh giá và Mean P@3 = 11,11%.

- [PDF hợp nhất để nộp](gd2/report/GD1-GD2-CSDLDPT-23-03.pdf)
- [Word hợp nhất để chỉnh sửa](gd2/report/GD1-GD2-CSDLDPT-23-03.docx)
- [Hướng dẫn GD2](gd2/README.md)
- [Thử nghiệm xếp hạng theo đoạn và phiếu chấm](experiments/passage_rerank/README.md)

## Chạy tìm kiếm

Từ thư mục gốc, dùng Python 3.10.11 và cài thư viện theo tệp phiên bản đã khóa.

```powershell
python -m pip install -r gd2/requirements.txt
python -m gd2.src.search --query gd2/queries/Q01.txt --out work/search_q01 --trace
```

Mở `work/search_q01/Q01/results.csv` để xem điểm và ba tệp TXT tương ứng. Chọn thư mục đầu ra mới mỗi lần chạy. CSDL đã dựng nằm tại `gd2/database/documents.sqlite`.

## Cấu trúc thư mục

```text
data/                 Kho TXT, metadata, nhãn và nhật ký rà soát
gd1/                  Mã và kết quả thống kê GD1
gd2/
  src/, tests/        Mã xử lý và kiểm thử
  config/, database/  Cấu hình, CSDL SQLite và schema
  queries/, sources/  Bộ truy vấn chính thức và nguồn đối chiếu
  artifacts/          Đặc trưng P2 và bằng chứng kiểm chứng
  results/            Top-3 và trace chính thức của P6
  evaluation/p6/      Hai phiếu chấm, kết quả chốt và số đo
  report/             Word, PDF và công cụ dựng báo cáo
docs/                 Kế hoạch, biên bản, báo cáo GD1 và hồ sơ đối chiếu
baselines/            Mốc kiểm tra SHA256 và snapshot GD1
tools/                Công cụ kiểm tra baseline
experiments/          Thử nghiệm bổ sung và phiếu chấm, tách khỏi GD2 chính thức
work/                 Kết quả chạy thử trên máy, tự tạo khi chạy
```

Chỉ các tệp `data/corpus/book_*.txt` được dùng để dựng đặc trưng. Kết quả chạy thử trong `work/` được Git bỏ qua.

## Kiểm tra và tra cứu

```powershell
python tools/verify_baseline.py
python -m unittest discover -s gd2/tests -v
```

- Kế hoạch và checklist nghiệm thu nằm trong [kế hoạch GD2](docs/gd2/KE_HOACH_GD2.md).
- Kết quả chấm và phương pháp đo nằm trong [biên bản P6](docs/gd2/BIEN_BAN_P6.md).
- Cách dựng lại Word và PDF nằm trong [hướng dẫn báo cáo](gd2/report/README.md).
- Các bản nháp và lượt chạy đã thay thế có thể tra lại ở commit `17e25f9`. Hồ sơ chuẩn bị và bản lưu nguồn nằm trong [docs/audit](docs/audit/README.md).
