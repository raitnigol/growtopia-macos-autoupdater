const fs=require('fs');
const vm=require('vm');
const assert=require('assert/strict');
const path=require('path');
function model(){
 const context={ObjC:{import(){},unwrap:x=>x,deepUnwrap:x=>x},console,Date,Math,Number,String,Boolean,Object,isFinite};
 vm.createContext(context);
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../Resources/ui.js'),'utf8'),context);
 context.home=()=>'/Users/test';
 context.localInfo=()=>({target:'/Users/test/Applications/Growtopia.app',source:'cdn',trust:'manual',installed:'true',installedVersion:'5.58',lastCheck:''});
 context.GT.bundle='/Users/test/Applications/Growtopia Launcher.app';
 for(const k of ['installed','installPath','primary','launch','remote','remoteDetail','remoteDate','trust','checked','target','selfInstall','status','detail','cancel'])context.GT.views[k]={};
 context.GT.views.source={selectItemAtIndex(i){this.selected=i;}};
 return context;
}
{
 const c=model();c.renderInfo({downloadState:'changed',remoteLastModified:'Sun, 01 Nov 2026 06:06:26 GMT',remoteSizeBytes:'340070658'});
 assert.equal(c.GT.views.installed.stringValue,'5.58');
 assert.equal(c.GT.views.remote.stringValue,'Download needs inspection');
 assert.match(c.GT.views.remoteDate.stringValue,/^Download modified:/);
 assert.doesNotMatch(c.GT.views.remote.stringValue,/5\.61|latest|update available/i);
}
{
 const c=model();c.renderInfo({installed:'false',installedVersion:''});
 assert.equal(c.GT.views.installed.stringValue,'Not installed');
 assert.equal(c.GT.views.primary.title,'Install & Play');
 assert.equal(c.GT.views.launch.enabled,false);
}
{
 const c=model();const calls=[];c.readText=()=>'';c.startTask=(...args)=>calls.push(args);
 c.startMode('inspect');assert.equal(calls[0][0],'inspect');
 calls.length=0;c.startMode('play');assert.equal(calls[0][0],'trust-manual');assert.equal(calls[0][3],'play');
}
{
 const c=model();const writes=[];c.GT.task={};c.GT.runDir='/private/run';c.GT.afterMode='play';c.writeText=(p,t)=>writes.push([p,t]);
 c.requestCancel();assert.equal(writes[0][0],'/private/run/cancel');assert.equal(c.GT.afterMode,null);
 assert.equal(c.GT.views.cancel.enabled,false);assert.match(c.GT.views.status.stringValue,/Cancelling/);
 assert.doesNotMatch(c.GT.views.detail.stringValue,/was kept|is preserved/);
}
{
 const source=fs.readFileSync(path.join(__dirname,'../Resources/ui.js'),'utf8');
 assert.doesNotMatch(source,/\.CGColor\b|\.layer\.(backgroundColor|borderColor)\b/);
}
{
 const c=model();let created,added;
 const background={name:'NSColor background'};
 Object.defineProperty(background,'CGColor',{get(){throw Error('CGColor must not cross the scripting bridge');}});
 const border={name:'NSColor border'};
 c.$={NSBoxCustom:4,NSNoTitle:0,NSLineBorder:1,NSMakeSize:(w,h)=>({w,h}),NSBox:{alloc:{initWithFrame(frame){created={frame,contentView:{}};return created;}}}};
 c.rect=(x,y,w,h)=>({x,y,w,h});c.color=()=>border;
 const content=c.panel({addSubview(box){added=box;}},10,20,386,120,background);
 assert.equal(added,created);assert.equal(content,created.contentView);
 assert.equal(created.fillColor,background);assert.equal(created.borderColor,border);
 assert.equal(created.boxType,4);assert.equal(created.borderType,1);assert.equal(created.titlePosition,0);
 assert.deepEqual(content.frame,{x:0,y:0,w:386,h:120});
 assert.equal(created.wantsLayer,undefined);assert.equal(created.layer,undefined);
}
console.log('6 UI behavior checks passed');
