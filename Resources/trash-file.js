ObjC.import('Foundation');
function run(argv) {
    if (!argv || argv.length !== 1) throw Error('Expected one selected installer.');
    var path=String(argv[0]);
    if (!/^\//.test(path) || !/^growtopia.*\.dmg$/i.test(path.split('/').pop())) throw Error('Not a Growtopia DMG path.');
    var manager=$.NSFileManager.defaultManager;
    var attributes=manager.attributesOfItemAtPathError(path,Ref());
    if (!attributes || ObjC.unwrap(attributes.objectForKey($.NSFileType)) !== ObjC.unwrap($.NSFileTypeRegular)) throw Error('Installer is not a regular file.');
    var error=Ref();
    if (!manager.trashItemAtURLResultingItemURLError($.NSURL.fileURLWithPath(path),$(),error)) {
        var detail='macOS refused to move the selected file.';
        try { if(error[0])detail=ObjC.unwrap(error[0].localizedDescription); } catch(_) {}
        throw Error(detail);
    }
    return 'Installer moved to Trash.';
}
