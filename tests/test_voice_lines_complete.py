"""Every shipped line is whole: fixed lines reach installed pets, and playback does not drop the last moment."""
import hashlib,json,pathlib,tempfile,time,unittest,wave
from PySide6.QtCore import QEventLoop,QTimer,QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QAudioFormat,QMediaDevices,QMediaPlayer
from selena_pet.pcm_player import PcmPlayer,TAIL_SECONDS,with_tail
from selena_pet.update_package import program_file
from selena_pet.voice_repair import repair

ROOT=pathlib.Path(__file__).resolve().parents[1]
sha=lambda data:hashlib.sha256(data).hexdigest()


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name)
        self.source=self.root/'resources/voice-repair';self.source.mkdir(parents=True)
        self.audio=self.root/'audio/赛琳娜语音';self.audio.mkdir(parents=True)
        self.defaults=self.root/'defaults/audio/赛琳娜语音';self.defaults.mkdir(parents=True)
        self.old,self.new=b'short line',b'the whole line'
        (self.source/'043.ogg').write_bytes(self.new)
        self.write_table({'043.ogg':{'old':[sha(self.old)],'sha256':sha(self.new),'bytes':len(self.new)}})
    def tearDown(self):self.tmp.cleanup()
    def write_table(self,files,directory='赛琳娜语音'):
        (self.source/'repairs.json').write_text(json.dumps({'directory':directory,'files':files}),'utf8')

    def test_an_unchanged_shipped_line_is_replaced_in_both_folders_once(self):
        for folder in (self.audio,self.defaults):(folder/'043.ogg').write_bytes(self.old)
        self.assertEqual(repair(self.root,self.root/'audio'),['043.ogg','043.ogg'])
        for folder in (self.audio,self.defaults):self.assertEqual((folder/'043.ogg').read_bytes(),self.new)
        self.assertEqual(repair(self.root,self.root/'audio'),[])
        self.assertEqual(sorted(p.name for p in self.audio.iterdir()),['043.ogg'])

    def test_the_users_own_file_and_a_removed_line_are_left_alone(self):
        (self.audio/'043.ogg').write_bytes(b'my own recording')
        self.assertEqual(repair(self.root,self.root/'audio'),[])
        self.assertEqual((self.audio/'043.ogg').read_bytes(),b'my own recording');self.assertFalse((self.defaults/'043.ogg').exists())

    def test_a_custom_audio_folder_is_repaired_and_the_same_folder_counts_once(self):
        mine=self.root/'mine/赛琳娜语音';mine.mkdir(parents=True);(mine/'043.ogg').write_bytes(self.old)
        self.assertEqual(repair(self.root,self.root/'mine'),['043.ogg']);self.assertEqual((mine/'043.ogg').read_bytes(),self.new)
        (self.defaults/'043.ogg').write_bytes(self.old)
        self.assertEqual(repair(self.root,self.root/'defaults/audio'),['043.ogg'])

    def test_a_damaged_or_unsafe_table_changes_nothing(self):
        (self.audio/'043.ogg').write_bytes(self.old)
        (self.source/'043.ogg').write_bytes(b'tampered')
        self.assertEqual(repair(self.root,self.root/'audio'),[])
        (self.source/'043.ogg').write_bytes(self.new)
        for files,directory in (({'../043.ogg':{'old':[sha(self.old)],'sha256':sha(self.new)}},'赛琳娜语音'),
                                ({'043.ogg':{'old':[sha(self.old)],'sha256':sha(self.new)}},'..'),([],'赛琳娜语音')):
            self.write_table(files,directory);self.assertEqual(repair(self.root,self.root/'audio'),[])
        (self.source/'repairs.json').write_text('{','utf8');self.assertEqual(repair(self.root,self.root/'audio'),[])
        (self.source/'repairs.json').unlink();self.assertEqual(repair(self.root,self.root/'audio'),[])
        self.assertEqual((self.audio/'043.ogg').read_bytes(),self.old)

    def test_the_fixed_lines_travel_in_the_program_update(self):
        self.assertTrue(program_file('resources/voice-repair/043-递奶茶2.ogg'))
        self.assertTrue(program_file('resources/voice-repair/repairs.json'))
        self.assertFalse(program_file('audio/赛琳娜语音/043-递奶茶2.ogg'))


class ShippedRepairTableTests(unittest.TestCase):
    def test_the_table_matches_the_shipped_lines(self):
        table_path=ROOT/'resources/voice-repair/repairs.json'
        if not table_path.exists():self.skipTest('no shipped line changed')
        table=json.loads(table_path.read_text('utf8'));shipped=ROOT/'defaults/audio'/table['directory']
        self.assertTrue(table['files'])
        for name,entry in table['files'].items():
            data=(ROOT/'resources/voice-repair'/name).read_bytes()
            self.assertEqual(sha(data),entry['sha256']);self.assertEqual(len(data),entry['bytes'])
            self.assertEqual((shipped/name).read_bytes(),data,name)
            self.assertTrue(entry['old']);self.assertNotIn(entry['sha256'],entry['old'])
        self.assertEqual(sorted(p.name for p in (ROOT/'resources/voice-repair').iterdir()),sorted([*table['files'],'repairs.json']))


class TailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_silence_follows_every_line_in_the_sinks_own_format(self):
        for rate,channels,sample,size in ((48000,1,QAudioFormat.SampleFormat.Int16,2),(44100,2,QAudioFormat.SampleFormat.Float,4),
                                          (48000,2,QAudioFormat.SampleFormat.Int32,4)):
            fmt=QAudioFormat();fmt.setSampleRate(rate);fmt.setChannelCount(channels);fmt.setSampleFormat(sample)
            data=b'\x01\x02'*(channels*size)*10;out=with_tail(data,fmt)
            self.assertTrue(out.startswith(data));self.assertEqual(out[len(data):],bytes(round(rate*TAIL_SECONDS)*channels*size))
            self.assertGreaterEqual(TAIL_SECONDS,0.35)

    def test_a_line_ends_only_after_it_has_been_played(self):
        if QMediaDevices.defaultAudioOutput().isNull():self.skipTest('no audio output')
        with tempfile.TemporaryDirectory() as tmp:
            path=pathlib.Path(tmp)/'line.wav'
            with wave.open(str(path),'wb') as f:f.setparams((1,2,48000,0,'NONE','not compressed'));f.writeframes(b'\0\0'*14400)
            player=PcmPlayer();player.setVolume(0);loop=QEventLoop();ended=[]
            def status(value):
                if value==QMediaPlayer.MediaStatus.EndOfMedia:ended.append((time.perf_counter()-start,player.position()));loop.quit()
            player.mediaStatusChanged.connect(status);QTimer.singleShot(5000,loop.quit)
            player.setSource(QUrl.fromLocalFile(str(path)));start=time.perf_counter();player.play();loop.exec()
            player.stop()
        self.assertEqual(len(ended),1);elapsed,position=ended[0]
        self.assertEqual(position,300)
        # The 0.3 s line has been handed out and played; what the device still held when it stopped was silence.
        self.assertGreater(elapsed,0.3+TAIL_SECONDS-0.26)


if __name__=='__main__':unittest.main()
