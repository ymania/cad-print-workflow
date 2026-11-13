/* Pure geometry and exports. No network, storage or third-party runtime. */
(function(root){
'use strict';
const roles={outline:{width:.5,dash:[]},thin:{width:.18,dash:[]},center:{width:.18,dash:[8,2,1,2]},dashed:{width:.18,dash:[4,2]},hatch:{width:.18,dash:[]},dimension:{width:.18,dash:[]}};
const num=x=>{if(typeof x!=='number'||!Number.isFinite(x)||Math.abs(x)>1e6)throw Error('数值必须为有限数字，绝对值不超过 1000000');return x};
const pt=p=>{if(!Array.isArray(p)||p.length!==2)throw Error('坐标必须是 [x,y]');return p.map(num)};
const f=x=>Number(x.toFixed(6)).toString();
function validate(s,review=false){
 if(!s||s.version!==1||s.units!=='mm'||!Array.isArray(s.unresolved)||typeof s.reviewed!=='boolean')throw Error('需要 version:1、units:mm、reviewed 和 unresolved 列表');
 if(s.notes!==undefined&&(!Array.isArray(s.notes)||s.notes.some(x=>typeof x!=='string')))throw Error('notes必须为中文说明字符串列表');
 if(review&&(!s.reviewed||s.unresolved.length))throw Error('请先解决待确认项并核对几何');
 if(!Array.isArray(s.components)||!s.components.length||s.components.length>200)throw Error('构件数量须在1到200之间');
 const ids=new Set();let count=0;
 for(const c of s.components){
  if(typeof c.id!=='string'||!c.id||c.id.length>150||ids.has(c.id))throw Error('每个构件需要唯一名称（最多150字符）');ids.add(c.id);
  if(!Array.isArray(c.dimensions)||!Array.isArray(c.entities))throw Error('构件需要 dimensions 和 entities 列表');
  if(c.scale!==undefined&&(num(c.scale)<=0||c.scale>100))throw Error('绘图比例须大于0且不超过100');if(c.offset!==undefined)pt(c.offset);
  for(const d of c.dimensions){num(d.value);if(typeof d.name!=='string'||typeof d.source!=='string'||!d.source.trim())throw Error('尺寸必须有名称、数值与来源');}
  if(review&&!c.entities.length)throw Error('构件没有可绘制几何');
  for(const e of c.entities){
   if(++count>20000)throw Error('最多支持20000个图元');
   if(!Object.hasOwn(roles,e.role))throw Error('未知图层用途');
   if(e.type==='line'){pt(e.start);pt(e.end);if(Math.hypot(e.start[0]-e.end[0],e.start[1]-e.end[1])<1e-8)throw Error('直线长度为零');}
   else if(e.type==='circle'||e.type==='arc'){pt(e.center);if(num(e.radius)<=0)throw Error('半径必须大于0');if(e.type==='arc'){num(e.start_angle);num(e.end_angle);if(e.start_angle<0||e.start_angle>=360||e.end_angle<0||e.end_angle>=360||e.start_angle===e.end_angle)throw Error('圆弧角度须不同且在0到360之间');}}
   else throw Error('仅支持 line、circle、arc；其他图元必须明确转换，不能跳过');
  }
 }
 return s;
}
function entities(s){validate(s);return s.components.flatMap(c=>c.entities.map(e=>{const scale=c.scale??1,offset=c.offset??[0,0],p=a=>a.map((v,i)=>v*scale+offset[i]);return e.type==='line'?{...e,start:p(e.start),end:p(e.end)}:{...e,center:p(e.center),radius:e.radius*scale}}));}
const rad=a=>a*Math.PI/180;
const at=(e,a)=>[e.center[0]+e.radius*Math.cos(rad(a)),e.center[1]+e.radius*Math.sin(rad(a))];
function sweep(e){return (e.end_angle-e.start_angle+360)%360;}
function boundary(e){if(e.type==='line')return[e.start,e.end];if(e.type==='circle')return[0,90,180,270].map(a=>at(e,a));return[e.start_angle,e.end_angle,...[0,90,180,270].filter(a=>(a-e.start_angle+360)%360<=sweep(e))].map(a=>at(e,a));}
function pageCheck(s){for(const e of entities(s))for(const p of boundary(e)){const w=roles[e.role].width/2;if(p[0]-w<0||p[1]-w<0||p[0]+w>420||p[1]+w>297)throw Error('图形（含线宽）超出A3横向420×297mm，请调整构件 offset/scale；不会自动缩放');}}
function svg(s){pageCheck(s);const paths=entities(s).map(e=>{const style=roles[e.role],attr=`fill="none" stroke="black" stroke-width="${style.width}"${style.dash.length?` stroke-dasharray="${style.dash.join(' ')}"`:''}`;
 if(e.type==='line')return`<path ${attr} d="M ${e.start.map(f).join(' ')} L ${e.end.map(f).join(' ')}"/>`;
 if(e.type==='circle')return`<circle ${attr} cx="${f(e.center[0])}" cy="${f(e.center[1])}" r="${f(e.radius)}"/>`;
 return`<path ${attr} d="M ${at(e,e.start_angle).map(f).join(' ')} A ${f(e.radius)} ${f(e.radius)} 0 ${sweep(e)>180?1:0} 1 ${at(e,e.end_angle).map(f).join(' ')}"/>`;
 }).join('\n');return`<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" viewBox="0 0 420 297"><rect width="420" height="297" fill="white"/><g transform="translate(0 297) scale(1 -1)">${paths}</g></svg>`;}
function dxf(s){validate(s,true);pageCheck(s);const lines=[];const p=(...a)=>lines.push(...a.map(String));
 p(0,'SECTION',2,'HEADER',9,'$ACADVER',1,'AC1015',9,'$INSUNITS',70,4,9,'$MEASUREMENT',70,1,9,'$LUNITS',70,2,9,'$LUPREC',70,4,9,'$LTSCALE',40,1,9,'$LWDISPLAY',290,1,0,'ENDSEC');
 p(0,'SECTION',2,'TABLES',0,'TABLE',2,'LTYPE',5,'10',100,'AcDbSymbolTable',70,3);
 for(const [name,segments] of [['CONTINUOUS',[]],['CENTER',[8,-2,1,-2]],['DASHED',[4,-2]]]){p(0,'LTYPE',100,'AcDbSymbolTableRecord',100,'AcDbLinetypeTableRecord',2,name,70,0,3,name,72,65,73,segments.length,40,segments.reduce((a,b)=>a+Math.abs(b),0));for(const n of segments)p(49,n,74,0);}
 p(0,'ENDTAB',0,'TABLE',2,'LAYER',5,'20',100,'AcDbSymbolTable',70,Object.keys(roles).length+1);
 for(const name of ['0',...Object.keys(roles)])p(0,'LAYER',100,'AcDbSymbolTableRecord',100,'AcDbLayerTableRecord',2,name,70,0,62,7,6,name==='center'?'CENTER':name==='dashed'?'DASHED':'CONTINUOUS',370,Math.round((roles[name]?.width??.18)*100));
 p(0,'ENDTAB',0,'ENDSEC',0,'SECTION',2,'BLOCKS',0,'ENDSEC',0,'SECTION',2,'ENTITIES');
 for(const e of entities(s)){p(0,e.type.toUpperCase(),100,'AcDbEntity',8,e.role,62,256,6,'BYLAYER',370,-1);
 if(e.type==='line')p(100,'AcDbLine',10,f(e.start[0]),20,f(e.start[1]),30,0,11,f(e.end[0]),21,f(e.end[1]),31,0);
 else{p(100,'AcDbCircle',10,f(e.center[0]),20,f(e.center[1]),30,0,40,f(e.radius));if(e.type==='arc')p(100,'AcDbArc',50,e.start_angle,51,e.end_angle);}}
 p(0,'ENDSEC',0,'EOF');return lines.join('\n')+'\n';
}
function bezier(e){const a=e.type==='circle'?0:e.start_angle,delta=e.type==='circle'?360:sweep(e),n=Math.ceil(delta/90),result=[];for(let i=0;i<n;i++){const t=rad(a+delta*i/n),u=rad(a+delta*(i+1)/n),k=4/3*Math.tan((u-t)/4),r=e.radius,[x,y]=e.center;const p=[x+r*Math.cos(t),y+r*Math.sin(t)],q=[x+r*Math.cos(u),y+r*Math.sin(u)];result.push([p,[p[0]-k*r*Math.sin(t),p[1]+k*r*Math.cos(t)],[q[0]+k*r*Math.sin(u),q[1]-k*r*Math.cos(u)],q]);}return result;}
function pdf(s){validate(s,true);pageCheck(s);const commands=['q','2.834645669291339 0 0 2.834645669291339 0 0 cm','0 G','0 J','0 j'];for(const e of entities(s)){const style=roles[e.role];commands.push(`${style.width} w`,`[${style.dash.join(' ')}] 0 d`);if(e.type==='line')commands.push(`${e.start.map(f).join(' ')} m`,`${e.end.map(f).join(' ')} l`);else{const segments=bezier(e);commands.push(`${segments[0][0].map(f).join(' ')} m`);for(const seg of segments)commands.push(`${seg.slice(1).flat().map(f).join(' ')} c`);if(e.type==='circle')commands.push('h');}commands.push('S');}commands.push('Q');const stream=commands.join('\n')+'\n';
 const objects=['<< /Type /Catalog /Pages 2 0 R >>','<< /Type /Pages /Kids [3 0 R] /Count 1 >>','<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1190.551181 841.889764] /Resources << >> /Contents 4 0 R >>',`<< /Length ${stream.length} >>\nstream\n${stream}endstream`];
 let result='%PDF-1.4\n',offsets=[0];for(let i=0;i<objects.length;i++){offsets.push(result.length);result+=`${i+1} 0 obj\n${objects[i]}\nendobj\n`;}const xref=result.length;result+=`xref\n0 ${objects.length+1}\n0000000000 65535 f \n`;for(const o of offsets.slice(1))result+=`${String(o).padStart(10,'0')} 00000 n \n`;return result+`trailer\n<< /Size ${objects.length+1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
}
function macro(s){validate(s,true);const literal=JSON.stringify(JSON.stringify(s)).replace(/[^\x00-\x7F]/g,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0'));return`# Generated data-only geometry; run in FreeCAD. Actual dimensions, no paper scaling.\nimport json, math\nfrom pathlib import Path\nimport FreeCAD as App\nimport Part\nspec = json.loads(${literal})\ndoc = App.newDocument("BrowserGeometry")\nfor i, c in enumerate(spec['components']):\n    sketch = doc.addObject('Sketcher::SketchObject', 'Component%d' % i)\n    sketch.Label = c['id']\n    sketch.addProperty('App::PropertyString', 'DimensionEvidence')\n    sketch.DimensionEvidence = json.dumps(c['dimensions'], ensure_ascii=False)\n    for e in c['entities']:\n        def v(p): return App.Vector(p[0], p[1], 0)\n        if e['type'] == 'line':\n            g = Part.LineSegment(v(e['start']), v(e['end']))\n        else:\n            circle = Part.Circle(v(e['center']), App.Vector(0,0,1), e['radius'])\n            if e['type'] == 'circle': g = circle\n            else:\n                a, b = e['start_angle'], e['end_angle']\n                if b <= a: b += 360\n                g = Part.ArcOfCircle(circle, math.radians(a), math.radians(b))\n        sketch.addGeometry(g, e['role'] == 'center')\ndoc.recompute()\noutput = Path(__file__).resolve().with_name('model.FCStd')\nif output.exists(): raise RuntimeError('model.FCStd already exists; choose another folder')\ndoc.saveAs(str(output))\nif App.GuiUp:\n    import FreeCADGui as Gui\n    Gui.activeDocument().activeView().viewTop()\n    Gui.activeDocument().activeView().fitAll()\n`;}
function report(s){validate(s,true);pageCheck(s);return{format:'browser-cad-report-v1',page_mm:[420,297],units:'mm',entities:entities(s).length,components:s.components.map(c=>({id:c.id,paper_scale:c.scale??1,offset:c.offset??[0,0]})),warnings:['人工核对尺寸与几何；证据列表不自动驱动几何。','DXF/PDF/SVG应用构件绘图比例；FreeCAD宏保留实际尺寸。','仅支持线、圆、圆弧；尺寸文字与原生DIMENSION尚不自动生成。','FreeCAD草图未完全约束；导出文件之间不自动联动。','打印选A3横向、实际大小100%，关闭页眉页脚。'],visual_review_required:true};}
const demo={version:1,units:'mm',reviewed:false,unresolved:[],components:[{id:'圆与中心线',description:'合成兼容性示例，直径80mm',dimensions:[{name:'直径',value:80,source:'内置示例明确指定'}],entities:[{type:'circle',center:[80,90],radius:40,role:'outline'},{type:'line',start:[32,90],end:[128,90],role:'center'},{type:'line',start:[80,42],end:[80,138],role:'center'},{type:'arc',center:[190,90],radius:35,start_angle:330,end_angle:120,role:'outline'},{type:'line',start:[40,190],end:[240,190],role:'outline'},{type:'line',start:[40,180],end:[240,180],role:'thin'},{type:'line',start:[40,170],end:[240,170],role:'dashed'},{type:'line',start:[40,160],end:[240,160],role:'center'}]}]};
const api={validate,entities,pageCheck,svg,dxf,pdf,macro,report,demo,bezier};root.CADCore=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
