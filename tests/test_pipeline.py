import copy
import json
from pathlib import Path
from unittest.mock import patch
import pytest
import ezdxf
from cad_print_workflow.pipeline import build, extract, validate, macro_text

@pytest.fixture
def spec():
    return json.loads((Path(__file__).parents[1]/'examples/reviewed_geometry.json').read_text())

def test_review_and_invalid_geometry(spec):
    spec['reviewed'] = False
    with pytest.raises(ValueError, match='Review'): validate(spec)
    spec['reviewed'] = True
    spec['unresolved'] = ['radius uncertain']
    with pytest.raises(ValueError, match='Review'): validate(spec)
    spec['unresolved'] = []
    spec['components'][0]['entities'][0]['radius'] = float('nan')
    with pytest.raises(ValueError, match='finite'): validate(spec)

def test_build_geometry_and_no_overwrite(spec, tmp_path):
    source = tmp_path/'input.json'; source.write_text(json.dumps(spec))
    before = source.read_bytes()
    out = tmp_path/'built'
    build(source,out)
    doc = ezdxf.readfile(out/'drawing.dxf')
    assert doc.modelspace().query('CIRCLE')[0].dxf.radius == 40
    assert len(doc.modelspace().query('ARC')) == 1
    assert (out/'drawing.pdf').stat().st_size > 100
    assert source.read_bytes() == before
    with pytest.raises(ValueError,match='new output'): build(source,out)

def test_model_cannot_claim_review(spec,tmp_path):
    image = tmp_path/'test.png'; image.write_bytes(b'test')
    response = {'choices':[{'message':{'content':json.dumps(spec)}}]}
    from io import BytesIO
    with patch('urllib.request.urlopen', return_value=BytesIO(json.dumps(response).encode())) as call:
        extract(image,tmp_path/'draft.json','vision','https://example.invalid/v1','secret')
    draft = json.loads((tmp_path/'draft.json').read_text())
    assert draft['reviewed'] is False
    assert len(draft['source_sha256']) == 64
    body = json.loads(call.call_args.args[0].data)
    assert body['messages'][1]['content'][1]['image_url']['url'].startswith('data:image/png;base64,')
    assert 'secret' not in (tmp_path/'draft.json').read_text()

def test_macro_labels_are_data(spec):
    spec['components'][0]['id'] = "'); raise RuntimeError('injected') #"
    compile(macro_text(spec),'macro','exec')
    assert repr(json.dumps(spec,ensure_ascii=True)) in macro_text(spec)
