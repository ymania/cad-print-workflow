/* Progressive workbench; all geometry and consent gates stay in existing tools. */
'use strict';
(function(){
const by=id=>document.getElementById(id),W=StudioWorkbench;
let items=[],mainHash=null,step=1,ingesting=false;
by('flow-nav').append(by('save')); // Save remains accessible at every stage.
const aside=document.querySelector('aside'),prep=document.createElement('div'),review=document.createElement('div'),output=document.createElement('div'),manual=document.createElement('details');
manual.innerHTML='<summary>手动构造（可选）</summary>';
let area=review;
for(const node of Array.from(aside.childNodes)){
 if(node.nodeName==='H2'){
  if(node.textContent.startsWith('1 ·')||node.textContent.startsWith('2 ·'))area=prep;
  else if(node.textContent.startsWith('3 ·'))area=manual;
  else if(node.textContent.startsWith('4 ·'))area=output;
 }
 area.append(node);
}
aside.append(prep,review,output);prep.append(manual);
const agent=document.querySelector('.agent-panel'),intro=document.querySelector('main>section'),gallery=by('source-gallery');
const local=['localhost','127.0.0.1'].includes(location.hostname)&&location.pathname.startsWith('/studio/');
if(local){const more=document.createElement('details'),summary=document.createElement('summary'),a=document.createElement('a');summary.textContent='已有DXF？检查与打印整套作业';a.href='/delivery';a.textContent='打开本机交付台';more.append(summary,a);output.append(more);}
function show(n){const state=W.state();if(state.working||ingesting)return;
 if(n>1&&!state.calibrated){by('flow-hint').textContent='先完成纸面校正，再点选一条已知尺寸的两个端点。';return;}
 step=n;intro.hidden=n!==1;prep.hidden=n!==1;agent.hidden=n!==2;review.hidden=n!==2;output.hidden=n!==3;
 document.querySelectorAll('#flow-nav button[data-step]').forEach(b=>b.setAttribute('aria-current',Number(b.dataset.step)===n?'step':'false'));
 by('flow-hint').textContent=['','先导入图片，选择主图；原图方正时可跳过透视校正，然后标定一个已知尺寸。','选模型、填Key和绘图要求，授权后启动。只在图上确认需要你决定的尺寸。','核对叠图后导出。若还有未确认尺寸，程序会阻止最终导出。'][n];
}
for(const b of document.querySelectorAll('#flow-nav button[data-step]'))b.onclick=()=>show(Number(b.dataset.step));
function next(parent,label,n){const b=document.createElement('button');b.textContent=label;b.className='primary';b.onclick=()=>show(n);parent.append(b);}
next(prep,'下一步：识别与确认',2);next(review,'下一步：导出图纸',3);
function refs(){StudioAgent.setReferences(items.filter(x=>x.hash!==mainHash));}
function galleryRender(){gallery.replaceChildren();for(const item of items){const b=document.createElement('button'),img=document.createElement('img'),label=document.createElement('span');b.type='button';img.src=item.data;img.alt='';label.textContent=(item.hash===mainHash?'当前主图 · ':'设为主图 · ')+item.name;b.append(img,label);b.setAttribute('aria-pressed',String(item.hash===mainHash));b.disabled=W.state().working;b.onclick=()=>select(item);gallery.append(b);}}
async function select(item){if(W.state().working||ingesting||item.hash===mainHash)return;if(W.state().loaded&&!confirm('切换主图会清除当前校正、标定和绘图草稿。需要保留时请先保存项目。继续切换？'))return;
 try{W.lock(true);await W.loadImage(item.data);mainHash=item.hash;refs();galleryRender();}catch(e){W.say(e.message)}finally{W.lock(false);galleryRender();}}
async function ingest(files){if(W.state().working||ingesting)return;ingesting=true;W.lock(true);try{
 const added=await CADImages.prepare(files,items),batch=[...items,...added.items];
 if(!batch.length)throw Error('没有可用图片，请选择PNG、JPEG或WebP');
 if(!mainHash){if(W.state().loaded&&!confirm('导入新主图会替换当前草稿，请先保存需要保留的项目。继续？'))return;await W.loadImage(batch[0].data);mainHash=batch[0].hash;}
 items=batch;refs();galleryRender();W.say(`共${items.length}张图片：当前主图用于建图，其余自动作为参考。已跳过${added.duplicates}张重复图、${added.skipped}个非图片文件。`);
 }catch(e){W.say(e.message)}finally{ingesting=false;W.lock(false);galleryRender();by('photo').value='';by('photo-folder').value='';}}
by('photo').onchange=()=>ingest(by('photo').files);by('photo-folder').onchange=()=>ingest(by('photo-folder').files);
// Keep project recovery and demos from silently retaining the previous intake batch.
for(const id of ['sample','load'])by(id).addEventListener(id==='load'?'change':'click',()=>{items=[];mainHash=null;galleryRender();});
// Additional reference uploads stay available, but only as an advanced option.
const extra=document.createElement('details'),sum=document.createElement('summary');sum.textContent='单独补充参考图（可选）';extra.append(sum);const refActions=by('agent-references').closest('.actions');refActions.before(extra);extra.append(refActions,by('agent-reference-summary'));
show(1);
})();
