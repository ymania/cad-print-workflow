"""Parse browser-produced bytes with independent CAD/PDF readers."""
import json
from pathlib import Path
import shutil
import subprocess
import ezdxf
from pypdf import PdfReader
import pytest

ROOT=Path(__file__).parents[1]

@pytest.mark.skipif(not shutil.which('node'),reason='Node needed to exercise browser export functions')
def test_browser_formats(tmp_path):
    script="""const fs=require('node:fs'),core=require('./frontend/core.js');
    const s={...structuredClone(core.demo),reviewed:true};
    const path=require('node:path');
    for(const [name,fn] of [['drawing.dxf','dxf'],['drawing.pdf','pdf'],['build.FCMacro','macro']])
      fs.writeFileSync(path.join(process.argv[1],name),core[fn](s));
    """
    subprocess.run(['node','-e',script,str(tmp_path)],cwd=ROOT,check=True)
    doc=ezdxf.readfile(tmp_path/'drawing.dxf'); audit=doc.audit()
    assert not audit.errors and not audit.fixes
    assert doc.units==4
    assert len(doc.modelspace())==8
    assert doc.modelspace().query('CIRCLE')[0].dxf.radius==40
    assert doc.layers.get('outline').dxf.lineweight==50
    assert doc.layers.get('center').dxf.linetype=='CENTER'
    pdf=PdfReader(tmp_path/'drawing.pdf')
    assert len(pdf.pages)==1
    assert abs(float(pdf.pages[0].mediabox.width)*25.4/72-420)<.001
    assert abs(float(pdf.pages[0].mediabox.height)*25.4/72-297)<.001
    import pymupdf
    with pymupdf.open(tmp_path/'drawing.pdf') as rendered:
        assert len(rendered[0].get_drawings())==8
    compile((tmp_path/'build.FCMacro').read_text(),'browser macro','exec')
