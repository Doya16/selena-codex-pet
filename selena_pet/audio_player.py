"""Optional local-file audio. Missing or disabled audio is a no-op."""
import pathlib,time,os,sys,threading,copy,random
from .voice_pool import clips_for,pick_clip,TaskVoiceGate,clip_bubble_text
from .audio_convert import playable_path
if sys.platform=='win32': os.environ.setdefault('QT_MEDIA_BACKEND','windows')
from PySide6.QtCore import QObject,QTimer,QUrl,Signal
from PySide6.QtMultimedia import QMediaPlayer
from .pcm_player import PcmPlayer
AUDIO_EXTS={'.wav','.mp3','.ogg','.flac','.m4a','.aac'}
# Lines about the task itself: never cut short by a click, and a click waits until they are said.
TASK_LINES={'error','waiting','done','paused'}
# Longest wait for a line to be decoded and start, and how long past its own length it may run, before
# the channel is freed anyway (a stalled decoder or audio device must never hold expressions or queued lines).
START_LIMIT,END_GRACE=20.0,2.5
def resolve_audio(value,directory,root):
    if not isinstance(value,str) or not value.strip(): return None
    path=pathlib.Path(value)
    if not path.is_absolute():
        base=pathlib.Path(directory or 'audio')
        if not base.is_absolute(): base=pathlib.Path(root)/base
        path=base/path
    return path if path.suffix.lower() in AUDIO_EXTS and path.is_file() else None

class VoicePlayer(QObject):
    status=Signal(str)
    prepared=Signal(int,str,str)
    changed=Signal()
    def __init__(self,root,parent=None):
        super().__init__(parent); self.root=root; self.player=PcmPlayer(self); self.output=self.player
        self.pending=QTimer(self); self.pending.setSingleShot(True); self.pending.timeout.connect(self._play_pending)
        self.last_play={}; self.last_clip={}; self.next_path=None; self.selected_clip=None; self.selected_state=None; self.generation=0; self.gate=TaskVoiceGate(root/'voice-history.json')
        self.busy=False; self.queued=None; self.selected_binding={}; self.started_at=0
        self.session_played=set(); self.selected_automatic=False
        # The on-screen moment (an expression entry) the current line belongs to; None for a line with no expression of its own.
        self.owner=None
        # Decides whether a line that waited for the previous one still belongs on screen; set by the pet.
        self.accept=None
        self.watchdog=QTimer(self); self.watchdog.setSingleShot(True); self.watchdog.timeout.connect(self._overdue)
        self.prepared.connect(self._prepared)
        self.player.errorOccurred.connect(self._error)
        self.player.mediaStatusChanged.connect(self._media_status)
    def stop(self,fade=False):
        self.generation+=1; self.queued=None; self.busy=False; self.owner=None; self.pending.stop(); self.watchdog.stop()
        if fade: self.player.fade_out()
        self.player.stop(); self.player.setSource(QUrl()); self.next_path=None; self.selected_clip=None; self.selected_state=None; self.selected_binding={}; self.changed.emit()
    def speaking(self,owner):
        """Whether the line being said belongs to this on-screen moment."""
        return self.busy and owner is not None and self.owner==owner
    def line_state(self):
        return self.selected_state if self.busy else None
    def _error(self,*_):
        self.status.emit('音频暂时无法播放，桌宠继续运行。'); self._finish()
    def _media_status(self,status):
        if status==QMediaPlayer.MediaStatus.EndOfMedia: self._finish()
    def _overdue(self):
        if not self.busy: return
        # A late decode result must not start this line after all.
        self.generation+=1; self.pending.stop(); self.player.stop()
        self.status.emit('这句语音没有按时播完，已跳过。'); self._finish()
    def _finish(self):
        if not self.busy: return
        self.busy=False; self.owner=None; self.next_path=None; self.watchdog.stop(); self.changed.emit()
        if self.queued:
            generation=self.generation
            QTimer.singleShot(0,lambda:self._drain(generation))
    def _drain(self,generation):
        if generation!=self.generation or self.busy or not self.queued: return
        request=self.queued; self.queued=None
        # A line whose moment has passed is dropped rather than said over a different expression.
        if self.accept and not self.accept(request): return
        self.trigger(request['state'],request['binding'],request['options'],task=request['task'],owner=request.get('owner'))
    def priority(self,state,binding):
        if state in ('error','waiting','done','paused'): return 3
        if binding.get('audio_policy')=='turn': return 2
        return 1
    def trigger(self,state,binding,options,preview=False,now=None,task=None,notification=False,owner=None,barge=False):
        """Start a line, or keep it for later. owner: the on-screen moment it belongs to (that expression stays
        until the line ends). barge: a mouse reaction; it may cut a line that is not about the task, and is
        never kept for later, because said later it would no longer match the expression."""
        if options.get('audio_muted'):
            if preview: self.status.emit('安静陪伴（静音）已开启，请先在设置或右键菜单取消静音。')
            return False
        if not preview and (not options.get('audio_enabled') or not binding.get('audio_enabled',True)): return False
        policy=binding.get('audio_policy','entry')
        if not preview and policy=='session' and state in self.session_played: return False
        once=(policy=='turn' or notification) and not preview
        if once and (task is None or self.gate.contains(state,task)): return False
        candidates=[]; seen=set()
        for clip in clips_for(binding):
            path=resolve_audio(clip['file'],options.get('audio_directory','audio'),self.root)
            if not clip['enabled'] or not path: continue
            identity=os.path.normcase(str(path.resolve()))
            pair=(identity,clip_bubble_text(clip))
            if pair in seen: continue
            seen.add(pair); candidates.append(dict(clip,path=path,identity=identity))
        if not candidates:
            if preview: self.status.emit('没有可播放的音频，请先选择一个有效文件。')
            return False
        now=time.monotonic() if now is None else now
        # A fresh task may notify immediately, even within the general cooldown.
        if not preview and not once and now-self.last_play.get(state,-1e12)<options.get('audio_cooldown',12): return False
        # Protect a whole utterance, including its delay and decoder startup.
        # Passive idle/hover must not cut in after a short GIF or mouse leave.
        cut=False
        if not preview and self.busy:
            if state in ('idle','hover'): return False
            if barge:
                if self.selected_state in TASK_LINES: return False
                cut=True
            else:
                request=dict(state=state,binding=copy.deepcopy(binding),options=dict(options),task=task,owner=owner)
                if not self.queued or self.priority(state,binding)>=self.priority(self.queued['state'],self.queued['binding']): self.queued=request
                return False
        if not preview and policy=='occasional':
            if now-self.last_play.get(state,-1e12)<binding.get('audio_min_interval',300): return False
            if random.random()*100>=binding.get('audio_chance',20): return False
        selected=pick_clip(candidates,self.last_clip.get(state),binding.get('audio_avoid_repeat',True))
        deferred=self.queued if not preview else None
        self.stop(fade=cut or (preview and self.busy))
        self.queued=deferred
        if once: self.gate.mark(state,task)
        self.owner=owner; self.watchdog.start(round((START_LIMIT+(0 if preview else binding.get('audio_delay',0)))*1000))
        path=selected['path']; self.selected_clip=selected; self.selected_state=state; self.last_clip[state]=selected['identity']
        self.selected_binding=copy.deepcopy(binding); self.started_at=time.monotonic(); self.busy=True
        self.selected_automatic=not preview
        self.output.setVolume(options.get('volume',75)/100); self.next_path=path
        if not preview: self.last_play[state]=now
        self.pending.start(round((0 if preview else binding.get('audio_delay',0))*1000)); self.changed.emit(); return True
    def _play_pending(self):
        if self.next_path and self.next_path.is_file():
            path=self.next_path; generation=self.generation
            def decode():
                try: ready=str(playable_path(path,self.root/'.audio-cache')); error=''
                except Exception as exc: ready=''; error=str(exc)
                try: self.prepared.emit(generation,ready,error)
                except RuntimeError: pass
            threading.Thread(target=decode,daemon=True).start()
        else: self._error()
    def _prepared(self,generation,path,error):
        if generation!=self.generation: return
        if error: self.status.emit('音频无法解码：'+error); self._finish(); return
        self.player.setSource(QUrl.fromLocalFile(str(pathlib.Path(path).resolve())))
        if self.player.error()!=QMediaPlayer.Error.NoError: return
        self.player.play()
        if self.player.error()==QMediaPlayer.Error.NoError:
            self.watchdog.start(round(self.player.duration()+END_GRACE*1000))
            if self.selected_automatic: self.session_played.add(self.selected_state)
            self.status.emit('正在播放：'+(self.selected_clip.get('title') or pathlib.Path(path).name))
