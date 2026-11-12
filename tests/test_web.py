import time
from fastapi.testclient import TestClient
from cad_print_workflow.web import create_app

def test_demo_review_build_download(tmp_path, monkeypatch):
    monkeypatch.delenv('CAD_FREECAD_CMD',raising=False)
    client=TestClient(create_app(tmp_path)); headers={'X-CAD-Local':'1'}
    assert client.get('/').status_code==200
    assert client.post('/api/demo').status_code==403
    demo=client.post('/api/demo',headers=headers).json()
    assert demo['status']=='review'
    spec=demo['spec']
    assert client.post('/api/build',headers=headers,json={'confirmed':True,'spec':spec}).status_code==400
    spec['reviewed']=True
    job=client.post('/api/build',headers=headers,json={'confirmed':True,'spec':spec}).json()
    for _ in range(100):
        job=client.get('/api/jobs/'+job['id']).json()
        if job['status']!='running':break
        time.sleep(.05)
    assert job['status']=='done',job
    assert 'drawing.pdf' in job['files']
    assert client.get('/api/files/'+job['id']+'/drawing.pdf').content.startswith(b'%PDF')
    assert client.get('/api/files/'+job['id']+'/input.json').status_code==404

def test_config_does_not_echo_key(tmp_path):
    client=TestClient(create_app(tmp_path))
    result=client.post('/api/config',headers={'X-CAD-Local':'1'},json={'model':'vision','base_url':'https://example.invalid/v1','key':'test-secret'})
    assert result.status_code==200
    assert 'test-secret' not in result.text
    assert 'test-secret' not in client.get('/api/status').text
    assert client.get('/',headers={'Host':'evil.example'}).status_code==400
