"""An expression lasts as long as its own line; clicks, queued lines and a stalled channel follow fixed rules."""
import pathlib,tempfile,time,unittest,wave
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from selena_pet import pet as module
from selena_pet.audio_player import VoicePlayer,START_LIMIT,END_GRACE
from selena_pet.config_io import save_atomic
from selena_pet.presets import load_defaults


class VoiceChannelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([]);cls.app.setQuitOnLastWindowClosed(False)
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.path=self.root/'line.wav'
        with wave.open(str(self.path),'wb') as f:f.setparams((1,2,8000,0,'NONE','not compressed'));f.writeframes(b'\0\0'*16000)
        self.voice=VoicePlayer(self.root);self.options=dict(audio_enabled=True,volume=0,audio_cooldown=0)
        self.binding=dict(audio_policy='entry',audio_clips=[dict(file=str(self.path))])
    def tearDown(self):self.voice.stop();self.voice.deleteLater();self.app.processEvents();self.tmp.cleanup()
    def say(self,state,**kwargs):
        ok=self.voice.trigger(state,self.binding,self.options,**kwargs)
        if ok:
            self.voice.pending.stop()
            with patch.object(self.voice.player,'play'):self.voice._prepared(self.voice.generation,str(self.path),'')
        return ok

    def test_no_reaction_cuts_a_line_and_none_is_kept_for_later(self):
        for line in ('idle','pet','feed','doubleclick','drop','thinking','working','done','error','paused','waiting'):
            self.assertTrue(self.say(line,owner=1))
            for reaction in ('pet','feed','doubleclick','drag','drop','hover'):
                self.assertFalse(self.say(reaction,owner=2,barge=True))
            self.assertEqual(self.voice.line_state(),line);self.assertTrue(self.voice.speaking(1));self.assertIsNone(self.voice.queued)
            self.voice.stop()

    def test_only_an_audition_replaces_the_line(self):
        self.assertTrue(self.say('idle',owner=1))
        with patch.object(self.voice.player,'fade_out') as fade:self.assertTrue(self.voice.trigger('pet',self.binding,self.options,preview=True))
        fade.assert_called_once();self.assertEqual(self.voice.line_state(),'pet')

    def test_the_log_records_how_each_line_ended(self):
        self.voice.log_path=self.root/'voice-log.txt'
        self.assertTrue(self.say('idle',owner=1));self.voice._finish()
        self.assertTrue(self.say('pet',owner=2));self.voice.stop(reason='静音')
        self.assertTrue(self.say('done',owner=3));self.voice._overdue()
        rows=self.voice.log_path.read_text('utf8').splitlines()
        self.assertEqual(len(rows),6);self.assertIn('idle  line  开始（2.0 秒）',rows[0]);self.assertIn('播完（',rows[1])
        self.assertIn('pet  line  停止：静音',rows[3]);self.assertIn('done  line  超时跳过（',rows[5])

    def test_the_log_stays_small(self):
        self.voice.log_path=self.root/'voice-log.txt';self.voice.log_path.write_text('old line\n'*9000,'utf8')
        self.assertTrue(self.say('idle',owner=1))
        self.assertLess(self.voice.log_path.stat().st_size,50000);self.assertIn('开始',self.voice.log_path.read_text('utf8').splitlines()[-1])

    def test_idle_and_hover_never_interrupt(self):
        self.assertTrue(self.say('pet',owner=1,barge=True))
        self.assertFalse(self.say('hover',owner=2,barge=True));self.assertFalse(self.say('idle',owner=3))
        self.assertEqual(self.voice.line_state(),'pet');self.assertIsNone(self.voice.queued)

    def test_a_waiting_line_is_said_only_while_its_moment_is_on_screen(self):
        for still_there in (False,True):
            self.voice.accept=lambda request:still_there
            self.assertTrue(self.say('pet',owner=1,barge=True))
            self.assertFalse(self.say('waiting',owner=2));self.assertEqual(self.voice.queued['owner'],2)
            self.voice._finish();self.app.processEvents()
            self.assertEqual(self.voice.busy,still_there);self.assertIsNone(self.voice.queued)
            self.voice.stop()

    def test_the_line_belongs_to_its_moment_until_it_ends(self):
        self.assertTrue(self.say('pet',owner=7,barge=True))
        self.assertTrue(self.voice.speaking(7));self.assertFalse(self.voice.speaking(8));self.assertFalse(self.voice.speaking(None))
        self.voice._finish();self.assertFalse(self.voice.speaking(7))

    def test_a_stalled_line_frees_the_channel(self):
        self.assertTrue(self.voice.trigger('pet',self.binding,self.options,owner=1,barge=True))
        self.assertTrue(self.voice.watchdog.isActive());self.assertGreaterEqual(self.voice.watchdog.interval(),START_LIMIT*1000)
        self.voice.pending.stop()
        with patch.object(self.voice.player,'play'):self.voice._prepared(self.voice.generation,str(self.path),'')
        self.assertEqual(self.voice.watchdog.interval(),round(self.voice.player.duration()+END_GRACE*1000))
        self.voice.accept=lambda request:True;self.assertFalse(self.say('done',owner=2));generation=self.voice.generation
        self.voice._overdue();self.app.processEvents()
        # The overdue line is skipped and the waiting task line gets the channel.
        self.assertEqual(self.voice.line_state(),'done');self.assertGreater(self.voice.generation,generation)

    def test_a_late_decode_cannot_restart_a_skipped_line(self):
        self.assertTrue(self.voice.trigger('pet',self.binding,self.options,owner=1,barge=True));self.voice.pending.stop()
        generation=self.voice.generation;self.voice._overdue()
        with patch.object(self.voice.player,'play') as play:self.voice._prepared(generation,str(self.path),'')
        play.assert_not_called();self.assertFalse(self.voice.busy)


class ExpressionTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([]);cls.app.setQuitOnLastWindowClosed(False)
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.old=module.SETTINGS
        module.SETTINGS=self.root/'settings.json';cfg=load_defaults(module.ROOT);cfg['appearance']['audio_enabled']=False
        save_atomic(module.SETTINGS,cfg);self.pet=module.Pet(offline=True);self.pet.timer.stop();self.pet.hover_timer.stop();self.pet.voice.gate.path=self.root/'gate.json'
    def tearDown(self):
        self.pet.voice.stop();self.pet.hide()
        for dialog in (self.pet.binding_editor,self.pet.preferences):
            if dialog:dialog.hide();dialog.deleteLater()
        self.pet.deleteLater();self.app.processEvents();module.SETTINGS=self.old;self.tmp.cleanup()
    def speaking(self,state,owner=None):
        v=self.pet.voice;v.busy=True;v.selected_state=state;v.owner=self.pet.controller.serial if owner is None else owner
    def quiet(self):self.pet.voice.busy=False;self.pet.voice.owner=None
    def long_ago(self):self.pet.controller.started=time.monotonic()-600

    def test_a_reaction_keeps_its_expression_until_its_line_ends(self):
        p=self.pet;p.react('pet');self.assertEqual(p.state,'pet');self.speaking('pet')
        self.long_ago();p.tick();self.assertEqual(p.state,'pet')
        self.quiet();p.tick();self.assertEqual(p.state,'idle')

    def test_without_a_line_the_expression_ends_on_time(self):
        p=self.pet;p.react('pet');self.long_ago();p.tick();self.assertEqual(p.state,'idle')

    def test_a_line_from_an_earlier_moment_does_not_hold_the_expression(self):
        p=self.pet;p.react('pet');self.speaking('thinking',owner=-5);self.long_ago();p.tick();self.assertEqual(p.state,'idle')

    def test_after_a_reaction_the_unfinished_line_brings_its_face_back(self):
        p=self.pet;p.react('pet');self.speaking('pet')
        p.react('doubleclick');self.assertEqual(p.state,'doubleclick');self.assertEqual(p.voice.line_state(),'pet')
        self.long_ago();p.tick();self.assertEqual(p.state,'pet');self.assertTrue(p.voice.speaking(p.controller.serial))
        self.long_ago();p.tick();self.assertEqual(p.state,'pet')
        self.quiet();p.tick();self.assertEqual(p.state,'idle')

    def test_an_idle_line_goes_on_through_a_click(self):
        p=self.pet;p.tick();self.speaking('idle')
        p.react('pet');self.assertEqual(p.state,'pet');self.assertEqual(p.voice.line_state(),'idle')
        self.long_ago();p.tick();self.assertEqual(p.state,'idle');self.assertTrue(p.voice.speaking(p.controller.serial))

    def test_a_dropped_pet_does_not_go_back_to_being_held(self):
        p=self.pet;p.react('drag');self.speaking('drag');p.react('drop')
        self.long_ago();p.tick();self.assertEqual(p.state,'idle')

    def test_the_line_face_does_not_cover_a_running_task(self):
        p=self.pet;p.react('pet');self.speaking('pet');p.react('doubleclick')
        p.on_status(dict(state='working',thread_id='t',turn_id='1',started=1,active=True,stale=False,title='T',events=[]))
        self.long_ago();p.tick();self.assertEqual(p.state,'working');self.assertEqual(p.voice.line_state(),'pet')

    def test_clicks_during_a_completion_line_show_and_the_completion_returns(self):
        p=self.pet;p.set_binding('done',playback='once',hold_seconds=0)
        status=dict(state='writing',thread_id='running',turn_id='live-turn',started=101,active=True,stale=False,title='Still working',
                    events=[dict(state='done',thread_id='A',turn_id='turn-A',started=101,ended=103,title='A')])
        p.on_status(status);self.assertEqual(p.state,'done');self.speaking('done')
        for reaction in ('pet','doubleclick','feed'):
            p.react(reaction);p.tick();self.assertEqual(p.state,reaction);self.assertEqual(p.voice.line_state(),'done')
            self.long_ago();p.tick();self.assertEqual(p.state,'done')
        self.quiet();p.notification_until=0;p.tick();self.assertEqual(p.state,'writing')

    def test_the_same_reaction_is_not_restarted_while_she_is_saying_it(self):
        p=self.pet;p.react('pet');self.speaking('pet');serial=p.controller.serial
        p.react('pet');self.assertEqual(p.controller.serial,serial)
        p.react('doubleclick');self.assertEqual(p.state,'doubleclick')

    def test_the_hover_face_stays_until_its_line_ends(self):
        p=self.pet;p.react('hover');self.assertEqual(p.override,'hover');self.speaking('hover')
        p.release_hover();self.assertEqual(p.state,'hover')
        self.quiet();p.tick();self.assertEqual(p.state,'idle');self.assertIsNone(p.override)
        p.react('hover');p.release_hover();self.assertEqual(p.state,'idle')

    def test_a_completion_comes_back_after_being_dragged_mid_line(self):
        p=self.pet;p.set_binding('done',playback='once',hold_seconds=0)
        status=dict(state='writing',thread_id='running',turn_id='live-turn',started=101,active=True,stale=False,title='Still working',
                    events=[dict(state='done',thread_id='A',turn_id='turn-A',started=101,ended=103,title='A')])
        p.on_status(status);self.assertEqual(p.state,'done');self.speaking('done')
        p.react('drag');p.tick();self.assertEqual(p.state,'drag');self.assertIsNotNone(p.held_notification)
        p.react('drop');self.long_ago();p.tick();self.assertEqual(p.state,'done')
        self.quiet();p.notification_until=0;p.tick();self.assertEqual(p.state,'writing')

    def test_a_completion_is_not_brought_back_once_its_line_is_over(self):
        p=self.pet;p.set_binding('done',playback='once',hold_seconds=0)
        status=dict(state='writing',thread_id='running',turn_id='live-turn',started=101,active=True,stale=False,title='Still working',
                    events=[dict(state='done',thread_id='A',turn_id='turn-A',started=101,ended=103,title='A')])
        p.on_status(status);self.speaking('done');p.react('drag');p.tick();p.react('drop')
        self.quiet();self.long_ago();p.tick();self.assertEqual(p.state,'writing')

    def test_task_progress_still_changes_the_expression_at_once(self):
        p=self.pet
        status=dict(state='waiting',thread_id='t',turn_id='1',started=1,active=True,stale=False,title='T',events=[])
        p.on_status(status);self.assertEqual(p.state,'waiting');self.speaking('waiting')
        p.on_status(dict(status,state='reading'));self.assertEqual(p.state,'reading')

    def test_queued_lines_are_said_only_for_their_own_moment(self):
        p=self.pet;accept=p.accept_queued_line
        self.assertTrue(accept(dict(owner=p.controller.serial)));self.assertFalse(accept(dict(owner=p.controller.serial-1)))
        status=dict(state='reading',thread_id='t',turn_id='1',started=1,active=True,stale=False,title='T',events=[])
        p.on_status(status);task=module.task_key(status)
        self.assertTrue(accept(dict(owner=None,task=task)))
        p.on_status(dict(status,active=False,state='idle'));self.assertFalse(accept(dict(owner=None,task=task)))


if __name__=='__main__':
    unittest.main()
