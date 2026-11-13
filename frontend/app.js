'use strict';
const $=id=>document.getElementById(id),core=CADCore,vision=CADVision;
const defaultPreset=vision.presets[0];
let config={...defaultPreset,key:''},selectedPreset=defaultPreset.id,images=[],current=null,busy=false,aborter=null,toastTimer,previewURL=null,downloads=[];
function notice(text){$('toast').textContent=text;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,9000)}
function message(text,role='assistant'){const el=document.createElement('div');el.className='message '+role;el.textContent=text;$('messages').append(el);$('messages').scrollTop=$('messages').scrollHeight}
function trace(items){$('trace').replaceChildren();for(const text of items){const el=document.createElement('div');el.textContent=text;$('trace').append(el)}}
function setBusy(value){busy=value;for(const id of ['send','demo','image','folder','import','apply','settings-open','clear'])$(id).disabled=value;$('spec').disabled=value;$('confirmed').disabled=value;$('cancel').disabled=!value||!aborter;for(const button of $('image-list').querySelectorAll('button'))button.disabled=value||button.dataset.locked==='true';$('build').disabled=value||!current||!$('confirmed').checked;$('save-draft').disabled=value||!current;$('state').textContent=value?'正在调用模型':'就绪'}
function clearFiles(){for(const url of downloads)URL.revokeObjectURL(url);downloads=[];$('files').textContent='等待生成交付文件'}
function clearPreview(){if(previewURL)URL.revokeObjectURL(previewURL);previewURL=null;$('preview').hidden=true;$('preview').removeAttribute('src');$('preview-state').textContent='待预览'}
function renderPreview(spec){clearPreview();try{previewURL=URL.createObjectURL(new Blob([core.svg(spec)],{type:'image/svg+xml'}));$('preview').src=previewURL;$('preview').hidden=false;$('preview-state').textContent='待核对预览'}catch(err){$('preview-state').textContent='排版需调整';notice(err.message)}}
function showSpec(spec){core.validate(spec);current=spec;$('spec').value=JSON.stringify(spec,null,2);$('confirmed').checked=false;clearFiles();$('count').textContent=spec.components.length+' 个构件';$('components').replaceChildren();for(const c of spec.components){const card=document.createElement('div');card.className='component';const title=document.createElement('h3');title.textContent=c.id;card.append(title);const desc=document.createElement('p');desc.textContent=(c.description||'')+` · 纸面比例 ${c.scale??1}:1`;card.append(desc);for(const d of c.dimensions){const row=document.createElement('div');row.className='dimension';row.textContent=d.name+'：'+d.value;const source=document.createElement('small');source.textContent='来源：'+d.source;row.append(source);card.append(row)}$('components').append(card)}$('issues').textContent=spec.unresolved.length?'待确认（解决前不能生成）：\n'+spec.unresolved.map(x=>typeof x==='string'?x:JSON.stringify(x)).join('\n'):'';renderPreview(spec);setBusy(busy)}
function blobLink(name,content,type){const url=URL.createObjectURL(new Blob([content],{type}));downloads.push(url);const a=document.createElement('a');a.href=url;a.download=name;a.textContent=name;$('files').append(a)}
function draft(){const s=JSON.parse($('spec').value);s.reviewed=false;return core.validate(s)}
function resetDrawing(){current=null;images=[];renderImages();$('image').value='';$('folder').value='';$('import').value='';$('spec').value='';$('count').textContent='等待识图';$('issues').textContent='';$('components').textContent='等待图片或参数文件';$('confirmed').checked=false;$('consent').checked=false;clearFiles();clearPreview();trace([]);setBusy(false);status()}
function status(){$('model-status').textContent=config.key?(vision.presets.find(p=>p.id===config.id)?.name||'自定义')+' 已配置':'模型待配置';$('destination').textContent=config.key?'图片接收地址：'+vision.endpoint(config.base)+` · 本次 ${images.length} 张图片`:'尚未配置模型密钥（默认 DeepSeek）'}
function selectProvider(id){
 const preset=vision.presets.find(p=>p.id===id);selectedPreset=id;
 for(const button of $('provider-cards').children)button.setAttribute('aria-pressed',String(button.dataset.provider===id));
 $('base-url').value=preset.base;$('model').value=preset.model;$('key').value='';
 $('advanced-config').open=id==='custom';
 $('provider-info').textContent=id==='custom'?'填写兼容接口、视觉模型名与对应密钥。':`${preset.name} · ${preset.model} · ${preset.note}。`;
}
for(const preset of vision.presets){const button=document.createElement('button');button.type='button';button.className='provider-card';button.dataset.provider=preset.id;const badge=document.createElement('b');badge.textContent=preset.badge;const name=document.createElement('strong');name.textContent=preset.name;const hint=document.createElement('small');hint.textContent=preset.note;button.append(badge,name,hint);button.onclick=()=>selectProvider(preset.id);$('provider-cards').append(button)}
$('settings-open').onclick=()=>{selectProvider(config.id||'custom');$('base-url').value=config.base;$('model').value=config.model;$('settings').showModal()};$('settings-close').onclick=()=>{$('key').value='';$('settings').close()};$('settings').addEventListener('close',()=>$('key').value='');
$('config-form').onsubmit=e=>{e.preventDefault();try{vision.endpoint($('base-url').value.trim());const key=$('key').value.trim()||config.key;if(!key)throw Error('请填写你自己的API Key');const base=$('base-url').value.trim();if(config.base!==base&&!$('key').value.trim())throw Error('更换服务商时请重新填写该服务商的密钥');const model=$('model').value.trim();if(!model)throw Error('请填写模型名称');config={id:selectedPreset,base,model,key};$('key').value='';$('settings').close();$('consent').checked=false;status();notice('配置仅保留在本页内存中，尚未发送任何模型请求')}catch(err){notice(err.message)}};
$('forget').onclick=()=>{config.key='';$('key').value='';$('consent').checked=false;status();notice('已移除本页保存的密钥')};
function invalidateImages(){
 $('confirmed').checked=false;$('consent').checked=false;clearFiles();
 if(current){current.reviewed=false;$('spec').value=JSON.stringify(current,null,2);$('preview-state').textContent='参考图片已变更，请重新识图或核对';}
 renderImages();setBusy(busy);status();
}
function renderImages(){
 $('image-list').replaceChildren();const size=images.reduce((n,x)=>n+x.size,0);
 $('image-summary').textContent=images.length?`已选 ${images.length} / 20 张 · ${(size/1024/1024).toFixed(2)} / 12 MiB · 按下方顺序一起发送，可继续添加、排序或移除`:'尚未选择图片；文件夹中的非图片会跳过，内容重复的图片只保留一份';
 images.forEach((item,index)=>{const card=document.createElement('div');card.className='image-card';const img=document.createElement('img');img.src=item.data;img.alt=`图片${index+1}：${item.name}`;const name=document.createElement('strong');name.textContent=`${index+1}. ${item.name}`;const actions=document.createElement('div');actions.className='actions';
  for(const [label,delta] of [['前移',-1],['后移',1],['移除',0]]){const button=document.createElement('button');button.type='button';button.textContent=label;button.setAttribute('aria-label',`${label}图片${index+1}`);const locked=delta!==0&&(index+delta<0||index+delta>=images.length);button.dataset.locked=String(locked);button.disabled=busy||locked;button.onclick=()=>{if(busy)return;if(delta===0)images.splice(index,1);else [images[index],images[index+delta]]=[images[index+delta],images[index]];invalidateImages()};actions.append(button)}
  card.append(img,name,actions);$('image-list').append(card);
 });
}
async function addImages(input){
 if(busy)return;const files=Array.from(input.files);if(!files.length)return;
 setBusy(true);$('state').textContent='正在读取本地图片';
 try{const result=await CADImages.prepare(files,images);images.push(...result.items);invalidateImages();const summary=`添加 ${result.items.length} 张；跳过 ${result.skipped} 个非图片文件、${result.duplicates} 张重复图片。当前共 ${images.length} 张。`;message(summary);notice(summary);}
 catch(err){notice(err.message)}finally{input.value='';setBusy(false)}
}
$('image').onchange=()=>addImages($('image'));$('folder').onchange=()=>addImages($('folder'));
if(!('webkitdirectory' in $('folder'))){$('folder-label').hidden=true;notice('当前浏览器不支持文件夹选择，请使用多选图片')}
$('import').onchange=async()=>{const file=$('import').files[0];if(!file)return;try{if(file.size>4*1024*1024)throw Error('参数文件不能超过4MB');const spec=JSON.parse(await file.text());spec.reviewed=false;core.validate(spec);resetDrawing();showSpec(spec);message('已导入本地参数；不调用模型。请重新核对后导出。')}catch(err){notice(err.message)}finally{$('import').value=''}};
$('demo').onclick=()=>{resetDrawing();showSpec(structuredClone(core.demo));trace(['已载入合成兼容性示例','预览在浏览器本地生成']);message('这是合成示例，不是识图结果。可以核对后直接导出DXF、PDF或FreeCAD宏。')};
$('apply').onclick=()=>{try{showSpec(draft());notice('结构已校验，预览已更新；仍需人工核对几何')}catch(err){clearFiles();clearPreview();notice(err.message)}};
$('spec').oninput=()=>{$('confirmed').checked=false;clearFiles();clearPreview();$('preview-state').textContent='数据已修改，请校验';setBusy(busy)};
$('confirmed').onchange=()=>setBusy(busy);
$('save-draft').onclick=()=>{try{const s=draft(),url=URL.createObjectURL(new Blob([JSON.stringify(s,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='cad-draft.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),60000)}catch(err){notice(err.message)}};
$('chat-form').onsubmit=async e=>{e.preventDefault();if(busy)return;let previous;try{if(!images.length)throw Error('请先选择原始图片；参数文件和示例可以直接导出，无需识图');if(!config.key)throw Error('请先配置视觉模型与API Key');if(!$('consent').checked)throw Error('请确认图片接收地址，并勾选发送许可');previous=current?draft():null;}catch(err){notice(err.message);return}const instruction=$('prompt').value;message(instruction,'user');aborter=new AbortController();setBusy(true);const timer=setTimeout(()=>aborter.abort(),120000);trace(['正在直接请求：'+new URL(config.base).origin,'本站不提供中转；等待模型返回']);try{const spec=await vision.recognize({...config,images:images.map(({name,data})=>({name,data})),instruction,previous,signal:aborter.signal});showSpec(spec);$('prompt').value='';$('consent').checked=false;trace(['视觉模型已返回','结构校验通过（不等于尺寸正确）','请核对尺寸来源与几何预览']);message(`识别到 ${spec.components.length} 个构件，${spec.unresolved.length} 个待确认项。可以继续发送修订要求。`)}catch(err){trace(['本次识图未完成']);message(err.message);notice(err.message)}finally{clearTimeout(timer);aborter=null;setBusy(false)}};
$('cancel').onclick=()=>aborter?.abort();
$('build').onclick=()=>{try{if(!$('confirmed').checked)throw Error('请先核对并确认');const spec=draft();spec.reviewed=true;core.validate(spec,true);core.pageCheck(spec);const files=[['drawing.dxf',core.dxf(spec),'application/dxf'],['drawing.pdf',core.pdf(spec),'application/pdf'],['drawing.svg',core.svg(spec),'image/svg+xml'],['build.FCMacro',core.macro(spec),'text/plain'],['reviewed.json',JSON.stringify(spec,null,2),'application/json'],['report.json',JSON.stringify(core.report(spec),null,2),'application/json']];clearFiles();$('files').replaceChildren();for(const args of files)blobLink(...args);current=spec;renderPreview(spec);$('preview-state').textContent='已生成 · 请复核';trace(['结构与A3边界检查通过','DXF、PDF、SVG与FreeCAD宏在浏览器生成','未向网络发送图纸或密钥']);message('交付文件已在本机生成。DXF可用LibreCAD编辑；FreeCAD宏在本机执行后生成FCStd。')}catch(err){clearFiles();notice(err.message);message(err.message)}};
$('clear').onclick=()=>{resetDrawing();config={...defaultPreset,key:''};$('key').value='';$('prompt').value='';$('messages').replaceChildren();message('本次会话和密钥已清空。已下载的文件不会被删除。');status()};
renderImages();status();
