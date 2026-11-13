/* Local image ingestion, with bounded memory and no network. */
(function(root){
'use strict';
const limits={count:20,totalBytes:12*1024*1024,fileBytes:10*1024*1024};
function mime(bytes){
 if(bytes[0]===137&&bytes[1]===80&&bytes[2]===78&&bytes[3]===71)return 'image/png';
 if(bytes[0]===255&&bytes[1]===216&&bytes[2]===255)return 'image/jpeg';
 if(String.fromCharCode(...bytes.slice(0,4))==='RIFF'&&String.fromCharCode(...bytes.slice(8,12))==='WEBP')return 'image/webp';
 throw Error('不是有效的PNG、JPEG或WebP图片');
}
function validateBatch(items){
 if(items.length>limits.count)throw Error(`一次最多${limits.count}张图片，请分组处理`);
 if(items.some(x=>x.size>limits.fileBytes))throw Error('单张图片不能超过10MiB');
 if(items.reduce((n,x)=>n+x.size,0)>limits.totalBytes)throw Error('图片合计不能超过12MiB，请减少图片或缩小文件后重试（不会自动压缩图纸）');
}
async function prepare(files,existing=[]){
 const all=Array.from(files);const candidates=all.filter(f=>/\.(png|jpe?g|webp)$/i.test(f.name)).sort((a,b)=>(a.webkitRelativePath||a.name).localeCompare(b.webkitRelativePath||b.name,'zh',{numeric:true}));
 if(candidates.length>200)throw Error('文件夹包含超过200张图片，请先选择一个较小的子文件夹');
 const output=[],hashes=new Set(existing.map(x=>x.hash));let duplicates=0;
 for(const file of candidates){
  if(file.size>limits.fileBytes)throw Error(file.name+' 超过单张10MiB限制；本次选择未添加');
  const bytes=new Uint8Array(await file.arrayBuffer());let type;
  try{type=mime(bytes)}catch{throw Error(file.name+' 的图片内容无效；本次选择未添加')}
  const hash=Array.from(new Uint8Array(await root.crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');
  if(hashes.has(hash)){duplicates++;continue;}
  hashes.add(hash);validateBatch([...existing,...output,{size:file.size}]);
  let binary='';for(let i=0;i<bytes.length;i+=32768)binary+=String.fromCharCode(...bytes.subarray(i,i+32768));
  output.push({name:file.name,size:file.size,hash,data:`data:${type};base64,${root.btoa(binary)}`});
 }
 return{items:output,skipped:all.length-candidates.length,duplicates};
}
const api={limits,mime,validateBatch,prepare};root.CADImages=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
