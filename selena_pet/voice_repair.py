"""Bring shipped voice lines up to date in an installed pet.

Updates never write to audio/ or defaults/ (they hold the user's own material), so a release that fixes a
shipped line also carries the fixed file in resources/voice-repair/ (a program folder) with repairs.json:
{"directory": "赛琳娜语音", "files": {"<name>.ogg": {"old": [sha256 of earlier shipped copies], "sha256": ..., "bytes": ...}}}
On start every listed line that is still byte for byte a copy an earlier release shipped is replaced.
A line the user changed, replaced or removed is left alone.
"""
import hashlib,json,os,pathlib,shutil

LIMIT=20_000_000

def digest(path):
    with open(path,'rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def plain_name(name):
    return isinstance(name,str) and name and name==pathlib.Path(name).name and name not in ('.','..') and ':' not in name

def repair(root,audio_directory):
    """Returns the names of the lines that were replaced (each folder counted once per line)."""
    root=pathlib.Path(root); source=root/'resources'/'voice-repair'
    try: table=json.loads((source/'repairs.json').read_text('utf8'))
    except (OSError,ValueError): return []
    folder=table.get('directory') if isinstance(table,dict) else None
    files=table.get('files') if isinstance(table,dict) else None
    if not plain_name(folder) or not isinstance(files,dict): return []
    folders=[];seen=set()
    for base in (pathlib.Path(audio_directory),root/'defaults'/'audio'):
        candidate=base/folder
        try: key=os.path.normcase(str(candidate.resolve()))
        except OSError: continue
        if key not in seen and candidate.is_dir(): seen.add(key);folders.append(candidate)
    replaced=[]
    for name,entry in files.items():
        if not plain_name(name) or not isinstance(entry,dict): continue
        old=set(entry.get('old') or ());fixed=source/name
        try:
            if not fixed.is_file() or digest(fixed)!=entry.get('sha256'): continue
        except OSError: continue
        for directory in folders:
            target=directory/name;temporary=target.with_name(target.name+'.repair-tmp')
            try:
                if not target.is_file() or target.stat().st_size>LIMIT or digest(target) not in old: continue
                shutil.copyfile(fixed,temporary);os.replace(temporary,target);replaced.append(name)
            except OSError:
                try: temporary.unlink(missing_ok=True)
                except OSError: pass
    return replaced
