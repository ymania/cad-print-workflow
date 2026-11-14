import hashlib
import json
import shutil
import zipfile
import ezdxf
import pytest
from pypdf import PdfReader
from cad_print_workflow.delivery import audit_job, build_job, package_job


def fixture(tmp_path, factor=1/3, text='<>'):
    doc=ezdxf.new('R2000');doc.units=4
    m=doc.modelspace();m.add_line((30,40),(195,40))
    dim=m.add_linear_dim(base=(30,30),p1=(30,40),p2=(195,40),text=text,override={'dimlfac':factor,'dimdec':0})
    dim.render();doc.saveas(tmp_path/'sheet.dxf')
    job={'version':1,'sheets':[{'id':'sheet1','source':'sheet.dxf','geometry_reviewed':True,'dimensions':[{'handle':dim.dimension.dxf.handle,'expected':55,'drawing_scale':3,'source':'合成题目：实际55，绘图3:1'}]}]}
    path=tmp_path/'job.json';path.write_text(json.dumps(job));return doc,dim.dimension,path,job


def test_reject_scale_override_stale_cache_and_missing_checks(tmp_path):
    doc,dim,path,job=fixture(tmp_path)
    assert audit_job(path)['passed']
    text=next(iter(doc.blocks[dim.dxf.geometry].query('MTEXT')))
    text.text='165';doc.saveas(tmp_path/'sheet.dxf')
    assert not audit_job(path)['passed']
    doc,dim,path,job=fixture(tmp_path,factor=1)
    report=audit_job(path);assert not report['passed'];assert '换算因子' in str(report)
    doc,dim,path,job=fixture(tmp_path,text='55')
    assert '固定覆盖' in str(audit_job(path))
    job['sheets'][0]['dimensions']=[];path.write_text(json.dumps(job))
    assert not audit_job(path)['passed']


def test_paths_and_unreviewed_jobs_blocked(tmp_path):
    doc,dim,path,job=fixture(tmp_path)
    job['sheets'][0]['source']='../secret.dxf';path.write_text(json.dumps(job))
    with pytest.raises(ValueError,match='超出'):audit_job(path)
    job['sheets'][0]['source']='sheet.dxf';job['sheets'][0]['geometry_reviewed']=False;path.write_text(json.dumps(job))
    with pytest.raises(ValueError,match='核对'):audit_job(path)


@pytest.mark.skipif(not shutil.which('pdftoppm'),reason='需要Poppler预览')
def test_multi_sheet_atomic_build_review_and_integrity(tmp_path):
    doc,dim,path,job=fixture(tmp_path)
    job['sheets'].append({**job['sheets'][0],'id':'sheet2'})
    path.write_text(json.dumps(job));before=hashlib.sha256((tmp_path/'sheet.dxf').read_bytes()).hexdigest()
    out=tmp_path/'delivery';build_job(path,out)
    assert len(PdfReader(out/'A3-all.pdf').pages)==2
    assert hashlib.sha256((tmp_path/'sheet.dxf').read_bytes()).hexdigest()==before
    with pytest.raises(ValueError,match='逐页'):package_job(out)
    package_job(out,True)
    with zipfile.ZipFile(out/'delivery.zip') as z:
        assert 'sheet2.dxf' in z.namelist()
        assert json.loads(z.read('review.json'))['visual_review_confirmed']
    with pytest.raises(ValueError,match='不覆盖'):build_job(path,out)
    (out/'sheet1.dxf').write_text('changed')
    with pytest.raises(ValueError,match='修改'):package_job(out,True)


def test_failed_audit_creates_no_delivery(tmp_path):
    doc,dim,path,job=fixture(tmp_path,factor=1)
    out=tmp_path/'delivery'
    with pytest.raises(ValueError,match='未通过'):build_job(path,out)
    assert not out.exists()
