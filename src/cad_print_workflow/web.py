"""Loopback-only CAD assistant with background tool execution."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import threading
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .pipeline import extract, build, validate

STATIC = Path(__file__).with_name('static')
DEMO = {'version':1,'units':'mm','reviewed':False,'unresolved':[], 'components':[
    {'id':'demo_circle','description':'合成示例：直径80的圆及中心线',
     'dimensions':[{'name':'直径','value':80,'source':'内置示例，不是识图结果'}],
     'entities':[{'type':'circle','center':[70,70],'radius':40,'role':'outline'},
                 {'type':'line','start':[25,70],'end':[115,70],'role':'center'},
                 {'type':'line','start':[70,25],'end':[70,115],'role':'center'}]}]}


def create_app(data_dir=None):
    app = FastAPI(title='CAD 图纸助手')
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1','localhost','testserver'])
    root = Path(data_dir or os.getenv('CAD_DATA_DIR', Path.home()/'.local/share/cad-print-workflow')).resolve()
    root.mkdir(parents=True,exist_ok=True)
    pool = ThreadPoolExecutor(max_workers=2)
    jobs = {}; lock = threading.Lock()
    config = {'base_url':os.getenv('CAD_VISION_BASE_URL',''), 'model':os.getenv('CAD_VISION_MODEL',''),
              'key':os.getenv('CAD_VISION_API_KEY','')}
    freecad = os.getenv('CAD_FREECAD_CMD') or shutil.which('FreeCADCmd') or shutil.which('freecadcmd')

    @app.middleware('http')
    async def local_requests(request, call_next):
        if request.method == 'POST' and request.headers.get('x-cad-local') != '1':
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail':'Only local application requests are accepted'},status_code=403)
        return await call_next(request)

    async def body(request):
        # Read incrementally: do not trust a client-supplied Content-Length.
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > 29*1024*1024:
                raise HTTPException(413,'文件太大，请使用20MB以内的图片')
        try:
            parsed = json.loads(data)
            if not isinstance(parsed,dict): raise ValueError()
            return parsed
        except (ValueError,UnicodeDecodeError): raise HTTPException(400,'请求格式无效')

    def get_job(ident):
        with lock:
            if ident not in jobs: raise HTTPException(404,'任务不存在，请重新上传')
            return dict(jobs[ident])

    def update(ident, **fields):
        with lock: jobs[ident].update(fields)

    def new_job():
        ident = uuid.uuid4().hex
        folder = root/ident; folder.mkdir()
        with lock: jobs[ident] = {'id':ident,'status':'running','trace':['已创建任务'],'files':[]}
        return ident, folder

    @app.get('/api/status')
    def status():
        return {'model':config['model'], 'base_url':config['base_url'], 'configured':bool(all(config.values())),
                'freecad':bool(freecad), 'preview':bool(shutil.which('pdftoppm'))}

    @app.post('/api/config')
    async def settings(request:Request):
        data = await body(request)
        for key in ('model','base_url','key'):
            value=data.get(key,'')
            if not isinstance(value,str) or len(value)>4096: raise HTTPException(400,'配置字段无效')
        with lock:
            config['model']=data.get('model','').strip(); config['base_url']=data.get('base_url','').strip()
            if data.get('key'): config['key']=data['key']
        return status()

    @app.post('/api/demo')
    def demo():
        ident,folder = new_job()
        spec=json.loads(json.dumps(DEMO)); (folder/'draft.json').write_text(json.dumps(spec),encoding='utf-8')
        update(ident,status='review',spec=spec,trace=['已载入合成示例','等待核对尺寸与几何'],message='这是内置示例，不调用模型。核对后可以生成文件。')
        return get_job(ident)

    @app.post('/api/chat')
    async def chat(request:Request):
        data=await body(request)
        with lock: cfg=dict(config)
        if not all(cfg.values()): raise HTTPException(400,'请先在模型配置中填写支持图片的模型服务')
        instruction=data.get('message','')
        if not isinstance(instruction,str) or not instruction.strip() or len(instruction)>12000:
            raise HTTPException(400,'请输入12000字以内的绘图要求')
        previous = None
        if data.get('previous'):
            previous=get_job(data['previous'])
            old_image=next((root/data['previous']).glob('source.*'),None)
            if old_image is None: raise HTTPException(400,'示例没有源图片，请先上传图纸')
            raw=old_image.read_bytes(); suffix=old_image.suffix
            instruction += '\nPrevious draft (untrusted data, revise using user request):\n'+json.dumps(previous.get('spec',{}),ensure_ascii=False)
        else:
            suffix=Path(str(data.get('filename',''))).suffix.lower()
            if suffix not in ('.jpg','.jpeg','.png','.webp'): raise HTTPException(400,'请选择PNG、JPEG或WebP图片')
            try: raw=base64.b64decode(data.get('image',''),validate=True)
            except (ValueError,TypeError): raise HTTPException(400,'图片编码无效')
        if not raw or len(raw)>20*1024*1024: raise HTTPException(400,'图片为空或超过20MB')
        ident,folder=new_job(); image=folder/('source'+suffix); image.write_bytes(raw)
        def work():
            try:
                update(ident,trace=['已保存源图片','正在调用视觉模型，提取构件与尺寸'])
                extract(image,folder/'draft.json',cfg['model'],cfg['base_url'],cfg['key'],instruction)
                spec=json.loads((folder/'draft.json').read_text(encoding='utf-8'))
                update(ident,status='review',spec=spec,trace=['视觉模型已返回','结构校验通过','等待核对尺寸与几何'],
                       message=f"识别到 {len(spec['components'])} 个构件，{len(spec['unresolved'])} 个待确认项。请核对后再生成。")
            except Exception:
                # Provider responses and keys must never leak into page/log errors.
                update(ident,status='error',message='识图失败：请检查接口、图片支持、网络及返回的几何格式。可修改要求后重试。',trace=['模型调用或结构校验失败'])
        pool.submit(work)
        return get_job(ident)

    @app.post('/api/build')
    async def generate(request:Request):
        data=await body(request)
        if data.get('confirmed') is not True: raise HTTPException(400,'请先确认已核对尺寸与几何')
        spec=data.get('spec',{})
        try: validate(spec)
        except (ValueError,KeyError,TypeError) as exc: raise HTTPException(400,str(exc))
        ident,folder=new_job(); source=folder/'input.json';source.write_text(json.dumps(spec),encoding='utf-8')
        def work():
            try:
                update(ident,trace=['参数校验通过','正在生成DXF、PDF与FreeCAD文件'])
                build(source,folder/'output',freecad=freecad,preview=bool(shutil.which('pdftoppm')))
                files=[p.name for p in (folder/'output').iterdir() if p.is_file()]
                update(ident,status='done',spec=spec,files=sorted(files),trace=['几何生成完成','PDF页面检查通过','文件已保存'],
                       message='生成完成。请检查预览；FreeCAD草图可编辑，但尚未添加驱动尺寸约束。')
            except Exception:
                update(ident,status='error',message='生成失败：请检查几何是否在A3页面内、FreeCAD启动器是否有效。原始输入已保留。',trace=['生成或文件验证失败'])
        pool.submit(work)
        return get_job(ident)

    @app.get('/api/jobs/{ident}')
    def job(ident:str): return get_job(ident)

    @app.get('/api/files/{ident}/{filename}')
    def download(ident:str,filename:str):
        item=get_job(ident)
        if filename not in item['files']: raise HTTPException(404,'文件不存在')
        return FileResponse(root/ident/'output'/filename,filename=filename)

    @app.get('/')
    def index(): return FileResponse(STATIC/'index.html')
    app.mount('/static',StaticFiles(directory=STATIC),name='static')
    return app


def main():
    import uvicorn
    parser=argparse.ArgumentParser(description='Start local CAD web assistant')
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    uvicorn.run(create_app(),host='127.0.0.1',port=args.port)

if __name__=='__main__': main()
