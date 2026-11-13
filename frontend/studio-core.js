/* Deterministic geometry for the interactive workbench; no network. */
(function(root){
'use strict';
const finite=x=>typeof x==='number'&&Number.isFinite(x);
function homography(from,to){
 if(from.length!==4||to.length!==4)throw Error('需要四个角点');
 function check(p){if(p.some(q=>q.length!==2||!q.every(finite)))throw Error('角点无效');const cross=p.map((a,i)=>{const b=p[(i+1)%4],c=p[(i+2)%4];return(b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0])});if(!cross.every(x=>x>1e-6)&&!cross.every(x=>x< -1e-6))throw Error('四角必须沿纸面顺序围成凸四边形，不能交叉或重合');}check(from);check(to);
 const rows=[];from.forEach(([x,y],i)=>{const[u,v]=to[i];rows.push([x,y,1,0,0,0,-u*x,-u*y,u],[0,0,0,x,y,1,-v*x,-v*y,v]);});
 for(let i=0;i<8;i++){let k=i;for(let j=i+1;j<8;j++)if(Math.abs(rows[j][i])>Math.abs(rows[k][i]))k=j;if(Math.abs(rows[k][i])<1e-10)throw Error('角点无法计算，请重新选择');[rows[i],rows[k]]=[rows[k],rows[i]];const d=rows[i][i];for(let c=i;c<9;c++)rows[i][c]/=d;for(let j=0;j<8;j++)if(j!==i){const f=rows[j][i];for(let c=i;c<9;c++)rows[j][c]-=f*rows[i][c];}}
 return [...rows.map(r=>r[8]),1];
}
function transform(h,[x,y]){const w=h[6]*x+h[7]*y+h[8];if(Math.abs(w)<1e-10)throw Error('无效透视映射');return[(h[0]*x+h[1]*y+h[2])/w,(h[3]*x+h[4]*y+h[5])/w];}
function calibrate(a,b,mm){const d=Math.hypot(b[0]-a[0],b[1]-a[1]);if(!finite(mm)||mm<=0||d<2)throw Error('请输入正数长度，并选择间隔至少2像素的两个点');return mm/d;}
function geometry(shape){const {type,a,b,value}=shape;if(!['line','circle','hexagon','star'].includes(type)||!a?.every(finite)||!b?.every(finite)||a.length!==2||b.length!==2||!finite(value)||value<=0)throw Error('图形参数无效');const angle=Math.atan2(b[1]-a[1],b[0]-a[0]);const role='outline';if(type==='line')return[{type:'line',start:a,end:[a[0]+value*Math.cos(angle),a[1]+value*Math.sin(angle)],role}];if(type==='circle')return[{type:'circle',center:a,radius:value/2,role}];const n=type==='hexagon'?6:10,r=value/2,inner=(3-Math.sqrt(5))/2;const pts=Array.from({length:n},(_,i)=>{const radius=r*(type==='star'&&i%2?inner:1),t=angle+i*2*Math.PI/n;return[a[0]+radius*Math.cos(t),a[1]+radius*Math.sin(t)]});return pts.map((p,i)=>({type:'line',start:p,end:pts[(i+1)%n],role}));}
function spec(shapes,scale=1){if(!shapes.length)throw Error('请先建立图形');if(!finite(scale)||scale<=0||scale>100)throw Error('纸面比例无效');const all=shapes.flatMap(geometry);const points=all.flatMap(e=>e.type==='circle'?[[e.center[0]-e.radius,e.center[1]-e.radius],[e.center[0]+e.radius,e.center[1]+e.radius]]:[e.start,e.end]);const min=[0,1].map(i=>Math.min(...points.map(p=>p[i])));return{version:1,units:'mm',reviewed:false,unresolved:[],components:shapes.map((s,i)=>({id:`构件${i+1}`,description:s.type,scale,offset:[10-min[0]*scale,10-min[1]*scale],dimensions:[{name:s.type==='line'?'长度':'外接圆直径',value:s.value,source:s.confirmed?'用户在图上确认':'标定后估计，待核对'}],entities:geometry(s)}))};}
const api={homography,transform,calibrate,geometry,spec};root.CADStudio=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
