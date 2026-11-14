(function(root){
'use strict';
const fields={shaftDiameter:'轴直径',shoulderDiameter:'轴肩直径',shaftLength:'轴段长度',shoulderHeight:'轴肩至内圆中心高度',offset:'主圆心横向偏置',drop:'回转圆心下移',r28:'上过渡半径',r40:'内过渡半径',r32:'外轮廓半径',innerDiameter:'内圆直径',tipRadius:'尖端半径',lipRadius:'外唇半径',returnRadius:'回转半径'};
function prepare(input,context={}){
 if(!input.hook)return input;
 const h=JSON.parse(JSON.stringify(input.hook));
 if(!h.params||!Array.isArray(h.origin)||h.origin.length!==2||h.origin.some(x=>!Number.isFinite(x)||Math.abs(x)>1e5)||!Number.isFinite(context.mmPerPixel)||context.mmPerPixel<=0)throw Error('吊钩需要实际尺寸、内圆中心位置和有效标定');
 for(const key of Object.keys(fields))if(typeof h.sources?.[key]!=='string'||!h.sources[key].trim())throw Error(fields[key]+'缺少尺寸来源');
 const p=root.CADStandardHook.construct(h.params);
 for(const e of p.entities)for(const k of ['start','end','center'])if(e[k])e[k]=e[k].map((x,i)=>x+h.origin[i]);
 const anchor=[h.origin[0]/context.mmPerPixel,-h.origin[1]/context.mmPerPixel];
 p.constraints.forEach(c=>c.anchor=anchor);p.closedPaths.forEach(c=>c.anchor=anchor);
 p.hook=h;p.questions=input.questions||[];p.notes.push('13项构造尺寸须在吊钩参数区核对；只适用当前教材构型。');return p;
}
root.CADHookAdapter={fields,prepare};if(typeof module!=='undefined')module.exports=root.CADHookAdapter;
})(globalThis);
