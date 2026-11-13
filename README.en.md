<!-- README language switch -->
[![中文](https://img.shields.io/badge/%E4%B8%AD%E6%96%87-555555?style=for-the-badge)](README.md) [![English](https://img.shields.io/badge/English-1677ff?style=for-the-badge)](README.en.md)

**v1.0.4**: You choose how long "remind me later" on the rest reminder waits (1–240 minutes, 30 by default); the button on the reminder card shows your choice. Since v1.0.3, 33 voice lines that were cut short when the assets were exported are complete (an installed pet swaps in the full versions after updating), and the last moment of a line is no longer swallowed. A voice line, once started, is always said in full: clicking or dragging her while she speaks changes only her pose. The settings window shows every preview when it opens. Two skins (bridal / original) with 128 expressions, and 115 Selena voice lines set up for 16 interactions. The full package includes a one-click deploy script; later versions update from inside the pet.

<!-- /README language switch -->

<div align="center">

# Selena Codex Desktop Pet

**Selena from *Punishing: Gray Raven* keeps you company in Codex: her expression follows your tasks, and she answers in her own voice.**

[Download for Windows](https://github.com/Doya16/selena-codex-pet/releases/latest) · [User guide (Chinese)](docs/USAGE.md) · [Report an issue](https://github.com/Doya16/selena-codex-pet/issues)

![Selena's expressions for the 16 interactions (bridal skin)](docs/images/events-bridal.jpg)

</div>

For **Windows 10/11 x64**. The full package includes the bridal expression set and a library of 128 GIFs, 115 Selena voice lines with subtitles, and fonts. Expressions, playback timing, bubbles, voices and appearance are preset. Extract the package, double-click the one-click deploy script and you are done; no Python installation is required.

## Installation

**Requirements**: Windows 10 (1809 or later) or Windows 11, 64-bit; Windows 7 / 8 are not supported. Install and sign in to **Codex** on Windows first (the pet also runs without it; connect later).

1. Open [Releases](https://github.com/Doya16/selena-codex-pet/releases/latest) and download **Selena-Codex-Windows-v1.0.4.zip**.
2. Extract it: right-click the ZIP → **Extract All**, or in 7-Zip / WinRAR choose **Extract to "Selena-Codex-Windows-v…\"** (a folder named after the ZIP).
   - Don't choose "Extract here": the ZIP has no top-level folder, so the files would spill into your Downloads folder.
   - Don't extract into a folder you cannot write to, such as `C:\Program Files`, and don't run it from inside the archive viewer.
3. Open the extracted folder and double-click **一键部署.cmd** (one-click deploy). It:
   - checks that the package is complete and the folder is writable;
   - checks for Codex (the pet still runs without it);
   - creates desktop and Start menu shortcuts;
   - starts Selena.
4. Right-click the pet → **Settings**: choose the conversation to follow in **Connect Codex**, and change expressions and voices in the **Interaction Studio**.

Afterwards, start the pet from the desktop shortcut. You can also skip the script and run **赛琳娜Codex桌宠启动.exe** directly; the first launch creates a desktop shortcut too. Keep the other folders next to it.

**If Windows or your security software stops it:**

- If **Windows protected your PC** appears, click **More info** → **Run anyway**; if **Open File - Security Warning** appears, click **Run**. The program has no paid code-signing certificate, which is why Windows asks; it is not a virus.
- If 360, Huorong or another security suite blocks it, add the folder to its trusted list. All source code is public on GitHub: [github.com/Doya16/selena-codex-pet](https://github.com/Doya16/selena-codex-pet). Every release page has a SHA256SUMS file for checking that your download is complete and unmodified.

When a new version is out, the pet tells you; click **更新并重启赛琳娜** (update and restart Selena) to update in one step, keeping your settings and assets (see "One-click updates" below).

Sound is on by default at 10% volume. Change it in Settings → Desktop & Sound.

## Expressions

Selena uses the **bridal** sticker set by default; every one of the 16 interactions has its own bridal expression.

The library also holds the original-outfit, community, Christmas and New Year stickers, 128 in all. In **Settings → Interaction Studio** you can give any interaction any of them, or import your own images.

## One-click updates

The pet checks for new versions in the background (every 6 hours by default). When one is available, a silent notice appears next to the pet; click **更新并重启赛琳娜** (update and restart Selena) to download, verify, install and restart.

- Only program files are downloaded; GIFs, voices, subtitles, fonts and all your settings stay.
- The update manifest is signed with the publisher's offline key (Ed25519). An update with a wrong signature is never installed, whether it comes from GitHub or a mirror.
- An interrupted download leaves the current program untouched; an interrupted install, or a new version that fails to start, rolls back to the previous version and settings.
- The update source can be **Auto / GitHub / Mirror (mainland China)**. The mirror is the third-party [GH-Proxy](https://gh-proxy.com/docs/github-accelerator) and only carries the files.

![Version and update settings](docs/images/updates.png)

## Features

- **Follows your tasks**: thinking, reading, editing, waiting and done each have their own expression. With several projects running, each conversation's completion notice plays in turn.
- **Mouse interactions**: click (head pat), double-click, hover, drag, drop and milk tea, each with a response and voice.
- **Selena's voice**: 115 lines from the Tempest, Capriccio and Pianissimo frame voices and event-story voice acting, each with a subtitle; several lines per action are picked at random.
- **Your own media**: choose any GIF or image per interaction; loop, speed, hold time and next state are adjustable; import your own images and audio.
- **Companion features**: completion float with elapsed time and confetti, edge docking, full-screen hiding, daily recap, water and break reminders.
- **Appearance and quota**: live scaling, fonts and sizes, and the Codex plan's remaining share or overage credits under the pet.
- **Save and move**: pack GIFs, voices, bubbles, fonts and all settings, and take them to another computer.

![Interaction Studio](docs/images/studio.png)

**Sound and tray**: the Windows volume mixer lists the pet as “赛琳娜 · Codex”, so its volume can be set on its own. The tray tooltip is “赛琳娜 · Codex · 点击唤醒/隐藏”; click it to show or hide the pet.

## Credits

Stickers: shared by the **Selena fan QQ group 978621218** (赛琳娜厨子). Thank you for making and sharing them.

Voice lines: Selena (Tempest, Capriccio, Pianissimo) frame voices and event-story voice acting from *Punishing: Gray Raven*.

Character art, stickers and original voices belong to their respective rights holders (*Punishing: Gray Raven* © KURO GAMES). This is a fan project and is not affiliated with the official game. The stickers are for personal, non-commercial use only; do not resell them or include them in paid distributions. The software and font licenses do not cover the character assets; see [asset credits](assets/CREDITS.txt) and [third-party licenses](THIRD_PARTY.txt).

<details>
<summary>Run from source</summary>

With Python 3.12, in the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m selena_pet
```

Build the portable edition with `tools/build_portable.py` (after installing `tools/requirements-build.txt`); release files come from `tools/make_release.py`, and update manifests are signed with `tools/sign_update.py --key`.

Tests: `.\.venv\Scripts\python.exe -m unittest discover -s tests`.

</details>
