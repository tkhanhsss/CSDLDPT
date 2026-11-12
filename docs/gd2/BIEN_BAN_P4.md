# Biên bản P4 — tìm kiếm và xuất trace

Ngày thực hiện: 04/11/2026, Asia/Bangkok. **P4 đã đạt điều kiện hoàn thành; bước tiếp theo là P5.** Dùng CSDL schema v4, build `gd2-p3-0274798c40134e5e91eb3452500cda71`. Corpus, CSDL và artifact P2 không bị sửa bởi quá trình tìm kiếm.

## Chức năng đã có

`gd2/src/search.py` nạp SQLite một lần cho mỗi lô một hoặc nhiều TXT. Tokenizer dùng chung với P2; vocabulary và IDF đọc từ CSDL. Đếm stem, bỏ term ngoài vocabulary, tính log TF × IDF và L2; không fit lại trên truy vấn. Tính toàn bộ 1.000 điểm bằng Xqᵀ, xếp giảm dần và phá hòa theo filename.

Mỗi truy vấn có thư mục Q01, Q02… riêng, `results.json`, `results.csv` và ba bản sao TXT khi vector khác 0. Ba tệp nguồn được kiểm tra hash trước khi công bố; sai hash hoặc lỗi xuất khiến truy vấn được báo lỗi, không công bố các bản sao dở dang. Nhãn và metadata chỉ hiển thị.

`--trace` xuất:

- `preprocess.csv`: nguyên dạng token, vị trí trong chuỗi, token chuẩn hóa, base, giữ/bỏ và stem. Vị trí là chỉ số ký tự bắt đầu từ 0, kết thúc không bao gồm ký tự ở chỉ số cuối.
- `query_terms.csv`: count, TF, df/IDF của kho, trọng số trước/sau L2, term ngoài vocabulary.
- `all_scores.csv`: đủ 1.000 điểm theo thứ hạng.
- `rank1_contributions.csv` đến `rank3_contributions.csv`: toàn bộ đóng góp term chung.
- `trace_summary.json`: norm trước L2, tổng đóng góp, sai số so với cosine.

Luồng mặc định không xuất trace. `query_manifest.csv` ánh xạ mã chạy tới đường dẫn đầu vào; `run_metadata.json` ghi build ID, thời gian nạp riêng, thời gian cả lô và hash mã xử lý. Mã Q01… ở đây chỉ là mã trong lần chạy, không tự xác nhận truy vấn thuộc bộ thử chính thức.

## Kiểm chứng thực chạy

**18/18 kiểm thử đạt:** 11 kiểm thử P2–P3 và 7 kiểm thử P4. Bao gồm transform với lặp từ/OOV/dấu nháy/stopword, phá hòa và điểm 0, một lần nạp cho cả lô, đầu vào trùng basename, rỗng/sai mã hóa/không có token/không tồn tại, tiếp tục sau truy vấn lỗi, hash TXT, không xuất tệp dở dang, từ chối ghi đè, CSDL lỗi, trace tùy chọn và nguyên dạng/vị trí token.

Chạy trên CSDL thật tại [bộ bằng chứng cuối](../../gd2/artifacts/p4_final/verification.json). Bộ đối chiếu dùng CountVectorizer với vocabulary cố định và TfidfTransformer học IDF từ count **của corpus P2**, sau đó transform truy vấn. Đây là mã kiểm chứng riêng; luồng search không đọc NPZ và không fit.

| Kiểm tra | Kết quả |
|---|---|
| Hai truy vấn kỹ thuật có vector và một ca vector rỗng | Khớp trạng thái dự kiến |
| Vector truy vấn so với tham chiếu scikit-learn | Sai khác tối đa 0 |
| Toàn bộ 1.000 điểm của từng ca hợp lệ | Sai khác tối đa 0 |
| Thứ tự toàn bộ điểm và Top-3 | Khớp tham chiếu |
| Sáu TXT trả về cho hai truy vấn có vector | Hash khớp corpus |
| Tổng đóng góp term so với cosine | Sai số tối đa 1,3877787807814457 × 10⁻¹⁷ |
| Ca không có raw token | Báo lỗi; không trả TXT |
| CLI mặc định không trace | Thành công, mã thoát 0, trả ba TXT |

Bộ bằng chứng gồm câu hàng hải tự viết, một đoạn lấy từ `book_0001.txt` để kiểm tra kỹ thuật, một chuỗi stopword và một chuỗi chỉ có số/ký hiệu. **Không dùng các đầu vào này làm bộ truy vấn P5, không suy ra P@3 hoặc chất lượng tìm kiếm.** Đoạn tự truy hồi đứng đầu với `book_0001.txt` là phép kiểm tra hành vi, không phải bằng chứng về tác phẩm ngoài kho.

Lô kiểm chứng cố ý chứa ca lỗi nên `batch/run_metadata.json` có mã thoát 1; `verification.json` vẫn ghi `passed` vì đây là kết quả mong đợi. Lệnh CLI độc lập ở `gd2/results/p4_cli_smoke` có mã thoát 0. Thư mục `gd2/artifacts/p4` là lần chạy kỹ thuật trước khi bổ sung cột nguyên dạng/vị trí token; dùng `p4_final` cho biên bản hiện hành.

## Thời gian

Lô bốn đầu vào có trace: nạp kho 3,260 giây; toàn lô 3,359 giây. Hai đầu vào có vector mất lần lượt khoảng 0,025 và 0,039 giây từ lúc đọc truy vấn tới trước ghi báo cáo, có tính việc xuất trace và TXT. Đây là một lần chạy kiểm chứng, không phải thống kê hiệu năng P6. JSON lưu số đo đầy đủ và tách transform, tính điểm, xếp hạng.

## Cách chạy

Từ thư mục gốc, chọn thư mục đầu ra mới:

```powershell
python -m gd2.src.search --query gd2/artifacts/p4_final/inputs/technical_maritime.txt --out gd2/results/demo_new --trace
python -m gd2.src.search --query first.txt second.txt --out gd2/results/batch_new
```

Kiểm thử và tái lập kiểm chứng vào thư mục mới:

```powershell
python -m unittest discover -s gd2/tests -v
python -m gd2.src.verify_search --out gd2/artifacts/p4_recheck
```

Đặc tả đầy đủ: [HOP_DONG_P4.md](HOP_DONG_P4.md). P5 tiếp theo chọn/chốt 12 đoạn từ tác phẩm ngoài kho, trước khi xem kết quả để đánh giá P6.
