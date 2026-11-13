"""Maintainer tool: carry the shipped voice lines that changed since earlier releases.

  python tools/make_voice_repair.py v1.0.0 v1.0.1 v1.0.2

Updates never write to audio/ or defaults/, so every OGG in defaults/audio/赛琳娜语音 that differs from the copy
a listed release shipped is put in resources/voice-repair/ together with repairs.json (the hashes of those
earlier copies). An installed pet then replaces only its unchanged copies on start (selena_pet/voice_repair.py).
Run it with every earlier release tag before building a release; lines that never changed are not carried.
"""
import hashlib, json, pathlib, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
FOLDER = '赛琳娜语音'
AUDIO = ROOT / 'defaults' / 'audio' / FOLDER
OUT = ROOT / 'resources' / 'voice-repair'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def shipped(ref, name):
    r = subprocess.run(['git', '-C', str(ROOT), 'show', f'{ref}:defaults/audio/{FOLDER}/{name}'], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def main(refs):
    if not refs:
        raise SystemExit('name the earlier release tags, for example v1.0.0 v1.0.1 v1.0.2')
    for ref in refs:
        if subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--verify', '--quiet', ref + '^{commit}'], capture_output=True).returncode:
            raise SystemExit(f'unknown release: {ref}')
    files = {}
    for path in sorted(AUDIO.glob('*.ogg')):
        data = path.read_bytes(); now = sha(data)
        old = sorted({sha(b) for b in (shipped(ref, path.name) for ref in refs) if b is not None} - {now})
        if old:
            files[path.name] = {'old': old, 'sha256': now, 'bytes': len(data)}
    if OUT.exists():
        shutil.rmtree(OUT)
    if not files:
        print('no shipped voice line changed'); return
    OUT.mkdir(parents=True)
    for name in files:
        shutil.copyfile(AUDIO / name, OUT / name)
    table = {'directory': FOLDER, 'since': refs, 'files': files}
    (OUT / 'repairs.json').write_text(json.dumps(table, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(f'{len(files)} changed voice lines, {sum(f["bytes"] for f in files.values()) / 1e6:.1f} MB')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf8')
    main(sys.argv[1:])
