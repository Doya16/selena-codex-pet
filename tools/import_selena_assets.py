"""Maintainer tool: import the Selena sticker GIFs and the chosen voice lines into the pet.

Usage:
  python tools/import_selena_assets.py --gifs <workbench>/library --export <workbench>/export/selena-<stamp>

- Every GIF from both skins is resized to 300x300 (transparency and frame timing kept) into assets/originals.
- assets/catalog.json lists them with pack and skin.
- The chosen voice lines become OGG files with a subtitle .txt in defaults/audio/赛琳娜语音.
- defaults/settings.json gets the voice pools; GIFs come from the selected skin set (see PACKS in pet.py),
  which this tool prints as Python so both skins stay in sync.
Needs ffmpeg on PATH and Pillow.
"""
import argparse, hashlib, json, pathlib, re, shutil, subprocess, sys
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
FFMPEG = shutil.which('ffmpeg') or 'ffmpeg'
# pack folder -> (catalog id prefix, display pack name, skin)
PACKS = [
    ('B版花嫁', 'hb', 'B版花嫁', '花嫁'), ('花嫁DLC1', 'hd1', '花嫁DLC1', '花嫁'), ('花嫁DLC2', 'hd2', '花嫁DLC2', '花嫁'),
    ('A版花嫁', 'ha', 'A版花嫁', '花嫁'), ('B版原皮', 'yb', 'B版原皮', '原皮'), ('原皮社区包', 'ys', '原皮社区包', '原皮'),
    ('原皮圣诞', 'yc', '原皮圣诞', '原皮'), ('新年表情包', 'yn', '新年表情包', '原皮'),
]
SKIN_ORDER = {'花嫁': ['B版花嫁', '花嫁DLC1', '花嫁DLC2', 'A版花嫁'], '原皮': ['B版原皮', '原皮社区包', '原皮圣诞', '新年表情包']}
# 原皮 has no counterpart for these DLC-only actions; use the closest original-skin expression
SUBS = {'原皮': {'pet': '害羞', 'drag': '我擦', 'drop': '敬礼', 'idle': '不赖', 'reading': '我？', 'writing': '启动',
                 'working': '-648', 'waiting': '抱抱', 'error': '轮椅'}}
STATES = ['pet', 'doubleclick', 'hover', 'drag', 'drop', 'feed', 'idle', 'thinking', 'reading', 'writing', 'working',
          'waiting', 'done', 'error', 'paused', 'unknown']
AUDIO_DIR = '赛琳娜语音'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def gif_info(p):
    with Image.open(p) as im:
        n = getattr(im, 'n_frames', 1); durs = []
        for i in range(n):
            im.seek(i); durs.append(int(im.info.get('duration', 100) or 100))
        return im.size, n, durs


def resize_gif(src, dst):
    vf = ('[0:v]scale=300:300:flags=lanczos,split[a][b];[a]palettegen=reserve_transparent=1:stats_mode=diff[p];'
          '[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle:alpha_threshold=128')
    subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(src), '-filter_complex', vf, '-loop', '0', str(dst)], check=True)


def import_gifs(library):
    rows = json.loads((library / 'gifs.json').read_text(encoding='utf-8'))
    out = ROOT / 'assets' / 'originals'
    for old in out.glob('*.gif'):
        old.unlink()
    catalog, by_pack_name = [], {}
    for folder, code, label, skin in PACKS:
        items = [r for r in rows if r['pack'] == folder]
        for n, r in enumerate(items, 1):
            gid = f'{code}-{n:02}'
            dst = out / f'{gid}.gif'
            resize_gif(library.parent / r['file'], dst)
            (w, h), frames, durs = gif_info(dst)
            src_durs = gif_info(library.parent / r['file'])[2]
            # GIF delays are stored in 10 ms steps, so allow rounding but not lost or merged frames
            if abs(sum(durs) - sum(src_durs)) > max(30, sum(src_durs) * 0.03):
                raise SystemExit(f'timing changed for {r["file"]}: {sum(src_durs)} -> {sum(durs)} ms, {len(src_durs)} -> {frames} frames')
            catalog.append({'id': gid, 'name': r['name'] + '.gif', 'pack': label, 'skin': skin,
                            'archive': '赛琳娜表情包', 'member': f'{folder}/{r["name"]}.gif', 'path': f'assets/originals/{gid}.gif',
                            'sha256': sha(dst), 'width': w, 'height': h, 'frames': frames, 'duration_ms': sum(durs), 'durations_ms': durs})
            by_pack_name[(label, r['name'])] = gid
    (ROOT / 'assets' / 'catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    return catalog, by_pack_name


def skin_sets(export_events, by_pack_name):
    sets = {'花嫁': {}, '原皮': {}}
    for state in STATES:
        g = export_events[state]['gif']
        sets['花嫁'][state] = by_pack_name[(g['pack'], g['name'])]
        hit = next((by_pack_name[(p, g['name'])] for p in SKIN_ORDER['原皮'] if (p, g['name']) in by_pack_name), None)
        if not hit:
            sub = SUBS['原皮'][state]
            hit = next(by_pack_name[(p, sub)] for p in SKIN_ORDER['原皮'] if (p, sub) in by_pack_name)
        sets['原皮'][state] = hit
    return sets


def import_audio(export):
    man = json.loads((export / 'bindings.json').read_text(encoding='utf-8'))
    out = ROOT / 'defaults' / 'audio'
    for old in out.iterdir():
        shutil.rmtree(old) if old.is_dir() else old.unlink()
    target = out / AUDIO_DIR; target.mkdir(parents=True)
    clips, n = {}, 0
    for state in STATES:
        e = man['events'][state]; clips[state] = []
        for i, c in enumerate(e['audio_clips'], 1):
            n += 1
            title = f'{n:03}-{e["label"].split(" /")[0].split("/")[0].strip()}{i}'
            title = re.sub(r'[\\/:*?"<>|\s]+', '', title)
            dst = target / f'{title}.ogg'
            subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(export / c['file']), '-c:a', 'libvorbis', '-q:a', '6', str(dst)], check=True)
            dst.with_suffix('.txt').write_text(c['subtitle'] + '\n', encoding='utf-8', newline='\n')
            clips[state].append({'file': f'{AUDIO_DIR}/{dst.name}', 'subtitle': c['subtitle'], 'title': title, 'enabled': True})
    return man['events'], clips


def write_defaults(clips):
    p = ROOT / 'defaults' / 'settings.json'
    d = json.loads(p.read_text(encoding='utf-8'))
    for state, b in d['bindings'].items():
        b.pop('asset', None)  # the GIF comes from the selected skin set
        pool = clips.get(state, [])
        b['audio_clips'] = pool
        if pool:
            b['bubble_mode'] = 'audio'; b['bubble_text'] = pool[0]['subtitle']
        elif b.get('bubble_mode') == 'custom':
            # The previous character's lines must not survive; fall back to the neutral built-in status text
            b['bubble_mode'] = 'auto'; b['bubble_text'] = ''
        b.pop('audio_file', None)
    d['pack'] = '花嫁'
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--gifs', required=True); ap.add_argument('--export', required=True)
    a = ap.parse_args()
    catalog, by_pack_name = import_gifs(pathlib.Path(a.gifs))
    events, clips = import_audio(pathlib.Path(a.export))
    write_defaults(clips)
    sets = skin_sets(events, by_pack_name)
    print(f'gifs {len(catalog)}  clips {sum(len(v) for v in clips.values())}')
    print('PACKS=' + json.dumps(sets, ensure_ascii=False))


if __name__ == '__main__':
    main()
