"""Check the published report against retained GD1 and frozen P6 evidence."""
from pathlib import Path
import csv
import hashlib
import json
import re
import zipfile
from datetime import datetime
from docx import Document
from docx.oxml.ns import qn
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'gd2/report'
EVAL = ROOT / 'gd2/evaluation/p6'

def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def texts(element):
    return ''.join(n.text or '' for n in element.iter() if n.tag in (qn('w:t'), qn('m:t')))

def chapter_body(doc):
    elements=list(doc.element.body)
    start=next(i for i,e in enumerate(elements) if e.find('.//'+qn('w:pStyle')) is not None and e.find('.//'+qn('w:pStyle')).get(qn('w:val'))=='CTDT-H1')
    end=next((i for i,e in enumerate(elements[start+1:],start+1) if texts(e).startswith('CHƯƠNG 3.')),len(elements)-1)
    return elements[start:end]

def main():
    original=ROOT/'docs/gd1/GD1-CSDLDPT-23-03.docx'
    docx=OUT/'GD1-GD2-CSDLDPT-23-03.docx'
    pdf=docx.with_suffix('.pdf')
    inventory=load(OUT/'work/source_inventory.json')
    assert sha(original)==inventory['sha256']
    source=Document(original); final=Document(docx)
    old=chapter_body(source); new=chapter_body(final)
    old_text=[texts(e) for e in old if texts(e)]
    new_text=[texts(e) for e in new if texts(e)]
    assert old_text==new_text, 'GD1 chapter text/formulas/table contents changed'
    old_math=[texts(n) for e in old for n in e.iter(qn('m:oMath'))]
    new_math=[texts(n) for e in new for n in e.iter(qn('m:oMath'))]
    assert old_math==new_math and len(old_math)==19
    with zipfile.ZipFile(original) as zs,zipfile.ZipFile(docx) as zf:
        original_media=[hashlib.sha256(zs.read(n)).hexdigest() for n in zs.namelist() if n.startswith('word/media/')]
        final_media=[hashlib.sha256(zf.read(n)).hexdigest() for n in zf.namelist() if n.startswith('word/media/')]
        assert all(h in final_media for h in original_media)
    paragraphs=[p.text for p in final.paragraphs]
    start=paragraphs.index('PHỤ LỤC C. TOÀN VĂN TRUY VẤN Q01')
    end=paragraphs.index('PHỤ LỤC D. SCHEMA SQL ĐÃ TRIỂN KHAI')
    actual=' '.join(paragraphs[start+3:end])
    expected=(ROOT/'gd2/queries/Q01.txt').read_text(encoding='utf-8').strip()
    normalize=lambda s:re.sub(r'\s+',' ',s).strip()
    assert normalize(actual)==normalize(expected), 'Q01 appendix differs'
    p6=load(ROOT/'gd2/artifacts/p6/verification.json')
    checked=0; historical=[]
    for name,h in p6['files_sha256'].items():
        if name.endswith('.md'):
            historical.append(name)
        else:
            assert sha(ROOT/name)==h, name
            checked+=1
    metrics=load(EVAL/'grading_final/metrics.json')
    assert metrics['mean_precision_at_3']==1/9
    with (EVAL/'grading_final/comparison.csv').open(encoding='utf-8-sig',newline='') as f:
        grades=list(csv.DictReader(f))
    # Every final relevance row and rounded score is reproduced in the report.
    report_rows=[tuple(c.text for c in row.cells) for t in final.tables for row in t.rows]
    for grade in grades:
        result=load(ROOT/f"gd2/results/p6_official/{grade['query_id']}/results.json")
        entries=result.get('top3',result.get('results',[]))
        item=next(x for x in entries if x['filename']==grade['filename'])
        score=item.get('score',item.get('cosine'))
        expected_start=f"{grade['query_id']}/{grade['rank']}"
        grade_cell='/'.join(grade[k] for k in ['grade_A','grade_B','consensus_grade'])
        assert any(row[0]==expected_start and grade['filename'] in row[1] and row[-1]==grade_cell and f'{score:.6f}'.replace('.',',') in row for row in report_rows)
    reader=PdfReader(pdf)
    pages=[p.extract_text() for p in reader.pages]
    all_text='\n'.join(pages)
    for bad in ['Error!','Error: Reference','[ĐIỀN','[ĐO','TODO','turn0search','provided_mapping','verified_volume_scope','not_verified','original_filename']:
        assert bad not in all_text, bad
    # Printed numbers are continuous; cover has no printed page number.
    for i,page in enumerate(reader.pages[1:],2):
        footer=[]
        page.extract_text(visitor_text=lambda text,cm,tm,font,size:footer.append(text) if 20<tm[5]<50 else None)
        assert ''.join(footer).strip()==str(i), f'Page number mismatch: {i}'
    captions=[p for p in final.paragraphs if p.style.name in ['P7 Table','P7 Figure']]
    assert [int(re.match(r'Bảng (\d+)',p.text).group(1)) for p in captions if p.text.startswith('Bảng')]==list(range(6,31))
    assert [int(re.match(r'Hình (\d+)',p.text).group(1)) for p in captions if p.text.startswith('Hình')]==[5,6,7]
    result={
        'phase':'P7','status':'complete','checked_at':datetime.now().astimezone().isoformat(),
        'pdf_pages':len(pages),'tables_numbered':30,'figures_numbered':7,
        'gd1_chapters_text_tables_formulas_preserved':True,'gd1_math_nodes':19,
        'gd1_original_media_preserved':len(original_media),'gd1_source_unchanged':True,
        'q01_appendix_content_preserved':True,'grading_rows_checked':len(grades),
        'p6_frozen_files_hash_checked':checked,'p6_historical_markdown_snapshots':historical,
        'page_numbers_continuous':True,'placeholder_and_field_error_scan':'passed',
        'renderer':load(OUT/'work/render_manifest.json'),
        'files_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in [original,docx,pdf,OUT/'build_report.py',OUT/'render_word.ps1',Path(__file__),ROOT/'gd2/database/documents.sqlite',ROOT/'gd2/artifacts/p6/verification.json']}
    }
    review_path=OUT/'work/visual_review.json'
    if review_path.exists():
        review=load(review_path)
        if review['pdf_sha256']==sha(pdf) and review['pages_reviewed']==list(range(1,len(pages)+1)):
            result['visual_review']=review
        else:
            result['status']='visual_review_required'
    else:
        result['status']='visual_review_required'
    target=ROOT/'gd2/artifacts/p7';target.mkdir(exist_ok=True)
    (target/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'work/pdf_text.txt').write_text('\n'.join(f'PAGE {i+1}\n{p}' for i,p in enumerate(pages)),encoding='utf-8')
    print(json.dumps({'pages':len(pages),'status':'passed','frozen_hashes_checked':checked}))

if __name__=='__main__':
    main()
