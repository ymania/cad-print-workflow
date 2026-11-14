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


def test_delivery_web_review_and_package(tmp_path):
    import base64
    import ezdxf
    doc=ezdxf.new(); doc.units=4
    doc.modelspace().add_circle((60,60),20)
    source=tmp_path/'input.dxf'; doc.saveas(source)
    client=TestClient(create_app(tmp_path/'data')); headers={'X-CAD-Local':'1'}
    assert client.get('/delivery').status_code==200
    assert client.post('/api/delivery/upload',json={}).status_code==403
    upload=client.post('/api/delivery/upload',headers=headers,json={'data':base64.b64encode(source.read_bytes()).decode()}).json()
    assert upload['status']=='uploaded'
    sheets=[{'upload':upload['id'],'title':'合成图','geometry_reviewed':True,'dimensions':[]}]
    def run(action):
        response=client.post('/api/delivery/run',headers=headers,json={'action':action,'sheets':sheets})
        assert response.status_code==200,response.text
        job=response.json()
        for _ in range(200):
            job=client.get('/api/jobs/'+job['id']).json()
            if job['status']!='running': break
            time.sleep(.05)
        return job
    checked=run('check'); assert checked['status']=='checked',checked
    assert checked['audit']['sheets'][0]['warnings']
    job=run('build'); assert job['status']=='visual_review',job
    assert client.get('/api/files/'+job['id']+'/sheet1.pdf').content.startswith(b'%PDF')
    endpoint='/api/delivery/'+job['id']+'/package'
    assert client.post(endpoint,headers=headers,json={'reviewed':[]}).status_code==400
    packed=client.post(endpoint,headers=headers,json={'reviewed':['sheet1']})
    assert packed.status_code==200,packed.text
    assert 'delivery.zip' in packed.json()['files']
    assert client.get('/api/files/'+job['id']+'/delivery.zip').content.startswith(b'PK')
    assert client.post(endpoint,headers=headers,json={'reviewed':['sheet1']}).status_code==409
    sheets[0]['geometry_reviewed']=False
    assert run('build')['status']=='error'
    assert source.read_bytes()==(tmp_path/'data'/upload['id']/'source.dxf').read_bytes()


def test_home_routes_to_v2_workbench(tmp_path):
    client=TestClient(create_app(tmp_path))
    page=client.get('/')
    assert page.url.path=='/studio/studio.html'
    assert 'photo-folder' in page.text
    assert client.get('/studio/studio-flow.js').status_code==200
    assert client.get('/legacy').status_code==200
