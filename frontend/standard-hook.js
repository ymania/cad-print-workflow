/* Independent analytic construction for the upright textbook hook family. */
(function(root){
'use strict';
function construct(p){
 const keys=['shaftDiameter','shoulderDiameter','shaftLength','shoulderHeight','offset','drop','r28','r40','r32','innerDiameter','tipRadius','lipRadius','returnRadius'];
 for(const k of keys)if(!Number.isFinite(p[k])||p[k]<=0)throw Error('请提供正的实际毫米尺寸：'+k);
 const d=p.shoulderDiameter/2,ri=p.innerDiameter/2;
 if(p.shaftDiameter>=p.shoulderDiameter)throw Error('轴径必须小于轴肩直径');
 function sqrt(v){if(v<=0)throw Error('尺寸无法形成指定相切分支');return Math.sqrt(v)}
 const ci=[0,0],co=[p.offset,0],c40=[p.r40-d,sqrt((p.r40+ri)**2-(p.r40-d)**2)],c28=[d+p.r28,sqrt((p.r28+p.r32)**2-(d+p.r28-p.offset)**2)],c15=[p.offset-p.r32-p.lipRadius,0],cr=[-sqrt((p.returnRadius+ri)**2-p.drop**2),-p.drop];
 if(p.shoulderHeight<=Math.max(c40[1],c28[1]))throw Error('轴肩高度不足以容纳相切过渡');
 const rA=p.lipRadius+p.tipRadius,rB=p.returnRadius-p.tipRadius;
 if(rB<=0)throw Error('钩尖半径必须小于回转圆弧半径');
 const dx=cr[0]-c15[0],dy=cr[1]-c15[1],dist=Math.hypot(dx,dy);
 if(dist<=0||dist>=rA+rB||dist<=Math.abs(rA-rB))throw Error('钩尖两圆没有有效交点');
 const a=(rA*rA-rB*rB+dist*dist)/(2*dist),h=sqrt(rA*rA-a*a),base=[c15[0]+a*dx/dist,c15[1]+a*dy/dist];
 const c3=[[base[0]-h*dy/dist,base[1]+h*dx/dist],[base[0]+h*dy/dist,base[1]-h*dx/dist]].sort((a,b)=>b[1]-a[1])[0];
 const tangent=(c,r,o)=>{const l=Math.hypot(o[0]-c[0],o[1]-c[1]);return c.map((x,i)=>x+r*(o[i]-x)/l)};
 const angle=(c,t)=>(Math.atan2(t[1]-c[1],t[0]-c[0])*180/Math.PI+360)%360;
 const ti=tangent(ci,ri,c40),to=tangent(co,p.r32,c28),tr=tangent(ci,ri,cr),tl=tangent(c15,p.lipRadius,c3),tt=tangent(cr,p.returnRadius,c3);
 const entities=[],constraints=[],anchor=[0,0];
 const points=[[-d,c40[1]],[-d,p.shoulderHeight],[-p.shaftDiameter/2,p.shoulderHeight],[-p.shaftDiameter/2,p.shoulderHeight+p.shaftLength],[p.shaftDiameter/2,p.shoulderHeight+p.shaftLength],[p.shaftDiameter/2,p.shoulderHeight],[d,p.shoulderHeight],[d,c28[1]]];
 for(let i=0;i<7;i++)entities.push({id:'line'+i,type:'line',start:points[i],end:points[i+1],role:'outline'});
 function arc(id,c,r,a,b){entities.push({id,type:'arc',center:c,radius:r,start_angle:a,end_angle:b,role:'outline'});constraints.push({id:'radius_'+id,type:'radius',entity:id,value:r,label:id+'半径',source:'用户参数，经解析构造',anchor})}
 arc('a28',c28,p.r28,180,angle(c28,to));arc('a32',co,p.r32,180,angle(co,to));arc('a15',c15,p.lipRadius,0,angle(c15,tl));arc('a3',c3,p.tipRadius,angle(c3,tt),angle(c3,tl));arc('a27',cr,p.returnRadius,angle(cr,tr),angle(cr,tt));arc('inner',ci,ri,angle(ci,tr),angle(ci,ti));arc('a40',c40,p.r40,180,angle(c40,ti));
 for(const [entity,other,branch]of [['a40','inner','external'],['a28','a32','external'],['a32','a15','external'],['inner','a27','external'],['a15','a3','external'],['a27','a3','internal'],['line0','a40',undefined],['line6','a28',undefined]])constraints.push({id:'t_'+entity+'_'+other,type:'tangent',entity,other,branch,label:entity+'与'+other+'相切',source:'标准吊钩构造关系',anchor});
 return{version:1,entities,constraints,closedPaths:[{id:'hook',anchor,entities:['line0','line1','line2','line3','line4','line5','line6','a28',{id:'a32',reverse:true},'a15',{id:'a3',reverse:true},{id:'a27',reverse:true},'inner',{id:'a40',reverse:true}]}],questions:[],notes:['仅适用竖直轴、指定内外切分支的教材吊钩。坐标为实际毫米；照片定位与尺寸来源需另行核对。']};
}
const api={construct};root.CADStandardHook=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
