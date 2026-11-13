const test=require('node:test'),assert=require('node:assert/strict');const imgs=require('../../frontend/images.js');
function file(name,tail,path=''){const f=new File([new Uint8Array([137,80,78,71,13,10,26,10,tail])],name,{type:'image/png'});Object.defineProperty(f,'webkitRelativePath',{value:path});return f}
test('folder filters non-images, naturally sorts and deduplicates content',async()=>{
 const result=await imgs.prepare([file('page10.png',10,'set/page10.png'),new File(['text'],'notes.txt'),file('page2.png',2,'set/page2.png'),file('copy.png',2,'set/zcopy.png')]);
 assert.equal(result.skipped,1);assert.equal(result.duplicates,1);assert.deepEqual(result.items.map(x=>x.name),['page2.png','page10.png']);assert.ok(result.items.every(x=>x.data.startsWith('data:image/png;base64,')));
 const second=await imgs.prepare([file('again.png',2)],result.items);assert.equal(second.items.length,0);assert.equal(second.duplicates,1);
});
test('invalid file fails atomically without mutating existing batch',async()=>{
 const existing=(await imgs.prepare([file('a.png',1)])).items;const before=JSON.stringify(existing);
 await assert.rejects(imgs.prepare([new File(['not a png'],'bad.png')],existing),/无效/);assert.equal(JSON.stringify(existing),before);
});
test('batch memory and count are bounded',()=>{
 assert.throws(()=>imgs.validateBatch(Array(21).fill({size:1})),/20/);
 assert.throws(()=>imgs.validateBatch([{size:8*1024*1024},{size:5*1024*1024}]),/12MiB/);
 assert.throws(()=>imgs.validateBatch([{size:11*1024*1024}]),/10MiB/);
});
