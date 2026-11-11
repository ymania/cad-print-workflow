import hashlib
import ezdxf
import pymupdf as fitz
import pytest
from pypdf import PdfReader
from cad_print_workflow.cli import convert


def drawing(tmp_path):
    d=ezdxf.new('R2000');d.units=4
    m=d.modelspace();d.layers.new('THIN',dxfattribs={'lineweight':25})
    for y in [185,200]:m.add_line((40,y),(200,y),dxfattribs={'layer':'THIN'})
    return d,m,tmp_path/'in.dxf',tmp_path/'out.pdf'


def test_render_lines_and_dimensions(tmp_path):
    d,m,src,out=drawing(tmp_path)
    m.add_linear_dim(base=(40,175),p1=(40,185),p2=(200,185)).render()
    d.saveas(src);before=hashlib.sha256(src.read_bytes()).hexdigest()
    report=convert(src,out)
    assert hashlib.sha256(src.read_bytes()).hexdigest()==before
    assert report['rendered_entities']['TEXT']>=1
    page=PdfReader(out).pages[0]
    assert float(page.mediabox.width)==pytest.approx(420*72/25.4,abs=.001)
    with fitz.open(out) as pdf:
        p=pdf[0]; pix=p.get_pixmap(matrix=fitz.Matrix(2,2),colorspace=fitz.csGRAY)
        for y in [185,200]:
            row=round((297-y)*72/25.4*2)
            # Long dark run at BOTH original y positions (regression for disappearing thin line).
            runs=[]
            for yy in range(row-2,row+3):
                data=pix.samples[yy*pix.stride:(yy+1)*pix.stride]
                runs.append(sum(v<100 for v in data))
            assert max(runs)>800
    with pytest.raises(ValueError,match='exists'):convert(src,out)


def test_rejects_unsupported_and_bounds(tmp_path):
    d,m,src,out=drawing(tmp_path);m.add_point((10,10));d.saveas(src)
    with pytest.raises(ValueError,match='Unsupported'):convert(src,out)
    assert not out.exists()
    m.delete_entity(list(m.query('POINT'))[0]);m.add_line((410,20),(430,20));d.saveas(src)
    with pytest.raises(ValueError,match='exceeds'):convert(src,out)
    assert not out.exists()


def test_hidden_and_units(tmp_path):
    d,m,src,out=drawing(tmp_path)
    d.layers.new('NO_PRINT',dxfattribs={'plot':0})
    m.add_point((500,500),dxfattribs={'layer':'NO_PRINT'});d.saveas(src)
    convert(src,out)
    d.units=1;d.saveas(src)
    with pytest.raises(ValueError,match='millimetre'):convert(src,tmp_path/'bad.pdf')


def test_scaled_dimension_keeps_actual_value(tmp_path):
    d,m,src,out=drawing(tmp_path)
    dim=m.add_linear_dim(base=(40,60),p1=(40,70),p2=(205,70),override={'dimlfac':1/3,'dimdec':0})
    dim.render();d.saveas(src)
    block=d.blocks[dim.dimension.dxf.geometry]
    assert any('55' in e.text for e in block.query('MTEXT'))
    report=convert(src,out)
    assert report['rendered_entities']['TEXT']>=1


def test_missing_glyph(tmp_path):
    d,m,src,out=drawing(tmp_path)
    m.add_text('中',dxfattribs={'insert':(40,50),'height':3});d.saveas(src)
    with pytest.raises(ValueError,match='lacks glyphs'):convert(src,out)
    assert not out.exists()
