"""Maintainer tool: package a built tree into the public release files.

  python tools/build_portable.py
  python tools/make_release.py OUT_DIR
  python tools/sign_update.py --key <offline key> OUT_DIR/<prefix>AutoUpdate-v<V>.json
  python tools/make_release.py OUT_DIR --sums        # after signing: write SHA256SUMS

Produces <prefix>Windows-v<V>.zip (full package), <prefix>Program-Update-v<V>.zip and
<prefix>AutoUpdate-v<V>.json (one-click update), <prefix>Settings-Patch-v<V>.zip (manual program patch).
"""
import argparse, hashlib, json, pathlib, sys, zipfile
root = pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0, str(root))
sys.stdout.reconfigure(encoding='utf8')
from selena_pet.config_io import export_bundle
from selena_pet.paths import VERSION
from selena_pet.update_package import prefix
from tools.package_update import package


def digest(p):
    with open(p, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def build(out):
    out.mkdir(parents=True, exist_ok=True)
    p = prefix()
    full = out / f'{p}Windows-v{VERSION}.zip'
    settings = json.loads((root / 'defaults/settings.json').read_text('utf8'))
    warnings = export_bundle(full, settings, root, True)
    assert not warnings, warnings
    result = package(full, out)
    program = out / f'{p}Program-Update-v{VERSION}.zip'
    patch = out / f'{p}Settings-Patch-v{VERSION}.zip'
    with zipfile.ZipFile(program) as source, zipfile.ZipFile(patch, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as target:
        for name in source.namelist():
            target.writestr(name, source.read(name))
        target.writestr('current-program.json', json.dumps({'version': VERSION}))
        target.writestr('程序补丁说明.txt', '请先退出桌宠并备份原目录，再解压覆盖。只更新程序，保留个人配置和素材。'
                                          '安装后可在 设置 → 版本与更新 中一键更新。')
    print(json.dumps({k: v for k, v in result.items() if k != 'program'}, ensure_ascii=False))


def sums(out):
    p = prefix()
    names = [f'{p}Windows-v{VERSION}.zip', f'{p}Program-Update-v{VERSION}.zip', f'{p}AutoUpdate-v{VERSION}.json',
             f'{p}AutoUpdate-v{VERSION}.json.sig', f'{p}Settings-Patch-v{VERSION}.zip']
    missing = [n for n in names if not (out / n).is_file()]
    if missing:
        raise SystemExit('missing: ' + ', '.join(missing))
    target = out / f'{p}SHA256SUMS-v{VERSION}.txt'
    target.write_text(''.join(f'{digest(out / n)}  {n}\n' for n in names), encoding='utf8', newline='\n')
    print(target)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('--sums', action='store_true')
    a = ap.parse_args(); out = pathlib.Path(a.out).resolve()
    sums(out) if a.sums else build(out)
