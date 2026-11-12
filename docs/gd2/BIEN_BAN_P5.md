# Biên bản P5 — bộ truy vấn chính thức

Chuẩn bị bắt đầu ngày 05/11/2026; chốt lúc **00:10:38 ngày 06/11/2026 (+07:00, Asia/Bangkok)**. **P5 đạt điều kiện hoàn thành; bước tiếp theo là P6.** Chưa chạy tìm kiếm hoặc chấm độ liên quan trên 12 truy vấn chính thức.

## Bộ đã chốt

| Mã | Nhóm nội dung | Tác phẩm nguồn | Phần trích | Số từ |
|---|---|---|---|---:|
| Q01 | Bí ẩn/tội phạm | [A Study in Scarlet — Arthur Conan Doyle](https://www.gutenberg.org/ebooks/244) | Phần I, chương III; hiện trường Lauriston Gardens | 991 |
| Q02 | Bí ẩn/tội phạm | [The Hound of the Baskervilles — Arthur Conan Doyle](https://www.gutenberg.org/ebooks/2852) | Chương 2; bản thảo và truyền thuyết gia đình | 1.018 |
| Q03 | Hàng hải | [Moby Dick; Or, The Whale — Herman Melville](https://www.gutenberg.org/ebooks/2701) | Chương 48: The First Lowering | 1.003 |
| Q04 | Hàng hải | [Two Years Before the Mast — Richard Henry Dana](https://www.gutenberg.org/ebooks/2055) | Chương III: Ship's Duties—Tropics | 997 |
| Q05 | Khoa học viễn tưởng | [The Time Machine — H. G. Wells](https://www.gutenberg.org/ebooks/35) | IV: Time Travelling | 994 |
| Q06 | Khoa học viễn tưởng | [The War of the Worlds — H. G. Wells](https://www.gutenberg.org/ebooks/36) | Quyển I, V: The Heat-Ray | 989 |
| Q07 | Tình cảm/xã hội | [Pride and Prejudice — Jane Austen](https://www.gutenberg.org/ebooks/1342) | Chương VI | 1.025 |
| Q08 | Tình cảm/xã hội | [Jane Eyre — Charlotte Brontë](https://www.gutenberg.org/ebooks/1260) | Chương IV | 1.008 |
| Q09 | Phiêu lưu | [Treasure Island — Robert Louis Stevenson](https://www.gutenberg.org/ebooks/120) | I: The Old Sea-dog at the Admiral Benbow | 965 |
| Q10 | Phiêu lưu | [The Count of Monte Cristo — Alexandre Dumas, Auguste Maquet](https://www.gutenberg.org/ebooks/1184) | Chương 21: The Island of Tiboulen | 998 |
| Q11 | Thiên nhiên/sinh vật | [Walden — Henry David Thoreau](https://www.gutenberg.org/ebooks/205) | The Ponds | 998 |
| Q12 | Thiên nhiên/sinh vật | [On the Origin of Species — Charles Darwin](https://www.gutenberg.org/ebooks/1228) | Chương III: Struggle for Existence | 1.025 |

Có **12 tác phẩm khác nhau**, sáu nhóm × hai truy vấn; tổng **12.011 từ**, nhỏ nhất **965**, lớn nhất **1.025**. Nhóm nội dung là quy ước tổ chức bộ thử, không phải nhãn đúng của kết quả hoặc cơ sở cộng điểm tìm kiếm. Không tuyên bố bộ này đại diện đủ 14 nhãn corpus.

Q01 được chọn trước làm ví dụ xuyên suốt vì mô tả hiện trường điều tra cụ thể. Q12 được chọn trước làm ca thăm dò: văn xuôi khoa học có thể đặt ra khó khăn cho kho thiên về truyện. Chưa có điểm truy hồi nên chưa gọi Q12 là ca kết quả kém; P6 sẽ ghi nhận thực tế và giữ đủ 12 truy vấn.

## Trích đoạn và nguồn

Toàn văn TXT chính thức được lưu tại `gd2/sources`, ngoài corpus. [Danh mục nguồn](../../gd2/sources/source_catalog.csv) chứa trang sách, URL TXT, hash, dung lượng và thời điểm tải. Ebook #205 chứa cả Walden và Civil Disobedience; Q11 được xác định thuộc Walden, phần The Ponds.

Mỗi đoạn bắt đầu tại một mốc văn bản duy nhất đã chọn theo nội dung. Kết thúc tại ranh giới đoạn văn gần 1.000 từ nhất trong khoảng 950–1.050; nếu không có thì dùng ranh giới câu. Số từ tính theo regex GD1 trước lọc stopword. Các TXT đầu ra là **chuỗi con liên tục, giữ nguyên ký tự và CRLF của nguồn đã giải mã UTF-8-sig**, không viết lại, ghép đoạn hoặc sửa câu. Manifest lưu offset ký tự bắt đầu từ 0, kết thúc không bao gồm ký tự cuối, cùng đoạn đầu/cuối để tìm lại.

Riêng Q07: đoạn ban đầu ở chương III chứa chú thích minh họa nên bị loại trước khi chạy tìm kiếm; chọn chương VI có văn xuôi liên tục. Lý do được ghi trong `p5_selection.json`. Đây là điều chỉnh theo tính hợp lệ của đoạn trích, không theo kết quả truy hồi.

## Kiểm tra ngoài kho

Đã thực hiện hai tầng trên toàn bộ 1.000 tệp:

1. So tên tác phẩm và các tên biến thể với metadata; rà các hàng có cùng/tương tự tên tác giả. Không có tên tác phẩm/biến thể khớp. Các sách khác của Doyle, Wells, Stevenson, Dumas và Thoreau được ghi rõ trong biên bản rà soát. Những khớp tên mơ hồ như Dana Winslow hoặc Howells không bị nhầm thành cùng tác giả.
2. Chuẩn hóa token đúng GD1, kiểm tra **mọi cửa sổ 12 token của truy vấn** với mọi vị trí trong corpus; đồng thời lấy **mốc 30 token, bước 30 trên toàn bộ phần thân mỗi ebook** rồi so với mọi vị trí corpus. Hash chỉ dùng tìm ứng viên, mọi khớp đều phải so lại token thật.

Kết quả: **0 khớp tên biến thể, 0 cửa sổ truy vấn trùng, 0 mốc toàn văn nguồn trùng**, ở cả 12 truy vấn. Lưới mốc 30 token bắt được mọi đoạn trùng nguyên chuỗi token dài từ 59 token trở lên trong phần thân nguồn, kể cả khi nằm trong một tuyển tập hoặc tệp khác tên. Phép kiểm tra sâu đã được chạy lại thành công sau khi khóa.

Các bằng chứng này hỗ trợ kết luận ngoài kho cho bộ đã chọn. Chúng không chứng minh tuyệt đối việc vắng mặt ở mọi bản dịch, diễn đạt lại hoặc ấn bản có chỉnh sửa; không suy rộng thành đã xác minh toàn bộ metadata corpus. Người rà soát ghi trong audit là Codex, không gán việc này cho hai thành viên nhóm.

## Khóa bộ thử và tiêu chí chấm

- [12 TXT và manifest](../../gd2/queries/query_manifest.csv).
- [Bằng chứng đối chiếu ngoài kho](../../gd2/queries/outside_corpus_audit.json).
- [Khóa bộ truy vấn](../../gd2/queries/queries.lock.json): hash của **36 tệp**, gồm 12 truy vấn, 12 nguồn, manifest, audit, quy tắc chọn/chấm, mã chuẩn bị/kiểm tra và tham chiếu dữ liệu liên quan.
- [Quy tắc đánh giá chốt trước truy hồi](../../gd2/queries/evaluation_protocol.json): mức 0/1/2; chỉ mức 2 được tính liên quan; P@3 = số kết quả mức 2 / 3; lấy trung bình trên 12 truy vấn. Hai thành viên chấm độc lập và lưu bằng chứng, điểm ban đầu, kết quả thống nhất. Chưa có phiếu chấm hoặc chỉ số chất lượng được điền.

Chương trình chuẩn bị/kiểm tra P5 không gọi search hay tính cosine. Bộ kiểm thử phần mềm có chạy search trên dữ liệu giả trong thư mục tạm để kiểm tra hồi quy; không dùng 12 TXT chính thức. Các TXT kỹ thuật ở P4 vẫn là bộ riêng.

## Kiểm chứng và dùng tiếp

**22/22 kiểm thử đạt**, gồm bốn kiểm thử mới cho trích liên tục, giữ nguyên dấu nháy/CRLF, loại mốc mơ hồ hoặc chú thích minh họa, hash cửa sổ và phát hiện đoạn trùng. Kiểm tra 36 hash, trích lại từ nguồn, sáu nhóm, số từ, baseline và kiểm tra sâu ngoài kho đều đạt. Corpus, CSDL và đặc trưng P2–P4 được giữ nguyên.

```powershell
python -m gd2.src.verify_queries
python -m gd2.src.verify_queries --deep
```

`prepare_queries` chỉ tạo bản nháp cần rà soát, không tự xác nhận ngoài kho hoặc ghi đè bộ đã chốt. Để tái tạo bản nháp từ nguồn đang lưu: `python -m gd2.src.prepare_queries --out gd2/artifacts/p5_reextract`. Không thay bộ đã khóa sau khi xem kết quả để làm đẹp điểm.

P6 tiếp theo chạy cả 12 TXT trong một lô, xuất trace Q01, chấm 36 cặp Top-3 và đo hiệu năng. Bộ truy vấn đủ điều kiện chuyển bước; chất lượng truy hồi phải chờ thực nghiệm P6.
