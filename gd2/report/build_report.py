"""Build the consolidated coursework report from frozen evidence and the retained GD1 DOCX.
Run with the bundled document runtime, not the pinned retrieval runtime.
"""
from pathlib import Path
from copy import deepcopy
import csv
import hashlib
import json
import math
import sqlite3
import textwrap
import zipfile

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont
from lxml import etree
from docx.enum.text import WD_BREAK

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'gd2/report'
WORK = OUT / 'work'
ASSETS = OUT / 'assets'
SOURCE = ROOT / 'docs/gd1/GD1-CSDLDPT-23-03.docx'
FINAL = OUT / 'GD1-GD2-CSDLDPT-23-03.docx'
EVAL = ROOT / 'gd2/evaluation/p6'
RUN = ROOT / 'gd2/results/p6_official'


def js(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def csvrows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def writej(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def fmt(value, places=6):
    return f'{float(value):.{places}f}'.replace('.', ',')


def diagram(name, boxes, arrows, width=2200, height=1500):
    im = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(im)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 36)
    titlefont = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 40)
    small = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 31)
    for x1,y1,x2,y2,title,body in boxes:
        draw.rounded_rectangle((x1,y1,x2,y2), radius=14, fill='#F2F6FA', outline='#294B64', width=4)
        draw.text(((x1+x2)/2,y1+38), title, font=titlefont, anchor='mm', fill='#102838')
        lines=body.split('\n')
        for k,line in enumerate(lines): draw.text(((x1+x2)/2,y1+103+k*48),line,font=font,anchor='mm',fill='black')
    for x1,y1,x2,y2,label in arrows:
        draw.line((x1,y1,x2,y2), fill='#294B64', width=5)
        angle=math.atan2(y2-y1,x2-x1)
        points=[(x2,y2),(x2-23*math.cos(angle-.4),y2-23*math.sin(angle-.4)),(x2-23*math.cos(angle+.4),y2-23*math.sin(angle+.4))]
        draw.polygon(points,fill='#294B64')
        if label: draw.text(((x1+x2)/2+12,(y1+y2)/2-48),label,font=small,fill='black')
    im.save(ASSETS/name)


def make_diagrams():
    diagram('fig5_erd.png',[
        (60,70,680,330,'labels','PK label_code\ndisplay_name\n14 dòng'),
        (60,500,680,990,'documents','PK doc_id; UNIQUE filename\nrelative_path; raw_sha256\nword_count; FK label_code\ntitle; author_display; l2_raw\n1.000 dòng'),
        (860,500,1490,990,'document_terms','PK (doc_id, term_id)\nFK doc_id → documents\nFK term_id → terms\nterm_count; weight\n1.926.766 dòng'),
        (1660,500,2160,890,'terms','PK term_id\nUNIQUE term_text\ndf; idf\n34.416 dòng'),
        (1040,70,2110,330,'build_info','Một dòng mô tả bản dựng\nCấu hình, phiên bản, hash, kích thước\nĐộc lập với chuỗi khóa ngoại')
    ],[(370,330,370,500,'1 : N'),(680,740,860,740,'1 : N'),(1660,740,1490,740,'1 : N')],height=1080)
    diagram('fig6_build.png',[
        (40,60,690,300,'Kho và cấu hình GD1','1.000 TXT + metadata + nhãn\nKiểm tra hash và ánh xạ'),
        (790,60,1440,300,'Tiền xử lý và đếm','Chuẩn hóa → lọc → Porter\nCount và df trên toàn kho'),
        (1540,60,2180,300,'Đặc trưng cố định','3 ≤ df ≤ 600; TF log; IDF\nChuẩn hóa L2 → X và vocabulary'),
        (1540,470,2180,740,'Nhập SQLite','Giao dịch + khóa + chỉ mục\nLưu đủ mọi trọng số khác 0\nTrạng thái building'),
        (790,470,1440,740,'Kiểm tra và nạp lại','Integrity; FK; df; norm\nSo sánh count, IDF và X\nSai lệch so với P2 bằng 0'),
        (40,470,690,740,'Bản dựng sẵn sàng','Trạng thái complete\nĐóng băng build_id và hash\nChỉ đọc khi tìm kiếm')
    ],[(690,180,790,180,''),(1440,180,1540,180,''),(1860,300,1860,470,''),(1540,600,1440,600,''),(790,600,690,600,'')],height=820)
    diagram('fig7_search.png',[
        (50,50,910,300,'SQLite → chỉ mục trong RAM','Nạp X 1.000 × 34.416\nVocabulary, IDF và metadata'),
        (1210,50,2130,300,'Đầu vào TXT ngoài kho','Đọc UTF-8-sig → tiền xử lý GD1\nĐếm stem; bỏ term ngoài vocabulary'),
        (1210,450,2130,710,'Vector truy vấn q','TF log × IDF đã lưu\nChuẩn hóa L2 nếu norm khác 0'),
        (50,450,910,710,'Tính điểm và xếp hạng','q khác 0: s = Xqᵀ, đủ 1.000 điểm\nGiảm dần; hòa điểm theo filename'),
        (1210,890,2130,1140,'q không có đặc trưng','Trạng thái empty_vector\nKhông trả Top-3 tùy ý'),
        (50,890,910,1190,'Đầu ra và giải thích','Top-3 CSV/JSON + ba bản sao TXT\nKiểm tra hash trước khi sao chép\nTrace và tổng đóng góp term')
    ],[(480,300,480,450,''),(1670,300,1670,450,''),(1210,580,910,580,'q ≠ 0'),(480,710,480,890,''),(1670,710,1670,890,'q = 0')],height=1270)


class Report:
    def __init__(self):
        self.d=Document(SOURCE)
        self.table_number=5
        self.figure_number=4
        self.captions=[]
        for name,size,bold,align in [('P7 Body',13,False,WD_ALIGN_PARAGRAPH.JUSTIFY),
            ('P7 Chapter',14,True,WD_ALIGN_PARAGRAPH.CENTER),('P7 Section',14,True,WD_ALIGN_PARAGRAPH.LEFT),
            ('P7 Subsection',13,True,WD_ALIGN_PARAGRAPH.LEFT),('P7 Front',14,True,WD_ALIGN_PARAGRAPH.CENTER),
            ('P7 TOC title',14,True,WD_ALIGN_PARAGRAPH.CENTER),('P7 Table',12,False,WD_ALIGN_PARAGRAPH.CENTER),
            ('P7 Figure',12,False,WD_ALIGN_PARAGRAPH.CENTER),('P7 Small',11,False,WD_ALIGN_PARAGRAPH.LEFT),
            ('P7 Code',9.5,False,WD_ALIGN_PARAGRAPH.LEFT)]:
            s=self.d.styles.add_style(name,WD_STYLE_TYPE.PARAGRAPH)
            s.base_style=self.d.styles['Normal']
            s.font.name='Consolas' if name=='P7 Code' else 'Times New Roman'
            s.font.size=Pt(size);s.font.bold=bold;s.font.color.rgb=RGBColor(0,0,0)
            pf=s.paragraph_format;pf.alignment=align;pf.space_after=Pt(6);pf.line_spacing=1.12
            pf.first_line_indent=Cm(.75) if name=='P7 Body' else Cm(0)
            pf.keep_with_next=name in ['P7 Chapter','P7 Section','P7 Subsection','P7 Front','P7 TOC title','P7 Table']
            pf.widow_control=True
            if name in ['P7 Chapter','P7 Front']:pf.page_break_before=True
            if name in ['P7 Chapter','P7 Section','P7 Subsection']:
                level=OxmlElement('w:outlineLvl');level.set(qn('w:val'),str({'P7 Chapter':0,'P7 Section':1,'P7 Subsection':2}[name]));s.element.get_or_add_pPr().append(level)
        # Keep every original body element in chapters 1-2, including equations and relationships.
        body=self.d.element.body
        start=self.d.paragraphs[32]._p; chapter=self.d.paragraphs[87]._p
        i,j=list(body).index(start),list(body).index(chapter)
        for e in list(body)[i:j]:body.remove(e)
        self.chapter_start=chapter
        self.original_body=[deepcopy(e) for e in list(body)[list(body).index(chapter):-1]]
        self.d.paragraphs[14].text='BÁO CÁO HỢP NHẤT GIAI ĐOẠN 1 VÀ 2'
        self.d.paragraphs[14].alignment=WD_ALIGN_PARAGRAPH.CENTER
        for run in self.d.paragraphs[14].runs:run.font.size=Pt(13);run.bold=True
        self.d.core_properties.title='Xây dựng hệ CSDL lưu trữ và tìm kiếm văn bản'
        self.d.core_properties.author='Lương Tùng Khánh; Hoàng Minh Trọng'
        self.d.core_properties.subject='Báo cáo hợp nhất giai đoạn 1 và 2, nhóm 23 lớp 03'
        for name in ['toc 1', 'toc 2']:
            s=self.d.styles[name]
            s.font.size=Pt(12)
            s.paragraph_format.space_before=Pt(0)
            s.paragraph_format.space_after=Pt(2)
            s.paragraph_format.line_spacing=1.0

    def p(self,text='',style='P7 Body',bold=False):
        p=self.d.add_paragraph(text,style=style)
        if bold:
            for r in p.runs:r.bold=True
        return p

    def h(self,text,level=2,newpage=False):
        p=self.p(text,['P7 Chapter','P7 Section','P7 Subsection'][level-1])
        # Let sections flow naturally; only chapters and appendices force a new page.
        return p

    def field(self,instruction):
        p=self.p('',style='P7 Small')
        for typ in ['begin','instruction','separate','end']:
            run=OxmlElement('w:r')
            if typ=='instruction':
                el=OxmlElement('w:instrText');el.set(qn('xml:space'),'preserve');el.text=instruction
            else:el=OxmlElement('w:fldChar');el.set(qn('w:fldCharType'),typ)
            run.append(el);p._p.append(run)
        return p

    def table(self,title,headers,rows,widths,size=11,number=True):
        if number:
            self.table_number+=1
            caption=f'Bảng {self.table_number}. {title}'
            self.p(caption,'P7 Table');self.captions.append(caption)
        t=self.d.add_table(rows=1,cols=len(headers));t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
        pr=t._tbl.tblPr
        borders=OxmlElement('w:tblBorders')
        for edge in ['top','left','bottom','right','insideH','insideV']:
            v=OxmlElement('w:'+edge);v.set(qn('w:val'),'single');v.set(qn('w:sz'),'4');v.set(qn('w:color'),'D9D9D9');borders.append(v)
        pr.append(borders)
        for col,w in zip(t.columns,widths):col.width=Cm(w)
        for k,rowvalues in enumerate([headers]+list(rows)):
            row=t.rows[0] if k==0 else t.add_row()
            cant=OxmlElement('w:cantSplit');row._tr.get_or_add_trPr().append(cant)
            if k==0:
                repeat=OxmlElement('w:tblHeader');row._tr.get_or_add_trPr().append(repeat)
            for cell,value,w in zip(row.cells,rowvalues,widths):
                cell.width=Cm(w);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
                cp=cell._tc.get_or_add_tcPr(); margins=OxmlElement('w:tcMar')
                for edge in ['top','bottom','left','right']:
                    m=OxmlElement('w:'+edge);m.set(qn('w:w'),'70');m.set(qn('w:type'),'dxa');margins.append(m)
                cp.append(margins)
                if k==0:
                    shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'E7EEF4');cp.append(shade)
                p=cell.paragraphs[0];p.style=self.d.styles['P7 Small'];p.paragraph_format.space_after=Pt(0);p.paragraph_format.line_spacing=1.03;p.paragraph_format.keep_with_next=k==0
                p.alignment=WD_ALIGN_PARAGRAPH.CENTER if w<2.6 else WD_ALIGN_PARAGRAPH.LEFT
                r=p.add_run(str(value));r.font.size=Pt(size);r.bold=k==0
        self.p('','P7 Small').paragraph_format.space_after=Pt(0)
        return t

    def figure(self,name,title,width=16.3):
        p=self.p('','P7 Small');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.keep_with_next=True
        p.add_run().add_picture(str(ASSETS/name),width=Cm(width))
        self.figure_number+=1;caption=f'Hình {self.figure_number} - {title}'
        self.p(caption,'P7 Figure');self.captions.append(caption)

    def code(self,text):
        lines=text.splitlines()
        for i,line in enumerate(lines):
            p=self.p(line,'P7 Code');p.paragraph_format.space_after=Pt(0)
            p.paragraph_format.keep_with_next=len(lines)<12 and i<len(lines)-1
        self.p('','P7 Small')

    def front(self):
        body=self.d.element.body; existing=set(body)
        self.p('MỤC LỤC','P7 TOC title')
        self.field(' TOC \\h \\z \\t "CTDT-H1,1,CTDT-H2,2,P7 Chapter,1,P7 Section,2,P7 Front,1" ')
        self.p('DANH MỤC CÁC HÌNH VẼ','P7 Front')
        self.field(' TOC \\h \\z \\t "CTDT-Hinh,1,P7 Figure,1" ')
        self.p('DANH MỤC CÁC BẢNG BIỂU','P7 Front')
        self.field(' TOC \\h \\z \\t "CTDT-Bang,1,P7 Table,1" ')
        self.p('DANH MỤC CÁC TỪ VIẾT TẮT','P7 Front')
        self.table('', ['Viết tắt','Thuật ngữ','Ý nghĩa sử dụng trong báo cáo'],[
            ['BOM','Byte Order Mark','Dấu nhận diện thứ tự byte; khác với tên bộ giải mã.'],
            ['CLI','Command Line Interface','Giao diện dòng lệnh của chương trình tìm kiếm.'],
            ['CSDL','Database','Cơ sở dữ liệu.'],['CSR','Compressed Sparse Row','Biểu diễn ma trận thưa theo hàng.'],
            ['df','Document Frequency','Số tài liệu chứa một term.'],['IDF','Inverse Document Frequency','Trọng số nghịch đảo tần suất tài liệu.'],
            ['L2','Euclidean norm','Chuẩn Euclid dùng chuẩn hóa vector.'],['NLTK','Natural Language Toolkit','Thư viện dùng Porter Stemmer.'],
            ['nnz','Number of Nonzeros','Số phần tử khác 0 trong ma trận/vector.'],['OOV','Out of Vocabulary','Stem nằm ngoài vocabulary cuối của kho.'],
            ['P@3','Precision at 3','Tỷ lệ kết quả mức 2 trong ba kết quả đầu.'],['SQL','Structured Query Language','Ngôn ngữ định nghĩa và truy vấn dữ liệu.'],
            ['TF','Term Frequency','Tần suất term, có điều chỉnh logarit.'],['TF-IDF','Term Frequency–Inverse Document Frequency','Trọng số term trong mô hình vector.'],
            ['TXT','Plain Text','Tệp văn bản thuần.'],['UTF-8','Unicode Transformation Format','Mã hóa Unicode; đọc bằng utf-8-sig.']], [1.7,6.0,9.0],size=11,number=False)
        self.p('MỞ ĐẦU','P7 Front')
        for text in [
            'Bài tập lớn xây dựng một hệ cơ sở dữ liệu lưu trữ đặc trưng và tìm kiếm văn bản tiếng Anh. Đầu vào là tệp truy vấn khoảng 1.000 từ từ tác phẩm ngoài kho; đầu ra là ba tài liệu có điểm cosine cao nhất, kèm tên tác phẩm, tác giả, điểm và ba bản sao TXT có thể mở để kiểm tra. Hệ thống làm việc trên bộ 1.000 tệp được thu thập, làm sạch và thống kê ở giai đoạn 1.',
            'Báo cáo hợp nhất kết quả giai đoạn 1 và 2. Phương pháp sử dụng chuẩn hóa dấu nháy và chữ thường, tách token, lọc từ dừng, Porter stemming, TF-IDF với TF logarit và IDF làm trơn, chuẩn hóa L2 rồi xếp hạng bằng cosine. Nhãn chủ đề và metadata phục vụ mô tả, không tham gia trọng số hay lọc ứng viên. Mỗi tệp vẫn là một đơn vị biểu diễn và tìm kiếm.',
            'Ở giai đoạn 2, nhóm đã tái lập ma trận 1.000 × 34.416 với 1.926.766 trọng số khác 0 và lưu đầy đủ vào SQLite. Chương trình dòng lệnh nạp đặc trưng từ CSDL, xử lý một hoặc nhiều truy vấn và xuất kết quả cùng trace. Bộ đánh giá gồm 12 đoạn từ 12 tác phẩm ngoài kho, được chốt trước khi xem kết quả; hai thành viên chấm độc lập 36 cặp Top-3 rồi thống nhất điểm cuối.',
            'Kết quả kiểm chứng cho thấy CSDL và phép tính điểm thực hiện đúng mô hình đã chọn. Mean P@3 đạt 11,11% khi chỉ mức liên quan rõ được tính là đúng; 3/12 truy vấn có ít nhất một kết quả mức 2. Trung vị xử lý khi chỉ mục đã ở RAM là 6,94 ms trên máy thử. Các số liệu này cho thấy cần phân biệt tính đúng kỹ thuật với chất lượng truy hồi trên bộ thử nhỏ.',
            'Báo cáo gồm bốn chương. Chương 1 mô tả kho và các thống kê; Chương 2 trình bày nguyên lý đặc trưng và xếp hạng. Chương 3 hiện thực hóa CSDL đặc trưng và kiểm chứng việc lưu–nạp. Chương 4 trình bày chương trình tìm kiếm, dữ liệu trung gian của Q01, kết quả toàn bộ bộ thử, đánh giá liên quan và hiệu năng. Phần làm rõ đơn vị tệp và mã hóa được đặt ở đầu Chương 3. Giao diện demo thuộc giai đoạn 3 và chưa được coi là kết quả của báo cáo này.'
        ]:self.p(text)
        self.p('', 'P7 Small').add_run().add_break(WD_BREAK.PAGE)
        created=[e for e in list(body) if e not in existing]
        for e in created:
            body.remove(e);self.chapter_start.addprevious(e)


def build():
    OUT.mkdir(exist_ok=True);WORK.mkdir(exist_ok=True);ASSETS.mkdir(exist_ok=True)
    with zipfile.ZipFile(SOURCE) as z:
        writej(WORK/'source_inventory.json',{'source':str(SOURCE),'sha256':digest(SOURCE),'parts':{n:{'bytes':len(z.read(n)),'sha256':hashlib.sha256(z.read(n)).hexdigest()} for n in z.namelist()}})
    p2=js(ROOT/'gd2/artifacts/p2/verification.json');p3=js(ROOT/'gd2/database/documents.verification.json')
    p6=js(ROOT/'gd2/artifacts/p6/verification.json');metrics=js(EVAL/'grading_final/metrics.json');perf=js(EVAL/'performance_final/performance.json')
    assert p6['status']=='complete' and metrics['status']=='complete'
    for path,hashvalue in p6['files_sha256'].items():
        # Markdown records capture the historical P6 state; P7 updates progress documents.
        # Computational inputs, frozen evidence and code must still match the P6 snapshot.
        if not path.endswith('.md'):
            assert digest(ROOT/path)==hashvalue, f'P6 input changed: {path}'
    manifest=csvrows(ROOT/'gd2/queries/query_manifest.csv')
    results={r['query_id']:js(RUN/r['query_id']/'results.json') for r in manifest}
    judgments={r['pair_id']:r for r in csvrows(EVAL/'consensus.csv')}
    mapping=csvrows(EVAL/'pair_map.csv'); pairbydoc={(r['query_id'],r['filename']):r for r in mapping}
    A={r['pair_id']:r for r in csvrows(EVAL/'reviewer_A.csv')};B={r['pair_id']:r for r in csvrows(EVAL/'reviewer_B.csv')}
    db=sqlite3.connect((ROOT/'gd2/database/documents.sqlite').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    make_diagrams();r=Report();r.front()
    r.h('CHƯƠNG 3. XÂY DỰNG CSDL LƯU TRỮ ĐẶC TRƯNG VĂN BẢN',1)
    r.h('3.1 Kế thừa dữ liệu và làm rõ phạm vi')
    r.p('Giai đoạn 2 sử dụng nguyên bộ 1.000 TXT và quy trình Chương 1–2. Không chia kho thành tập huấn luyện/kiểm tra, không tách tài liệu thành đoạn và không đưa nguồn truy vấn vào bước fit. Bản kê SHA256 xác nhận nội dung kho, nhãn, mã và kết quả GD1 giữ nguyên. Đặc trưng mới được dựng để hiện thực hóa phương pháp đã mô tả, không thay thuật toán nhằm tăng điểm thử nghiệm.')
    r.table('Đối chiếu nội dung kế thừa và phần hiện thực hóa',['Nội dung GD1','Hiện thực hóa ở GD2','Bằng chứng'],[
        ['1.000 tệp, 34.344.608 từ','Giữ nội dung và filename','Manifest/hash; thống kê đếm từ'],
        ['Tiền xử lý ở Bảng 4','Module preprocess.py dùng chung','Cấu hình và trace token Q01'],
        ['TF-IDF và L2 ở Bảng 5','Lưu vocabulary, IDF, count, trọng số','1.000 × 34.416; 1.926.766 dòng'],
        ['Cosine và Top-3 ở mục 2.4','Nhân Xqᵀ và xuất ba TXT','12.000 điểm và 36 bản sao đã kiểm tra'],
        ['Nhãn và tên tác phẩm','Nối metadata theo filename','1.000 ánh xạ; không tham gia điểm']], [5,6.1,5.6])
    r.p('Đơn vị dữ liệu là tệp, không đồng nhất với tác phẩm độc lập hoàn chỉnh. Hai tệp book_0637.txt và book_0797.txt lần lượt là Grania Tập I (Phần I–II) và Tập II (Phần III–IV); book_0927.txt và book_0988.txt là Tập 1 và Tập 2 của The Earl’s Promise. Tên tập đã được bổ sung để phân biệt; không gộp hay xóa tệp. Đối chiếu Grania giữ ghi nhận sai khác ba token tiêu đề PART II APRIL ở book_0637.txt, không coi là khớp toàn văn tuyệt đối. Nguồn đối chiếu là Gutenberg #58443, #70755 và #70756 [5].')
    r.p('Cụm “UTF-8 có BOM” tại mục 1.1 cần hiểu là bộ giải mã utf-8-sig đã đọc được tệp; kiểm tra byte thực tế cho thấy 0/1.000 tệp có BOM. Nguồn từ dừng là ENGLISH_STOP_WORDS của scikit-learn cộng EXTRA_STOP của mã GD1; NLTK dùng Porter Stemmer. Những làm rõ này không làm thay đổi nội dung, tokenizer, công thức hay số liệu của Chương 1–2.')
    r.h('3.2 Mục tiêu lưu trữ và mô hình quan hệ',newpage=True)
    r.p('CSDL lưu các đặc trưng thực sự cần cho tìm kiếm, gồm định danh tài liệu, từ vựng, df, IDF và toàn bộ trọng số khác 0. Các TXT được giữ trên đĩa, liên kết bằng đường dẫn tương đối và SHA256. Khi chạy, chương trình nạp CSDL vào ma trận CSR trong RAM; không dùng danh sách năm từ nổi bật thay cho vector đầy đủ.')
    r.figure('fig5_erd.png','Mô hình quan hệ của CSDL đặc trưng')
    r.table('Các bảng và quy mô của CSDL',['Bảng','Vai trò','Số dòng'],[
        ['build_info','Bản dựng, cấu hình, phiên bản, hash','1'],['labels','Danh mục nhãn mô tả kế thừa','14'],
        ['documents','Metadata, đường dẫn, hash, độ dài, norm','1.000'],['terms','Stem, df và IDF của kho','34.416'],
        ['document_terms','Count và trọng số của cặp doc–term','1.926.766']], [3.5,10.7,2.5])
    r.p('SQLite phù hợp với hệ thống chạy cục bộ vì có thể chuyển cùng dữ liệu dưới dạng một tệp CSDL. Bản đang dùng là SQLite 3.40.1, schema phiên bản 4. Các bảng dùng STRICT để kiểm tra kiểu dữ liệu; foreign_keys được bật trên từng kết nối trước giao dịch [2, 3]. Đây là lựa chọn triển khai theo phạm vi bài tập, không phải kết luận so sánh hiệu năng với hệ quản trị khác.')
    r.h('3.3 Trường dữ liệu và ràng buộc')
    r.table('Từ điển dữ liệu phục vụ tìm kiếm',['Bảng và trường','Kiểu và ràng buộc','Ý nghĩa'],[
        ['documents.doc_id','INTEGER, PK, > 0','ID hàng của tài liệu'],['filename; relative_path','TEXT, NOT NULL, UNIQUE','Tên tệp và đường dẫn nội dung'],
        ['raw_sha256; word_count','TEXT 64 ký tự; INTEGER > 0','Kiểm tra bản sao và số từ'],['label_code','TEXT, FK → labels','Nhãn mô tả'],
        ['title; author_display','TEXT, NOT NULL, không rỗng','Tên sách và tác giả theo bảng ánh xạ'],['l2_raw','REAL, hữu hạn, ≥ 0','Chuẩn trước khi chia L2'],
        ['terms.term_id; term_text','INTEGER PK; TEXT UNIQUE','Ánh xạ cột vector sang stem'],['terms.df; terms.idf','INTEGER 3–600; REAL ≥ 1','Tham số thống kê trên 1.000 tệp'],
        ['document_terms.doc_id; term_id','Hai FK, PK ghép','Một tọa độ khác 0 của X'],['term_count; weight','INTEGER > 0; REAL (0; 1+10⁻¹⁰]','Tần suất stem và trọng số sau L2'],
        ['labels.label_code; display_name','TEXT PK; TEXT không rỗng','14 mã và tên hiển thị GD1'],
        ['build_info','Một dòng; status building/complete','Quy mô, cấu hình, phiên bản, hash']], [5.4,5.3,6.0],size=10.5)
    r.p('Bảng documents có đúng chín trường như trên. Nhãn, tên sách và tác giả chỉ dùng để liên kết và hiển thị. Bảng document_terms dùng khóa ghép (doc_id, term_id), WITHOUT ROWID và chỉ mục theo term_id. Count là số lần stem xuất hiện sau tiền xử lý; weight đã đi qua TF log, IDF và chuẩn hóa, nên không được diễn giải như tần suất thô.')
    r.p('Tài liệu được sắp filename tăng dần; doc_id = chỉ số hàng + 1. Term được sắp theo chữ; term_id = chỉ số cột + 1. Khi nạp lại, truy vấn SQL chỉ rõ thứ tự ID. Không dựa vào thứ tự tự nhiên của bảng để ghép hàng/cột, vì sai ánh xạ sẽ làm sai cả điểm lẫn tệp trả về.')
    r.h('3.4 Quy trình dựng và công bố CSDL',newpage=True)
    r.figure('fig6_build.png','Quy trình dựng đặc trưng và công bố bản CSDL')
    r.p('Chương trình kiểm tra baseline và đọc 1.000 TXT theo thứ tự đã chốt. Sau tiền xử lý, CountVectorizer đếm unigram và lọc df trên toàn kho; ngưỡng giữ là 3 ≤ df ≤ 600, kể cả df = 600. TfidfTransformer áp dụng TF log, IDF làm trơn và L2 đúng Chương 2 [1]. Count, vocabulary, IDF, norm và X được kiểm tra rồi lưu làm tham chiếu ở bước dựng đặc trưng.')
    r.p('Bước dựng CSDL nối selected_stories.csv và labels.jsonl theo filename, kiểm tra đủ 1.000 ánh xạ, rồi nhập dữ liệu trong một giao dịch. Trạng thái building chỉ chuyển thành complete sau khi các kiểm tra đạt. Một tệp tạm được dùng để tránh công bố bản nhập dở; chương trình từ chối ghi đè đầu ra đã tồn tại. Thay đổi kho hoặc cấu hình cần một bản dựng mới để không trộn các không gian đặc trưng.')
    r.table('Số liệu của bản dựng đã kiểm chứng',['Chỉ tiêu','Giá trị'],[
        ['Số hàng × số cột X','1.000 × 34.416'],['Số phần tử khác 0','1.926.766'],['Mật độ X',fmt(1926766/(1000*34416)*100,4)+'%'],
        ['Dải df','3 đến 600'],['Dải IDF','1,510159844780013 đến 6,52246041819533'],['Số hàng vector rỗng','0'],
        ['Dung lượng SQLite','67.866.624 byte, khoảng 64,723 MiB'],['Kiểu trọng số trong xử lý','float64, không làm tròn trước lưu/tính điểm']], [7,9.7])
    r.h('3.5 Bản ghi và truy vấn SQL thực tế')
    sample=dict(db.execute("SELECT * FROM documents WHERE doc_id=733").fetchone())
    r.p('Tài liệu minh họa là book_0733.txt, THE CLUB OF QUEER TRADES của G. K. Chesterton, nhãn mystery_crime. Bản ghi có doc_id = 733, 44.404 từ, đường dẫn data/corpus/book_0733.txt và l2_raw = 241,65802198827006. Đây cũng là kết quả đầu của Q01, giúp đối chiếu từ lưu trữ đến trả tệp.')
    r.code('SELECT t.term_text, dt.term_count, t.df, t.idf, dt.weight\nFROM document_terms dt JOIN terms t USING (term_id)\nWHERE dt.doc_id = 733\nORDER BY dt.weight DESC, t.term_id LIMIT 8;')
    samples=[dict(x) for x in db.execute('SELECT t.term_text,dt.term_count,t.df,t.idf,dt.weight FROM document_terms dt JOIN terms t USING(term_id) WHERE dt.doc_id=733 ORDER BY dt.weight DESC,t.term_id LIMIT 8')]
    r.table('Tám term có trọng số lớn nhất của book_0733.txt',['Term','Count','df','IDF','Weight'],[[s['term_text'],s['term_count'],s['df'],fmt(s['idf']),fmt(s['weight'])] for s in samples],[4.7,2,2,4,4])
    r.p('Ví dụ basil có count = 228, df = 22. Tính lại (1 + ln 228) × 4,773260563386071 / 241,65802198827006 thu được 0,12699326795183496, trùng weight đã lưu. Term nổi bật trong tài liệu không nhất thiết đóng góp vào một truy vấn cụ thể: nếu term không thuộc q thì tích qⱼXᵢⱼ bằng 0.')
    r.code("SELECT COUNT(*) FROM document_terms;\n-- 1926766\nSELECT COUNT(*) FROM document_terms dt JOIN terms t\n  USING (term_id) WHERE t.term_text = 'gregson';\n-- 3, bằng terms.df của gregson\nPRAGMA integrity_check;       -- ok\nPRAGMA foreign_key_check;     -- không có dòng vi phạm")
    r.h('3.6 Kiểm chứng lưu nạp và khả năng tái lập')
    r.table('Kết quả kiểm chứng đặc trưng và CSDL',['Phép kiểm tra','Kết quả','Ý nghĩa'],[
        ['Integrity và khóa ngoại','ok; 0 vi phạm','CSDL hợp lệ về cấu trúc'],['df từ SQL so với terms.df','0 sai khác','Đếm theo số tài liệu đúng'],
        ['Count và trọng số đọc lại so với P2','Sai lệch lớn nhất 0','Lưu–nạp bảo toàn giá trị'],['IDF, df, l2_raw và ánh xạ','Khớp chính xác','Giữ cùng hệ tọa độ'],
        ['Sai số norm L2 lớn nhất','2,775558 × 10⁻¹⁵','Nhỏ hơn ngưỡng 10⁻¹⁰'],['Sai số công thức trọng số lớn nhất','3,885781 × 10⁻¹⁶','Phù hợp TF log, IDF và L2'],
        ['Top-5 term đối chiếu GD1','1.000/1.000 tệp khớp','Đối chiếu kết quả lịch sử']], [6.5,4.7,5.5])
    r.p('GD1 không lưu ma trận đầy đủ của lần chạy lịch sử. Vì vậy, đối chiếu lịch sử chỉ xác nhận số chiều và Top-5; phép so sánh toàn bộ vector là giữa lần dựng mới bằng mã GD2 và lần dựng độc lập dùng mã GD1 gốc. Sai lệch trọng số lớn nhất giữa hai lần dựng mới là 3,885781 × 10⁻¹⁶; IDF khớp. Không diễn giải kết quả này thành phục hồi từng bit của một ma trận lịch sử chưa được lưu.')
    r.p('Khi tìm kiếm, load_database mở SQLite chỉ đọc, nạp theo ID và kiểm tra nhẹ trạng thái, cấu hình, kích thước, ánh xạ và norm. Kiểm tra sâu SQL integrity, khóa, df và công thức nằm ở lệnh verify_database, không lặp lại trong mỗi truy vấn. Chương trình tìm kiếm không đọc ma trận NPZ; các tệp P2 chỉ là tham chiếu kiểm chứng.')

    r.h('CHƯƠNG 4. XÂY DỰNG VÀ ĐÁNH GIÁ HỆ THỐNG TÌM KIẾM VĂN BẢN',1)
    r.h('4.1 Bài toán và hợp đồng đầu vào đầu ra')
    r.p('Hệ thống nhận một hoặc nhiều tệp TXT tiếng Anh và một CSDL đã hoàn tất. Truy vấn chính thức là đoạn liên tục khoảng 1.000 từ từ tác phẩm không thuộc kho. Khi vector có đặc trưng, hệ thống xếp hạng toàn bộ 1.000 tệp và trả ba tài liệu đầu cùng metadata, cosine và ba bản sao nguyên byte. Tên truy vấn không được dùng làm đặc trưng.')
    r.code('python -m gd2.src.search --query gd2/queries/Q01.txt\n  --out gd2/results/run_new --trace')
    r.p('Lệnh trên được viết trên hai dòng để trình bày; khi chạy nhập trên một dòng. Có thể truyền nhiều đường dẫn sau --query để nạp kho một lần. Mỗi đầu vào nhận ID Q01, Q02… theo thứ tự đối số, nên bộ thử chính thức luôn truyền theo manifest Q01–Q12. Thư mục đích phải chưa tồn tại và nằm ngoài data/corpus.')
    r.table('Đầu ra cho một truy vấn',['Tệp hoặc thành phần','Nội dung'],[
        ['results.json; results.csv','Top-3, tên tệp, tên sách, tác giả, nhãn, điểm và trạng thái'],['rank1/2/3_book_xxxx.txt','Ba bản sao đúng TXT gốc, kiểm tra SHA256 trước khi xuất'],
        ['preprocess.csv; query_terms.csv','Token gốc, vị trí, quyết định lọc, stem, count và trọng số'],['all_scores.csv','Đủ 1.000 điểm và thứ hạng'],
        ['rankN_contributions.csv','Mọi term chung và tích trọng số của từng cặp'],['trace_summary.json; run_metadata.json','Sai số tổng đóng góp, build_id, hash nguồn và thời gian']], [6.5,10.2])
    r.p('Vector rỗng trả empty_vector và không sinh ba tệp tùy ý. Tệp trống, sai mã hóa, chỉ có ký tự không tạo token hoặc không đọc được được ghi là lỗi; lô vẫn tiếp tục các đầu vào còn lại. Nếu vector hợp lệ nhưng có kết quả điểm 0, chương trình vẫn tuân thủ Top-3 và ghi rõ zero_score; thứ tự các điểm bằng nhau được phá hòa theo filename tăng dần.')
    r.h('4.2 Sơ đồ triển khai và dòng xử lý',newpage=True)
    r.figure('fig7_search.png','Luồng truy vấn sử dụng đặc trưng đã lưu trong SQLite')
    r.p('Sau khi đọc UTF-8-sig, truy vấn đi qua đúng hàm content_tokens của kho. Các stem ngoài vocabulary cuối bị bỏ khỏi vector; các stem còn lại dùng IDF của terms. Mô hình chỉ transform, không học lại df hoặc IDF trên truy vấn. Vector q có 34.416 cột như X, được chuẩn hóa L2 trước khi tính s = Xqᵀ.')
    r.p('Nhân ma trận cho 1.000 điểm rồi sắp giảm dần bằng giá trị đầy đủ độ chính xác, phá hòa bằng filename. Ba TXT chỉ được xuất sau khi đường dẫn được kiểm tra thuộc corpus và SHA256 trùng CSDL. Trace được tạo tùy chọn sau phép tính, nhằm giải thích và kiểm tra kết quả chứ không tham gia xếp hạng.')
    r.h('4.3 Các module và dữ liệu trao đổi')
    r.table('Đầu vào và đầu ra các module',['Module','Đầu vào','Xử lý và đầu ra'],[
        ['preprocess','Chuỗi TXT; cấu hình từ dừng','Chuẩn hóa dấu nháy, regex, base, lọc, Porter → dãy stem'],
        ['features / build_features','1.000 TXT theo manifest','Count, df, lọc vocabulary, TF-IDF/L2 → CSR 1.000 × 34.416'],
        ['build_database','Đặc trưng P2; metadata; nhãn','Giao dịch nhập 5 bảng → SQLite và biên bản'],
        ['database.load_database','SQLite complete','Đọc ID, dựng X, vocabulary, IDF, metadata trong RAM'],
        ['search.transform_query','TXT; vocabulary và IDF','Counter stem → q 1 × 34.416; nnz, OOV, norm'],
        ['search.rank_scores','1.000 điểm; danh sách tài liệu','Sắp theo (-score, filename) → thứ tự Top-3'],
        ['search.export_trace','q, X, counts, điểm và Top-3','Bảng token, term, điểm, đóng góp và sai số'],
        ['evaluate / benchmark','Lần chạy; hai phiếu; điểm thống nhất','Kiểm chứng điểm/file, P@3, đồng thuận và số đo']], [4,5.3,7.4],size=10.5)
    r.p('Mỗi lần chạy lưu build_id, hash của mã xử lý và hash truy vấn để nối kết bằng chứng với cùng bản dựng. Các tệp nguồn truy vấn, phiếu chấm và kết quả nằm ngoài corpus. Kho tham chiếu không được quét đệ quy từ thư mục gốc vì sẽ lẫn bản sao, nguồn và truy vấn vào dữ liệu fit.')
    r.h('4.4 Bộ truy vấn ngoài kho và quy trình chọn',newpage=True)
    r.p('Bộ thử gồm 12 đoạn liên tục từ 12 tác phẩm, chia thành sáu nhóm nội dung, hai truy vấn mỗi nhóm. Mỗi đoạn có 950–1.050 token trước lọc theo regex GD1; số thực tế là 965–1.025, tổng 12.011. Đây là quy ước thực nghiệm của nhóm, không phải yêu cầu bổ sung của giảng viên. Q01 được chọn làm ví dụ chính trước khi truy hồi; Q12 là ca thăm dò, mọi truy vấn đều được giữ dù kết quả thấp.')
    groups=['Trinh thám và tội phạm','Hàng hải','Khoa học viễn tưởng','Tình cảm và xã hội','Phiêu lưu','Thiên nhiên và động vật']
    r.table('Danh sách 12 truy vấn đã chốt',['ID','Tác phẩm và tác giả','Nhóm','Từ'],[
        [m['query_id'],m['source_title']+'\n'+m['source_author'],groups[i//2],m['word_count']] for i,m in enumerate(manifest)], [1.1,10.1,3.8,1.7],size=10.5)
    r.p('Đoạn được cắt nguyên văn từ bản TXT Gutenberg: bỏ phạm vi header/footer, tìm mốc bắt đầu duy nhất và chọn kết thúc đoạn văn hoặc câu gần 1.000 từ. Giữ nguyên thứ tự, dấu câu và ký tự; không ghép câu từ các phần khác nhau. Manifest lưu tác phẩm, tác giả, URL, chương/phần, offset ký tự, số từ và hash. Q07 chọn Chương VI trước khi xem điểm để tránh chú thích tranh trong đoạn ban đầu. Nguồn, vị trí và toàn văn Q01 ở Phụ lục B–C.')
    r.p('Kiểm tra ngoài kho gồm đối chiếu tên/biến thể tên và tác giả trên cả 1.000 metadata, đọc các trường hợp cùng tác giả hoặc tuyển tập, rồi quét trùng token. Không phát hiện trùng 12-token liên tiếp giữa đoạn truy vấn và kho. Các neo 30-token lấy bước 30 trên toàn thân nguồn cũng không có hit sau đối chiếu token chính xác; cách lấy neo này phát hiện được đoạn trùng liên tục từ 59 token. Bằng chứng hỗ trợ việc chọn tác phẩm ngoài kho, nhưng không chứng minh tuyệt đối đối với bản dịch, diễn đạt lại hoặc ấn bản có biến đổi lớn.')
    r.p('Bộ truy vấn và rubric được khóa ngày 06/11/2026 lúc 00:10:38 +07:00, trước lần truy hồi chính thức. Toàn bộ 36 hash đầu vào đã được kiểm tra trước và sau P6. Số Gutenberg trong manifest là ID của nguồn truy vấn có URL cụ thể, không được suy ra từ mã filename của tài liệu kho.')
    r.h('4.5 Minh họa truy vấn Q01',newpage=True)
    r.h('4.5.1 Nguồn và diễn biến tiền xử lý',3)
    r.p('Q01 trích A Study in Scarlet của Arthur Conan Doyle, Part I, Chapter III, The Lauriston Gardens Mystery, Gutenberg #244. Đoạn bắt đầu “Number 3, Lauriston Gardens wore…” và kết thúc “…one of the main arteries of suburban London.” Nội dung mô tả Holmes khảo sát hiện trường cùng cảnh sát và quan sát thi thể. Offset ký tự [43668, 49364) được tính trên TXT giải mã UTF-8-sig, giữ CRLF; hash và toàn văn ở Phụ lục C.')
    r.table('Mười lăm token đầu của Q01',['Gốc','Chuẩn hóa','Base','Quyết định','Stem'],[
        [x['original_token'],x['token'],x['base'],{'kept':'Giữ','stopword':'Bỏ từ dừng','short_base':'Bỏ base ngắn'}[x['decision']],x['stem'] or '—'] for x in csvrows(RUN/'Q01/preprocess.csv')[:15]], [3.1,3.2,3.1,4.2,3.1])
    r.p('Số 3 không tạo token theo regex chữ cái, dấu gạch nối tách ill và omened; các từ như an, and, it bị loại trước stemming. Chuỗi Gardens được chuyển thành gardens và stem garden. Base được lấy trước dấu nháy đơn; không thêm bước lọc stopword sau stemming. Cách đếm 991 token nguyên văn khác số token còn lại dùng cho đặc trưng.')
    q=results['Q01']
    r.table('Thống kê Q01 qua các bước',['Chỉ tiêu','Giá trị'],[
        ['Raw token','991'],['Token sau lọc và Porter','426'],['Stem phân biệt','345'],['Stem trong vocabulary và nnz(q)','149'],
        ['Stem OOV phân biệt','196'],['Lượt xuất hiện stem OOV','265'],['Norm trước L2','38,400771824172914']], [10.7,6])
    r.p('OOV là ngoài vocabulary cuối, có thể do không xuất hiện trong kho hoặc bị ngưỡng df loại. Không được coi tất cả 196 stem là từ chưa từng có trong 1.000 tài liệu. Sau chiếu lên vocabulary, vector chỉ có 149 chiều khác 0 trên tổng 34.416 chiều.')
    r.h('4.5.2 Trọng số truy vấn và điểm toàn kho',3,newpage=True)
    terms=csvrows(RUN/'Q01/query_terms.csv')[:15]
    r.table('Mười lăm term Q01 có trọng số lớn nhất',['Term','f','TF','df','IDF','w thô','w L2'],[
        [x['term'],x['count'],fmt(x['tf'],4),x['df'],fmt(x['idf'],4),fmt(x['raw_weight'],4),fmt(x['weight'],6)] for x in terms], [3.5,1,2.3,1.2,2.6,2.9,3.2],size=10.5)
    r.p('Ví dụ gregson có f = 3 nên TF = 1 + ln(3) = 2,09861228866811. Stem này xuất hiện trong ba tài liệu kho, vì vậy IDF = ln(1001/4) + 1 = 6,52246041819533. Trọng số thô là 13,688115585976059; chia cho norm 38,400771824172914 cho trọng số L2 bằng 0,35645417880271674. Không có df nào trong bảng được tính trên 12 truy vấn.')
    r.table('Mười kết quả đầu của Q01',['Hạng','Tệp','Cosine'],[[x['rank'],x['filename'],fmt(x['score'])] for x in csvrows(RUN/'Q01/all_scores.csv')[:10]],[2,9.7,5])
    r.p('Khoảng cách điểm hạng 3 và hạng 4 là 0,00202307657959777. Top-3 được quyết định bằng số đầy đủ; sáu chữ số ở bảng chỉ phục vụ trình bày. Hệ thống tính đủ 1.000 điểm trước khi chọn kết quả, không lọc theo nhãn mystery_crime.')
    r.h('4.5.3 Ba tài liệu trả về và đóng góp của term',3,newpage=True)
    r.table('Metadata ba kết quả Q01',['Hạng và tệp','Tác phẩm và tác giả','Nhãn','Cosine'],[
        [str(x['rank'])+'\n'+x['filename'],x['title']+'\n'+x['author_display'],x['label_code'],fmt(x['score'])] for x in q['top3']],[3.7,7.6,3.3,2.1],size=10.5)
    r.p('Ba bản sao rank1_book_0733.txt, rank2_book_0659.txt và rank3_book_0638.txt đều có hash trùng tệp gốc và CSDL. Đây là đầu ra tệp thực, không chỉ danh sách tên sách. Tổng đóng góp các term chung phải bằng điểm: scoreᵢ = Σⱼ qⱼXᵢⱼ. Các bảng sau giữ cả phần còn lại để tránh nhầm tổng mười term hiển thị với toàn bộ cosine.')
    for rank in range(1,4):
        parts=csvrows(RUN/'Q01'/f'rank{rank}_contributions.csv')
        rows=[[x['term'],fmt(x['query_weight']),fmt(x['document_weight']),fmt(x['contribution'])] for x in parts[:10]]
        rows += [['Các term còn lại','—','—',fmt(math.fsum(float(x['contribution']) for x in parts[10:]))],['Tổng mọi term chung','—','—',fmt(math.fsum(float(x['contribution']) for x in parts))]]
        r.table(f'Đóng góp term vào kết quả Q01 hạng {rank}',['Term','qⱼ','Xᵢⱼ','Tích qⱼXᵢⱼ'],rows,[6.1,3.5,3.5,3.6],size=10.5)
    r.h('4.5.4 Nội dung kết quả và ca hạn chế',3)
    r.p('book_0733.txt có những đoạn bàn về suy luận trinh thám và nhắc Sherlock Holmes; dòng 482–489 chứa câu “Every detail points to something, certainly; but generally to the wrong thing.” book_0638.txt dòng 452–453 mô tả phát hiện người khách bị đâm chết: “My guest was lying sprawled on his back.” Các đoạn này hỗ trợ mối liên hệ nội dung, nhưng hai người chấm vẫn đánh giá cả hai chỉ mức 1 vì chưa sát tình huống trung tâm của Q01.')
    r.p('Kết quả hạng 2 là ca hạn chế rõ. Trong Q01, Gregson là thám tử tại hiện trường; ở book_0659.txt dòng 3273–3285, nhân vật là “Daniel Gregson, Esq., B.S.C., political agent to the Rajah of Oonomore”. Cùng stem gregson nhưng khác thực thể. Tích 0,35645417880271674 × 0,09774240775365489 = 0,03484068969002935 đóng góp 40,4363% cosine của cặp. Hai thành viên đều chấm mức 0. Tỷ lệ 40,4363% là phần đóng góp vào điểm, không phải phần trăm nội dung giống nhau hoặc xác suất liên quan.')
    r.p('Điểm cuối Q01 theo hạng là 1–0–1, nên P@3 = 0. Ca minh họa chính vẫn được giữ vì đã chọn trước thực nghiệm. Việc trace cộng đúng điểm không bảo đảm kết quả sát nội dung; ngược lại, điểm chất lượng thấp không chứng minh công thức hoặc CSDL sai.')
    r.h('4.6 Đánh giá trên toàn bộ bộ thử',newpage=True)
    r.h('4.6.1 Tiêu chí và quy trình chấm',3)
    r.p('Hai thành viên Khanh và Trong chấm riêng 36 cặp truy vấn–tài liệu. Hai phiếu xáo thứ tự khác nhau, ẩn điểm, hạng, nhãn và tên tệp corpus; mỗi cặp có toàn văn truy vấn và tài liệu để đọc. Mỗi mức chấm kèm trích dẫn nguyên văn ở cả hai phía và lý do. Sau khi nộp, nhóm đối chiếu bất đồng, giữ điểm ban đầu và ghi điểm thống nhất.')
    r.table('Thang liên quan và quy đổi nhị phân',['Mức','Tiêu chí nội dung','Liên quan nhị phân'],[
        ['2','Liên quan rõ với chủ đề hoặc tình huống trung tâm, có bằng chứng nội dung.','1'],
        ['1','Liên quan một phần hoặc chỉ chung bối cảnh, chưa sát trọng tâm.','0'],
        ['0','Không có liên quan đáng kể; trùng tên/từ phổ biến không đủ.','0']], [1.3,12.6,2.8])
    r.p('P@3(q) = số tài liệu mức 2 trong Top-3 / 3. Mean P@3 là trung bình trên đủ 12 truy vấn. Không bỏ truy vấn khó, không tính mức 1 vào tử số và không dùng cosine hay cùng nhãn để tự xác định liên quan. Không báo Recall, MAP hoặc nDCG vì chỉ chấm Top-3, chưa có phán xét đầy đủ cho toàn kho.')
    r.p('Hai phiếu giống mức ở 34/36 cặp, đồng thuận ban đầu 94,44%. P034 (Q03, hạng 3) và P003 (Q06, hạng 2) được Khanh chấm 1, Trong chấm 0; nhóm chốt cả hai mức 1. Các bất đồng 0/1 không làm đổi số kết quả mức 2, nhưng vẫn cần lưu để phản ánh mức độ nhất quán và cách phân biệt liên quan một phần với không liên quan.')
    r.h('4.6.2 Kết quả Top-3 và điểm liên quan',3)
    r.p('Bảng sau giữ đầy đủ 36 kết quả, kể cả các ca không đạt mức 2. A là Khanh, B là Trong; “Chốt” là mức thống nhất. Filename là khóa truy xuất, tên tác phẩm giữ từ metadata. Những ký tự thay thế có sẵn trong một số title nguồn được giữ nguyên; tên không tham gia tính điểm.')
    allrows=[]
    for m in manifest:
        qid=m['query_id']
        for x in results[qid]['top3']:
            pid=pairbydoc[qid,x['filename']]['pair_id']
            allrows.append([qid+'/'+str(x['rank']),x['filename']+'\n'+x['title'],fmt(x['score']),A[pid]['grade']+'/'+B[pid]['grade']+'/'+judgments[pid]['grade']])
    r.table('Toàn bộ Top-3 và hai lượt chấm độc lập',['Q/hạng','Tệp và tác phẩm','Cosine','A/B/Chốt'],allrows,[1.5,10.2,2.5,2.5],size=10.5)
    r.table('P@3 theo từng truy vấn',['ID','Mức cuối hạng 1–2–3','Số mức 2','P@3'],[
        [m['query_id'],' – '.join(judgments[pairbydoc[m['query_id'],x['filename']]['pair_id']]['grade'] for x in results[m['query_id']]['top3']),m['relevant_at_3'],fmt(m['precision_at_3'],4)] for m in metrics['per_query']], [2,8.2,3,3.5])
    r.p('Kết quả cuối có 11 cặp mức 0, 21 cặp mức 1 và 4 cặp mức 2. Mean P@3 = 1/9 = 0,111111… = 11,11%; do mọi truy vấn đều có k = 3, giá trị này cũng bằng 4/36. Có 3/12 truy vấn tìm được ít nhất một kết quả mức 2, tương đương 25%. Không gọi đây là accuracy phân loại. Chín truy vấn còn lại không đạt mức 2 trong Top-3 theo tiêu chí đã chốt.')
    r.p('Q04 có một kết quả mức 2 về đời sống và tổ chức thủy thủ tàu buôn. Q11 đạt 2/3 với hai tác phẩm của Thoreau về quan sát thiên nhiên; đây là đặc điểm của ca thử, không phải bằng chứng hiểu ngữ nghĩa tổng quát. Q12 đạt 1/3 với The Dawn of Reason, được chấm sát chủ đề sinh học và đấu tranh sinh tồn. Kết quả đầu Q12, The Coming Race, chỉ mức 1: có mô tả nghiên cứu sinh vật và ký sinh trong bối cảnh giả tưởng, nhưng không cùng mục đích lập luận khoa học với đoạn Darwin.')
    r.h('4.6.3 Kiểm chứng kỹ thuật và ngoại lệ',3,newpage=True)
    r.table('Kiểm chứng chương trình tìm kiếm',['Trường hợp','Kết quả kiểm tra'],[
        ['12 truy vấn chính thức','12/12 ok; đủ 36 bản sao khớp SHA256'],['Công thức độc lập cho 12.000 điểm','Sai lệch lớn nhất 5,551115123125783 × 10⁻¹⁷'],
        ['Tổng đóng góp của 36 cặp','Sai lệch lớn nhất 5,551115123125783 × 10⁻¹⁷'],['Ngưỡng chấp nhận','10⁻¹⁰; cả hai sai số đều nhỏ hơn'],
        ['Hòa điểm','Filename tăng dần, kiểm thử đạt'],['Tệp lỗi và lô nhiều đầu vào','Ghi lỗi, tiếp tục truy vấn sau, không xuất bản sao dở'],
        ['Đầu vào vector rỗng','empty_vector; Top-3 rỗng; 0 bản sao'],['Bộ kiểm thử P2–P6','27/27 kiểm thử Python đạt']], [7.5,9.2])
    r.p('Phép đối chiếu P6 đếm stem và dựng vector đặc theo công thức TF/IDF/L2 độc lập với hàm transform_query, dùng vocabulary và IDF từ SQLite; so sánh toàn bộ điểm, ánh xạ và thứ tự. Kiểm tra hash áp dụng cho cả nguồn và bản sao. Những kiểm tra này xác nhận tính đúng của triển khai, không thay thế chấm liên quan bằng nội dung.')
    r.p('Ca vector rỗng dùng riêng chuỗi “the and or is a chapter i ii iii”. Tất cả token bị loại sau tiền xử lý, norm bằng 0; chương trình trả empty_vector, không tạo ba kết quả tùy ý. Ca này nằm ngoài 12 truy vấn chính thức, không thay đổi mẫu số P@3. Các ca số/ký hiệu, tệp rỗng, thiếu tệp và UTF-8 lỗi được kiểm tra riêng trong bộ kiểm thử chức năng.')
    r.h('4.6.4 Thời gian xử lý và dung lượng',3)
    r.p('Máy thử dùng Intel Core i5-12400F, 6 nhân/12 luồng, RAM hệ thống báo 17.013.252.096 byte (khoảng 15,84 GiB), Windows 11 Pro 10.0.26200. Môi trường là Python 3.10.11, SQLite 3.40.1, NumPy 2.2.6, SciPy 1.15.3, scikit-learn 1.7.2 và NLTK 3.10.3. Đo bằng perf_counter, tách nạp CSDL và xử lý khi X đã ở RAM.')
    r.table('Thời gian và dung lượng đo thực',['Phép đo','Giá trị','Phạm vi'],[
        ['Dựng đặc trưng P2','28,290226 s','Nhật ký dựng; không gồm đối chiếu GD1 độc lập'],['Nhập và kiểm tra P3','26,008830 s','Giao dịch nhập và validate'],
        ['Nạp SQLite, trung vị 5 lượt','4,110522 s','Đọc, tạo chỉ mục, kiểm tra nhẹ; không gồm khởi động Python'],['Truy vấn, trung vị 60 lượt','6,943200 ms','Một làm nóng + năm đo mỗi Q; X/cache stem đã nạp'],
        ['Truy vấn nhỏ nhất/lớn nhất','5,994300 / 8,073300 ms','Cùng 60 lượt; không gồm trace và sao chép'],['Một lô chính thức có trace','4,999056 s','12 câu; gồm 4,246006 s nạp DB, không gồm khởi động Python'],
        ['SQLite','64,723 MiB','67.866.624 byte'],['Corpus TXT','183,269 MiB','192.171.854 byte'],['Mảng X dạng CSR','22,054 MiB','Không phải RAM đỉnh hay toàn DatabaseIndex']], [5.2,4.0,7.5],size=10.5)
    timings=csvrows(EVAL/'performance_final/query_timings_median.csv')
    r.table('Trung vị năm lượt theo từng truy vấn',['Q','Đọc ms','Transform ms','Xqᵀ ms','Xếp hạng ms','Tổng ms'],[
        [x['query_id']]+[fmt(float(x[k])*1000,4) for k in ['read_seconds','transform_seconds','score_seconds','ranking_seconds','total_seconds']] for x in timings],[1.3,2.8,3.5,3.0,3.3,2.8],size=10.5)
    r.p('Phép đo chính được chạy riêng, không chạy kiểm thử song song. Nạp SQLite không xóa cache hệ điều hành nên không gọi là đọc đĩa lạnh. Thời gian truy vấn gồm đọc/giải mã TXT, transform, tính 1.000 điểm và xếp hạng; không gồm thao tác người dùng, xuất trace, sao chép kết quả hoặc khởi động trình thông dịch. Trung vị từng thành phần không nhất thiết cộng thành trung vị tổng. Các số dựng P2/P3 là nhật ký lịch sử, không phải dựng lại ở P6.')
    r.h('4.7 Giới hạn và hướng hoàn thiện')
    r.p('Kết quả cho thấy TF-IDF unigram với một vector cho cả tệp còn hạn chế khi truy vấn là một đoạn có tình huống cụ thể. Nhiều kết quả chia sẻ bối cảnh hoặc từ khóa nhưng chưa sát trọng tâm, thể hiện ở 21 mức 1 và chỉ bốn mức 2. Tên riêng hiếm có thể chiếm phần lớn điểm như gregson; mô hình không phân biệt hai thực thể cùng tên và không trực tiếp mô hình hóa từ đồng nghĩa hay quan hệ ngữ cảnh.')
    r.p('Độ dài tài liệu lớn có thể làm phân tán trọng số của đoạn liên quan; lọc df loại một số từ hiếm hoặc quá phổ biến. Bộ thử gồm 12 đoạn được chọn có chủ đích ở sáu nhóm, không đại diện toàn bộ 14 nhãn hay mọi văn bản tiếng Anh. Điểm chấm vẫn phụ thuộc cách người đọc xác định trọng tâm; đồng thuận ban đầu 94,44% cho biết mức nhất quán trong bộ thử này, không loại bỏ mọi tính chủ quan.')
    r.p('Giai đoạn 3 trước mắt tái sử dụng CSDL và hàm search để xây giao diện chọn TXT, xem điểm, mở ba tài liệu và xem trace. Các hướng như tìm theo đoạn, xử lý thực thể hay biểu diễn ngữ nghĩa chỉ là đề xuất nghiên cứu tiếp; chưa được triển khai hoặc đo so sánh trong báo cáo. Không đổi thuật toán, bộ truy vấn hoặc ngưỡng chấm sau khi biết kết quả để hợp thức hóa chất lượng.')
    r.h('KẾT LUẬN',1)
    r.p('Trên bộ 1.000 tệp tiếng Anh, nhóm đã hoàn thành CSDL SQLite lưu vocabulary 34.416 term cùng 1.926.766 trọng số khác 0, count, df, IDF và metadata cần thiết. Ma trận đọc lại khớp tham chiếu P2; kiểm tra cấu trúc, khóa và công thức đều đạt. Hệ thống dòng lệnh dùng cùng tiền xử lý GD1, không fit lại truy vấn và không dùng nhãn để tính điểm.')
    r.p('Chương trình đã chạy 12 truy vấn ngoài kho, xuất đủ 36 bản sao và trace có thể kiểm tra từ token đến tổng đóng góp. Sai lệch điểm lớn nhất so với công thức kiểm chứng là 5,551115123125783 × 10⁻¹⁷. Trung vị xử lý khi chỉ mục đã nạp là 6,943200 ms trên máy thử; số đo này không gồm trace, sao chép tệp hay khởi động Python.')
    r.p('Chất lượng truy hồi còn hạn chế: Mean P@3 đạt 11,11%, ba truy vấn có ít nhất một kết quả mức 2. Các trường hợp trùng tên riêng hoặc chỉ chung bối cảnh cho thấy tính đúng số học không đồng nghĩa hiểu đúng nội dung. Báo cáo giữ đầy đủ điểm ban đầu, quyết định thống nhất và các ca chưa tốt, tạo cơ sở trung thực cho cải tiến và demo ở giai đoạn 3.')
    r.h('TÀI LIỆU THAM KHẢO',1)
    refs=[
        '[1] scikit-learn. TfidfTransformer, tài liệu phiên bản 1.7.2. https://scikit-learn.org/1.7/modules/generated/sklearn.feature_extraction.text.TfidfTransformer.html. Đối chiếu ngày 06/11/2026.',
        '[2] SQLite. Foreign Key Support. https://www.sqlite.org/foreignkeys.html. Đối chiếu ngày 06/11/2026.',
        '[3] SQLite. STRICT Tables. https://www.sqlite.org/stricttables.html. Đối chiếu ngày 06/11/2026.',
        '[4] NLTK. nltk.stem.porter module, chế độ NLTK_EXTENSIONS. https://www.nltk.org/api/nltk.stem.porter.html. Đối chiếu ngày 06/11/2026; phiên bản thực nghiệm ghi ở mục 4.6.4.',
        '[5] Project Gutenberg. Grania #58443; The Earl’s Promise tập 1 #70755 và tập 2 #70756. https://www.gutenberg.org/ebooks/58443; https://www.gutenberg.org/ebooks/70755; https://www.gutenberg.org/ebooks/70756. Bằng chứng đối chiếu tập ngày 04/11/2026.',
        '[6] Project Gutenberg. Các nguồn 12 truy vấn, danh mục và vị trí trích ghi tại Phụ lục B. Toàn văn nguồn tải ngày 05/11/2026, bộ truy vấn khóa ngày 06/11/2026 trước truy hồi.',
        '[7] Nhóm 23 lớp 03. Bộ dữ liệu, mã thống kê và báo cáo GD1; biên bản P2–P6, manifest truy vấn, log thực nghiệm và hai phiếu chấm Khanh/Trong, 2026. Bằng chứng tái lập được liệt kê ở Phụ lục A.'
    ]
    for ref in refs:r.p(ref,'P7 Small')
    r.h('PHỤ LỤC A. CẤU HÌNH VÀ ĐỐI CHIẾU BẰNG CHỨNG',1)
    r.p('Các đường dẫn dưới đây tính từ thư mục gốc dự án. Những số liệu quyết định đã được trình bày trong thân báo cáo; tệp ngoài PDF cung cấp độ chính xác đầy đủ và khả năng tái lập.')
    r.table('Cấu hình và các tệp bằng chứng',['Thành phần','Giá trị hoặc vị trí'],[
        ['Regex raw token',"[a-z]+(?:'[a-z]+)?"],['Base; lọc; stemming',"token.split(\"'\")[0]; len ≥ 2; stopword trước Porter"],
        ['Stopword và Porter','scikit-learn ENGLISH_STOP_WORDS + EXTRA_STOP; NLTK_EXTENSIONS'],['TF-IDF','Unigram; min_df=3; max_df=0,6; sublinear_tf; smooth_idf; norm=L2'],
        ['P2 và P3','gd2/artifacts/p2/verification.json; gd2/database/documents.verification.json'],['Bộ truy vấn và khóa','gd2/queries/query_manifest.csv; queries.lock.json'],
        ['Kết quả và trace','gd2/results/p6_official/Q01…Q12'],['Chấm cuối và hiệu năng','gd2/evaluation/p6/grading_final; performance_final']], [5.3,11.4],size=10.5)
    r.p('Build ID: '+p3['build_id'],'P7 Small')
    r.p('SHA256 CSDL: '+p3['database_sha256'],'P7 Code')
    r.code('python tools/verify_baseline.py\npython -m gd2.src.verify_database\npython -m gd2.src.verify_queries\npython -m gd2.src.search --query gd2/queries/Q01.txt --out new_run --trace\npython -m gd2.src.evaluate grade --out grading_recheck')
    r.p('Các thư mục đầu ra mới phải chưa tồn tại. Khi chạy đủ bộ thử, truyền Q01.txt đến Q12.txt theo đúng thứ tự manifest. Tệp grading_final giữ bản sao ba CSV và hash; hai phiếu ban đầu không bị thay bằng điểm thống nhất.')
    r.h('PHỤ LỤC B. NGUỒN VÀ VỊ TRÍ CỦA BỘ TRUY VẤN',1)
    r.p('URL danh mục có dạng https://www.gutenberg.org/ebooks/ID. TXT dùng dạng https://www.gutenberg.org/cache/epub/ID/pgID.txt. ID trong bảng là ID của nguồn đã lưu. Offset bắt đầu từ 0, kết thúc không bao gồm, trên chuỗi UTF-8-sig giữ CRLF; mỗi đoạn khớp chính xác chuỗi con của nguồn. Với #205, truy vấn lấy The Ponds trong Walden, không lấy Civil Disobedience cùng tệp nguồn.')
    r.table('Nguồn Gutenberg và vị trí trích nguyên văn',['Q và ID','Chương hoặc phần','Khoảng ký tự','Số từ'],[
        [m['query_id']+' / #'+m['source_id'],m['chapter_or_section'],'['+m['start_locator']+', '+m['end_locator']+')',m['word_count']] for m in manifest],[2.4,8.4,4.2,1.7],size=10.5)
    r.p('Tác phẩm và tác giả tương ứng đã được liệt kê ở Bảng 14. Hai tầng kiểm tra ngoài kho được mô tả ở mục 4.4. Việc khóa trước khi truy hồi áp dụng cho cả nội dung TXT, nguồn, manifest và rubric; không chọn lại đoạn dựa trên cosine hay P@3.')
    r.h('PHỤ LỤC C. TOÀN VĂN TRUY VẤN Q01',1)
    r.p('A Study in Scarlet — Arthur Conan Doyle. Part I, Chapter III. Gutenberg #244; đoạn liên tục gồm 991 token theo regex GD1. Văn bản dưới đây giữ nguyên nội dung; dàn dòng lại cho trang báo cáo.','P7 Small')
    r.p('SHA256 Q01: '+results['Q01']['query_sha256'],'P7 Code')
    text=(ROOT/'gd2/queries/Q01.txt').read_text(encoding='utf-8')
    import re
    for para in re.split(r'\n\s*\n',text.strip()):
        p=r.p(re.sub(r'\s*\n\s*',' ',para),'P7 Small');p.paragraph_format.line_spacing=1.08;p.paragraph_format.space_after=Pt(5)
    r.h('PHỤ LỤC D. SCHEMA SQL ĐÃ TRIỂN KHAI',1)
    r.p('Schema phiên bản 4 dưới đây là schema của CSDL được dùng trong thực nghiệm. Phần chú thích chỉ phục vụ trình bày; khai báo trường và ràng buộc giữ theo tệp schema.sql.','P7 Small')
    schema=(ROOT/'gd2/database/schema.sql').read_text(encoding='utf-8')
    r.code('\n'.join(line for line in schema.splitlines() if not line.startswith('--')))
    # Evidence for content preservation before Word refresh.
    current=list(r.d.element.body); start=current.index(r.chapter_start)
    for source_el,dest_el in zip(r.original_body,current[start:start+len(r.original_body)]):
        assert etree.tostring(source_el,method='c14n',exclusive=True)==etree.tostring(dest_el,method='c14n',exclusive=True), 'GD1 body was modified during authoring'
    r.d.save(FINAL)
    writej(WORK/'build_manifest.json',{'source_sha256':digest(SOURCE),'output':str(FINAL),'tables_total':r.table_number,'figures_total':r.figure_number,
        'original_body_elements_preserved':len(r.original_body),'original_math_nodes':19,'new_captions':r.captions,
        'input_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):digest(p) for p in [ROOT/'gd2/artifacts/p6/verification.json',EVAL/'grading_final/metrics.json',ROOT/'gd2/database/documents.sqlite',ROOT/'gd2/queries/query_manifest.csv']}})
    print(FINAL)


if __name__=='__main__':build()
