/* Native AppKit UI. Runs with macOS's built-in JavaScript for Automation. */
ObjC.import('Cocoa');
var GT = { task:null, runDir:null, logHandle:null, timer:null, controller:null, window:null, app:null, views:{}, mode:null, afterMode:null, pendingQuit:false, info:{}, resource:null, bundle:null, lastStatus:'', ready:false, smoke:false };
var VERSION = '2.1.0';
function unbox(value) { try { return ObjC.unwrap(value); } catch (_) { return null; } }
function nativeText(value) { return value === undefined || value === null ? '' : String(value); }
function fm() { return $.NSFileManager.defaultManager; }
function home() { return ObjC.unwrap($.NSHomeDirectory()); }
function statePath() { return home() + '/Library/Application Support/Growtopia Launcher'; }
function exists(path) { return Boolean(fm().fileExistsAtPath(path)); }
function readText(path) { if (!exists(path)) return ''; return nativeText(unbox($.NSString.stringWithContentsOfFileEncodingError(path,$.NSUTF8StringEncoding,Ref()))).replace(/[\r\n]+$/,''); }
function writeText(path,text) { return Boolean($(text).writeToFileAtomicallyEncodingError(path,true,$.NSUTF8StringEncoding,Ref())); }
function ensureDir(path) { var error=Ref(); if (!fm().createDirectoryAtPathWithIntermediateDirectoriesAttributesError(path,true,$(),error)) throw Error('Could not create ' + path); }
function readPlist(path) { if (!exists(path)) return {}; try { return ObjC.deepUnwrap($.NSDictionary.dictionaryWithContentsOfFile(path)) || {}; } catch (_) { return {}; } }
function sourceLabel(source) { return source==='website' ? 'Official website beta' : 'In-game Ubisoft CDN'; }
function color(r,g,b) { return $.NSColor.colorWithSRGBRedGreenBlueAlpha(r/255,g/255,b/255,1); }
function rect(x,y,w,h) { return $.NSMakeRect(x,y,w,h); }
function addLabel(parent,text,x,y,w,h,size,weight,ink) {
    var view=$.NSTextField.alloc.initWithFrame(rect(x,y,w,h));
    view.stringValue=nativeText(text); view.bezeled=false; view.drawsBackground=false; view.editable=false; view.selectable=true;
    view.font=$.NSFont.systemFontOfSizeWeight(size||14,weight||0); view.textColor=ink||color(31,48,48);
    view.cell.usesSingleLineMode=false; view.cell.wraps=true; view.cell.scrollable=false;
    parent.addSubview(view); return view;
}
function panel(parent,x,y,w,h,bg) {
    // Keep colours as NSColor objects across the JXA bridge. The old direct
    // CALayer/CGColor assignment crashed in setBackgroundColor on the user's Mac.
    var box=$.NSBox.alloc.initWithFrame(rect(x,y,w,h));
    box.boxType=$.NSBoxCustom;box.titlePosition=$.NSNoTitle;box.title='';
    box.borderType=$.NSLineBorder;box.transparent=false;
    box.fillColor=bg;box.borderColor=color(221,229,223);
    box.borderWidth=1;box.cornerRadius=14;
    box.contentViewMargins=$.NSMakeSize(0,0);
    parent.addSubview(box);box.contentView.frame=rect(0,0,w,h);return box.contentView;
}
function addButton(parent,title,action,x,y,w,h,primary) {
    var b=$.NSButton.alloc.initWithFrame(rect(x,y,w,h));b.title=title;b.bezelStyle=1;b.target=GT.controller;b.action=action;b.font=$.NSFont.systemFontOfSizeWeight(13,0.2);
    if(primary){b.bezelColor=color(24,112,89);b.contentTintColor=$.NSColor.whiteColor;}
    parent.addSubview(b);return b;
}
function alert(title,text,first,second) { var a=$.NSAlert.alloc.init;a.messageText=title;a.informativeText=text;a.addButtonWithTitle(first||'OK');if(second)a.addButtonWithTitle(second);return Number(a.runModal)===1000; }
function openPath(path) { return Boolean($.NSWorkspace.sharedWorkspace.openURL($.NSURL.fileURLWithPath(path))); }
function appendUILog(message) { try {ensureDir(home()+'/Library/Logs');var p=home()+'/Library/Logs/Growtopia Launcher UI.log';if(!exists(p))fm().createFileAtPathContentsAttributes(p,$.NSData.data,$());var h=$.NSFileHandle.fileHandleForWritingAtPath(p);h.seekToEndOfFile;h.writeData($(new Date().toISOString()+' '+message+'\n').dataUsingEncoding($.NSUTF8StringEncoding));h.closeFile;} catch (_) {} }
function localInfo() {
    var target=readText(statePath()+'/target');
    if(!target) target=exists('/Applications/Growtopia.app') ? '/Applications/Growtopia.app' : home()+'/Applications/Growtopia.app';
    var p=readPlist(target+'/Contents/Info.plist');
    return {target:target,source:readText(statePath()+'/source')||'cdn',trust:readText(statePath()+'/trust')||'manual',installed:exists(target)?'true':'false',installedVersion:p.CFBundleShortVersionString||p.CFBundleVersion||'',lastCheck:readText(statePath()+'/last-check')};
}
function setStatus(title,detail) { GT.views.status.stringValue=nativeText(title); if(detail!==undefined)GT.views.detail.stringValue=nativeText(detail); }
function renderInfo(data) {
    var combined=localInfo();Object.keys(GT.info).forEach(function(k){combined[k]=GT.info[k];});Object.keys(data||{}).forEach(function(k){combined[k]=data[k];});GT.info=combined;
    var i=GT.info,hasGame=i.installed==='true';
    GT.views.installed.stringValue=hasGame?(i.installedVersion||'Version not provided'):'Not installed';
    GT.views.installPath.stringValue=i.target||'No managed installation';
    GT.views.primary.title=hasGame?'Update & Play':'Install & Play';
    GT.views.launch.enabled=hasGame&&!GT.task;
    var online='Not checked';
    if(i.downloadState==='unchanged')online='No download change detected';
    if(i.downloadState==='changed')online='Download needs inspection';
    if(i.downloadState==='downloaded')online='Downloaded build inspected';
    if(i.downloadState==='unreachable')online='Source unavailable';
    GT.views.remote.stringValue=online;
    var remoteDetail=sourceLabel(i.source);
    if(i.downloadedVersion&&i.downloadState==='downloaded')remoteDetail+=' · Bundle '+i.downloadedVersion;
    else if(i.remoteSizeBytes)remoteDetail+=' · '+Math.round(Number(i.remoteSizeBytes)/1048576)+' MB';
    GT.views.remoteDetail.stringValue=remoteDetail;
    GT.views.remoteDate.stringValue=i.remoteLastModified?'Download modified: '+i.remoteLastModified:'Online game version appears only after downloading the bundle.';
    GT.views.source.selectItemAtIndex(i.source==='website'?1:0);
    GT.views.trust.state=i.trust==='official'?1:0;
    GT.views.checked.stringValue=i.lastCheck?'Last check: '+i.lastCheck:'Check for Updates inspects the source without downloading the game.';
    GT.views.target.stringValue='Game folder: '+(i.target||'Not selected');
    var installedLauncher=home()+'/Applications/Growtopia Launcher.app';
    GT.views.selfInstall.title=GT.bundle===installedLauncher?'Launcher installed':(GT.selfCopied?'Show Installed App':'Install Launcher');
    GT.views.selfInstall.enabled=!GT.task&&GT.bundle!==installedLauncher;
}
function setBusy(busy) {
    ['primary','check','launch','source','trust','personal','restore','fresh','selfInstall','cleanup'].forEach(function(k){if(GT.views[k])GT.views[k].enabled=!busy;});
    GT.views.cancel.enabled=busy;
    if(!busy){GT.views.launch.enabled=GT.info.installed==='true';GT.views.selfInstall.enabled=GT.bundle!==home()+'/Applications/Growtopia Launcher.app';}
}
function startMode(mode,afterMode) {
    if(GT.task)return;
    if(['play','update','fresh','restore'].indexOf(mode)!==-1&&!readText(statePath()+'/trust')){startMode('trust-manual',mode);return;}
    startTask(mode,GT.resource+'/core.sh',[mode],afterMode||null);
}
function startTask(mode,script,leadingArgs,afterMode) {
    if(GT.task)return;
    try {
        var base=ObjC.unwrap($.NSTemporaryDirectory());
        var dir=base+'/growtopia-native-'+ObjC.unwrap($.NSUUID.UUID.UUIDString);
        ensureDir(dir);ensureDir(home()+'/Library/Logs');
        var logPath=home()+'/Library/Logs/Growtopia Launcher.log';
        if(!exists(logPath))fm().createFileAtPathContentsAttributes(logPath,$.NSData.data,$());
        var h=$.NSFileHandle.fileHandleForWritingAtPath(logPath);h.seekToEndOfFile;
        var task=$.NSTask.alloc.init;
        task.launchPath='/bin/bash';task.arguments=$([script].concat(leadingArgs).concat([dir]));task.standardOutput=h;task.standardError=h;
        GT.task=task;GT.runDir=dir;GT.logHandle=h;GT.mode=mode;GT.afterMode=afterMode;GT.lastStatus='';
        setBusy(true);GT.views.progress.indeterminate=true;GT.views.progress.startAnimation($());
        setStatus(mode==='install-launcher'?'Installing the launcher…':'Working…','Keep this window open until the operation finishes.');
        task.launch;
    } catch(e) {
        appendUILog(String(e));GT.task=null;GT.afterMode=null;if(GT.logHandle){try{GT.logHandle.closeFile;}catch(_){}GT.logHandle=null;}
        setBusy(false);GT.views.progress.stopAnimation($());setStatus('Could not start the operation',String(e));alert('Could not start',String(e));
    }
}
function requestCancel() { if(!GT.task)return;writeText(GT.runDir+'/cancel','1\n');GT.afterMode=null;GT.views.cancel.enabled=false;setStatus('Cancelling safely…','The current safe step may finish before cancellation. See the log for completed actions.'); }
function pollWorker() {
    if(!GT.task)return;
    try {
        var dir=GT.runDir, s=readText(dir+'/status');
        if(s&&s!==GT.lastStatus){GT.lastStatus=s;GT.views.status.stringValue=s;}
        var info=readPlist(dir+'/info.plist');if(Object.keys(info).length)renderInfo(info);
        var raw=readText(dir+'/progress');
        if(raw!==''&&isFinite(Number(raw))){GT.views.progress.indeterminate=false;GT.views.progress.doubleValue=Math.max(0,Math.min(100,Number(raw)));}else if(!Boolean(GT.views.progress.indeterminate)){GT.views.progress.indeterminate=true;GT.views.progress.startAnimation($());}
        var result=readText(dir+'/result');
        if(!result&&Boolean(GT.task.running))return;
        if(!result){result='error';writeText(dir+'/error.txt','The updater stopped unexpectedly. Open the log for details.');}
        var errorText=readText(dir+'/error.txt'),finishedMode=GT.mode,next=GT.afterMode,cancelled=exists(dir+'/cancel');
        var lastInfo=readPlist(dir+'/info.plist');
        GT.task=null;GT.afterMode=null;GT.mode=null;
        if(GT.logHandle){GT.logHandle.closeFile;GT.logHandle=null;}
        GT.views.progress.stopAnimation($());GT.views.progress.indeterminate=false;GT.views.progress.doubleValue=result==='ok'&&!cancelled?100:0;
        setBusy(false);renderInfo(lastInfo);
        fm().removeItemAtPathError(dir,Ref());GT.runDir=null;
        if(result==='error'){
            setStatus('Operation stopped',errorText||'Open the log for details.');
            if(!GT.pendingQuit&&alert('Growtopia Launcher',errorText||'The updater stopped. Open the log for details.','Open Log','Close'))openLog();
        }else if(cancelled){setStatus('Stopped after the current safe step','See the log for any completed actions.');}
        else if(finishedMode==='install-launcher'){GT.selfCopied=true;renderInfo(lastInfo);setStatus('Launcher installed','Saved in your personal Applications folder. Use that copy for your Dock icon.');if(alert('Launcher installed','The application is in ~/Applications. Close this copy when finished, then open the installed one and add it to your Dock.','Show Applications','OK'))openPath(home()+'/Applications');}
        else if(!next){
            var messages={inspect:'Check complete',play:'Growtopia opened',update:'Game installation complete',fresh:'Fresh installation complete',launch:'Growtopia opened',restore:'Previous version restored','trust-official':'Growtopia-only trust enabled','trust-manual':'Normal macOS checks enabled','source-cdn':'Download source saved','source-website':'Download source saved','personal-target':'Personal game folder selected','cleanup-installers':'Installer cleanup complete'};
            setStatus(messages[finishedMode]||'Done',GT.lastStatus||'Operation complete.');
        }
        if(GT.pendingQuit){GT.app.terminate($());return;}
        if(result==='ok'&&!cancelled&&next)startMode(next);
    } catch(e) {appendUILog('Polling: '+String(e));GT.views.detail.stringValue='UI error: '+String(e)+' — see UI log.';}
}
function copyDiagnostics() {
    try {
        var task=$.NSTask.alloc.init,pipe=$.NSPipe.pipe;
        task.launchPath='/bin/bash';task.arguments=$([GT.resource+'/diagnostics.sh',GT.bundle]);task.standardOutput=pipe;task.standardError=pipe;
        task.launch;
        var data=pipe.fileHandleForReading.readDataToEndOfFile;task.waitUntilExit;
        var report=ObjC.unwrap($.NSString.alloc.initWithDataEncoding(data,$.NSUTF8StringEncoding));
        if(Number(task.terminationStatus)!==0){alert('Diagnostics failed',report||'Open the UI log for details.');return;}
        var clipboard=$.NSPasteboard.generalPasteboard;clipboard.clearContents;clipboard.setStringForType(report,$.NSPasteboardTypeString);
        alert('Diagnostics copied','Paste the report into a GitHub issue. It omits usernames, serial numbers, home paths, login data and raw logs.');
    }catch(e){appendUILog('Diagnostics: '+String(e));alert('Diagnostics failed',String(e));}
}
function removeInstallers() {
    if(GT.task)return;
    var picker=$.NSOpenPanel.openPanel;
    picker.title='Remove Growtopia Installers';picker.message='Select Growtopia DMG files to move to Trash.';
    picker.prompt='Select';picker.canChooseFiles=true;picker.canChooseDirectories=false;picker.allowsMultipleSelection=true;picker.allowedFileTypes=$(['dmg']);
    picker.directoryURL=$.NSURL.fileURLWithPath(home()+'/Downloads');
    if(Number(picker.runModal)!==1)return;
    var selected=[],names=[],urls=picker.URLs;
    for(var n=0;n<Number(urls.count);n++) {
        var path=ObjC.unwrap(urls.objectAtIndex(n).path),name=path.split('/').pop();
        if(!/^growtopia.*\.dmg$/i.test(name)){alert('File not selected for removal','This action only accepts files named Growtopia*.dmg.');return;}
        selected.push(path);names.push(name);
    }
    if(!selected.length)return;
    if(!alert('Move installers to Trash?',names.join('\n')+'\n\nOnly these selected files will be moved. Game settings and login data are not changed.','Move to Trash','Cancel'))return;
    startTask('cleanup-installers',GT.resource+'/cleanup-installers.sh',selected,null);
}
function openLog(){var p=home()+'/Library/Logs/Growtopia Launcher.log';if(!exists(p)){alert('No log yet','Run Check for Updates or Install & Play first.');return;}openPath(p);}
function quitRequested(){if(!GT.task)return true;if(alert('An operation is running','Cancel it safely and close the launcher once the current safe step finishes?','Cancel and Quit','Keep Open')){GT.pendingQuit=true;requestCancel();}return false;}
function configureCallbacks(){
    ObjC.registerSubclass({name:'GTNativeController',superclass:'NSObject',protocols:['NSApplicationDelegate','NSWindowDelegate'],methods:{
        'tick:':{types:['void',['id']],implementation:function(){if(GT.smoke){appendUILog('UI smoke test passed');GT.timer.invalidate;GT.window.orderOut($());GT.app.stop($());return;}pollWorker();}},
        'check:':{types:['void',['id']],implementation:function(){startMode('inspect');}},
        'play:':{types:['void',['id']],implementation:function(){startMode('play');}},
        'launch:':{types:['void',['id']],implementation:function(){startMode('launch');}},
        'cancel:':{types:['void',['id']],implementation:function(){requestCancel();}},
        'sourceChanged:':{types:['void',['id']],implementation:function(sender){startMode(Number(sender.indexOfSelectedItem)===1?'source-website':'source-cdn');}},
        'trustChanged:':{types:['void',['id']],implementation:function(sender){if(Number(sender.state)===1){if(!alert('Trust official Growtopia downloads?','This authorizes removing quarantine from Growtopia.app only, including future downloads from the selected official HTTPS source. It can skip Apple\'s first-open/notarization check. An unsigned build is not publisher-verified. Other apps and global Gatekeeper settings are unchanged.','Trust Official Downloads','Cancel')){sender.state=0;return;}startMode('trust-official');}else startMode('trust-manual');}},
        'personal:':{types:['void',['id']],implementation:function(){startMode('personal-target');}},
        'fresh:':{types:['void',['id']],implementation:function(){startMode('fresh');}},
        'restore:':{types:['void',['id']],implementation:function(){startMode('restore');}},
        'diagnostics:':{types:['void',['id']],implementation:function(){copyDiagnostics();}},
        'cleanup:':{types:['void',['id']],implementation:function(){removeInstallers();}},
        'logs:':{types:['void',['id']],implementation:function(){openLog();}},
        'folder:':{types:['void',['id']],implementation:function(){openPath(ObjC.unwrap($(GT.info.target||home()+'/Applications/Growtopia.app').stringByDeletingLastPathComponent));}},
        'help:':{types:['void',['id']],implementation:function(){openPath(GT.resource+'/README.html');}},
        'installLauncher:':{types:['void',['id']],implementation:function(){if(GT.selfCopied){openPath(home()+'/Applications');return;}startTask('install-launcher',GT.resource+'/install-ui.sh',[GT.bundle],null);}},
        'quit:':{types:['void',['id']],implementation:function(){GT.app.terminate($());}},
        'applicationShouldTerminateAfterLastWindowClosed:':{types:['bool',['id']],implementation:function(){return true;}},
        'applicationShouldTerminate:':{types:['unsigned long',['id']],implementation:function(){return quitRequested()?1:0;}},
        'windowShouldClose:':{types:['bool',['id']],implementation:function(){return quitRequested();}}
    }});
    GT.controller=$.GTNativeController.alloc.init;
}
function buildWindow(){
    appendUILog('Startup: creating AppKit application; mainThread='+Boolean($.NSThread.isMainThread));
    GT.app=$.NSApplication.sharedApplication;GT.app.setActivationPolicy($.NSApplicationActivationPolicyRegular);$.NSProcessInfo.processInfo.processName='Growtopia Launcher';
    appendUILog('Startup: registering interface callbacks');
    configureCallbacks();GT.app.delegate=GT.controller;
    var menu=$.NSMenu.alloc.init,appItem=$.NSMenuItem.alloc.init,appMenu=$.NSMenu.alloc.init;
    menu.addItem(appItem);appItem.submenu=appMenu;
    var diagnostics=$.NSMenuItem.alloc.initWithTitleActionKeyEquivalent('Copy Diagnostics','diagnostics:','');diagnostics.target=GT.controller;appMenu.addItem(diagnostics);appMenu.addItem($.NSMenuItem.separatorItem);
    var quit=$.NSMenuItem.alloc.initWithTitleActionKeyEquivalent('Quit Growtopia Launcher','quit:','q');quit.target=GT.controller;appMenu.addItem(quit);GT.app.mainMenu=menu;
    appendUILog('Startup: constructing main window');
    var w=$.NSWindow.alloc.initWithContentRectStyleMaskBackingDefer(rect(0,0,860,760),$.NSWindowStyleMaskTitled|$.NSWindowStyleMaskClosable|$.NSWindowStyleMaskMiniaturizable,2,false);
    GT.window=w;w.title='Growtopia Launcher';w.releasedWhenClosed=false;w.delegate=GT.controller;w.backgroundColor=color(245,247,242);w.appearance=$.NSAppearance.appearanceNamed($.NSAppearanceNameAqua);
    var root=w.contentView,muted=color(100,114,104),green=color(25,106,78);
    var icon=$.NSImage.alloc.initWithContentsOfFile(GT.resource+'/AppIcon.icns');if(icon)GT.app.applicationIconImage=icon;
    addLabel(root,'macOS',34,713,550,20,11,0.6,green);
    addLabel(root,'Growtopia Launcher',34,671,650,38,29,0.5);
    GT.views.selfInstall=addButton(root,'Install Launcher','installLauncher:',664,711,164,30,false);
    addLabel(root,'Install, update and launch Growtopia.',34,646,760,22,14,0,muted);
    appendUILog('Startup: constructing NSBox cards');
    var installed=panel(root,34,506,386,120,$.NSColor.whiteColor);
    addLabel(installed,'INSTALLED GAME',18,88,345,18,10,0.6,muted);
    GT.views.installed=addLabel(installed,'Reading installation…',18,48,347,35,27,0.5);
    GT.views.installPath=addLabel(installed,'',18,10,350,32,10,0,muted);
    var remote=panel(root,438,506,390,120,$.NSColor.whiteColor);
    addLabel(remote,'OFFICIAL DOWNLOAD',18,88,350,18,10,0.6,muted);
    GT.views.remote=addLabel(remote,'Not checked',18,58,350,26,17,0.5);
    GT.views.remoteDetail=addLabel(remote,'',18,35,350,22,12,0,green);
    GT.views.remoteDate=addLabel(remote,'',18,6,350,30,10,0,muted);
    var progressPanel=panel(root,34,354,794,133,color(233,242,233));
    GT.views.status=addLabel(progressPanel,'Idle',18,87,756,28,17,0.5);
    GT.views.detail=addLabel(progressPanel,'Select an action.',18,48,756,35,12,0,muted);
    GT.views.progress=$.NSProgressIndicator.alloc.initWithFrame(rect(19,18,755,15));GT.views.progress.minValue=0;GT.views.progress.maxValue=100;GT.views.progress.indeterminate=false;progressPanel.addSubview(GT.views.progress);
    GT.views.primary=addButton(root,'Install & Play','play:',34,297,215,39,true);
    GT.views.check=addButton(root,'Check for Updates','check:',260,297,192,39,false);
    GT.views.launch=addButton(root,'Launch Installed','launch:',464,297,190,39,false);
    GT.views.cancel=addButton(root,'Cancel','cancel:',665,297,163,39,false);GT.views.cancel.enabled=false;
    var settings=panel(root,34,106,794,173,$.NSColor.whiteColor);
    addLabel(settings,'PREFERENCES',18,141,300,18,10,0.6,muted);
    addLabel(settings,'Download source',18,105,150,23,13,0.2);
    GT.views.source=$.NSPopUpButton.alloc.initWithFramePullsDown(rect(185,104,335,28),false);GT.views.source.addItemsWithTitles($(['In-game Ubisoft CDN','Official website beta']));GT.views.source.target=GT.controller;GT.views.source.action='sourceChanged:';settings.addSubview(GT.views.source);
    GT.views.trust=$.NSButton.alloc.initWithFrame(rect(18,66,750,26));GT.views.trust.setButtonType(3);GT.views.trust.title='Trust official downloads for Growtopia only';GT.views.trust.target=GT.controller;GT.views.trust.action='trustChanged:';GT.views.trust.font=$.NSFont.systemFontOfSize(13);settings.addSubview(GT.views.trust);
    addLabel(settings,'Unchecked keeps normal macOS first-open checks. Changing source requests a fresh download.',37,44,720,21,10,0,muted);
    GT.views.target=addLabel(settings,'',18,12,555,25,10,0,muted);
    GT.views.personal=addButton(settings,'Use Personal Folder','personal:',587,9,188,30,false);
    GT.views.restore=addButton(root,'Restore Previous','restore:',34,61,145,29,false);
    GT.views.fresh=addButton(root,'Download Again','fresh:',189,61,145,29,false);
    GT.views.cleanup=addButton(root,'Remove Installers','cleanup:',344,61,155,29,false);
    GT.views.logs=addButton(root,'Open Log','logs:',509,61,83,29,false);
    GT.views.folder=addButton(root,'Game Folder','folder:',602,61,116,29,false);
    GT.views.help=addButton(root,'Guide','help:',728,61,100,29,false);
    GT.views.checked=addLabel(root,'',34,25,700,24,10,0,muted);
    addLabel(root,'v'+VERSION,760,25,68,24,10,0,muted);
    appendUILog('Startup: rendering installation information');
    renderInfo({});w.center;w.makeKeyAndOrderFront($());GT.app.activateIgnoringOtherApps(true);
    GT.timer=$.NSTimer.timerWithTimeIntervalTargetSelectorUserInfoRepeats(0.35,GT.controller,'tick:',$(),true);
    $.NSRunLoop.mainRunLoop.addTimerForMode(GT.timer,$.NSRunLoopCommonModes);
    GT.ready=true;appendUILog('Startup: window ready; starting event loop');GT.app.run;
}
function run(argv){
    try {
        if(!argv||!argv[0])throw Error('The app did not provide its Resources folder. Open the complete Growtopia Launcher.app bundle.');
        appendUILog('Startup: Growtopia Launcher '+VERSION);
        GT.smoke=argv.length>1&&String(argv[1])==='--smoke-test';
        GT.resource=String(argv[0]);GT.bundle=ObjC.unwrap($(GT.resource).stringByDeletingLastPathComponent.stringByDeletingLastPathComponent);
        if(!exists(GT.resource+'/core.sh'))throw Error('The app bundle is incomplete: core.sh is missing.');
        buildWindow();
        if(GT.smoke)return 'GROWTOPIA_UI_SMOKE_OK';
    } catch(e) {
        appendUILog('Startup: '+String(e));
        try{var a=Application.currentApplication();a.includeStandardAdditions=true;a.displayAlert('Growtopia Launcher could not open',{message:String(e)+'\nSee ~/Library/Logs/Growtopia Launcher UI.log'});}catch(_){}
        throw e;
    }
}
