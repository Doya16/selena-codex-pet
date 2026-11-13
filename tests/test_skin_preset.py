"""The 原皮 expression preset was removed: Selena always starts from the bridal set, while the original-outfit
stickers stay in the library for anyone who picks them one interaction at a time."""
import pathlib,tempfile,unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QComboBox
from selena_pet import pet as module
from selena_pet.config_io import save_atomic


class OriginalPresetRemovedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([]);cls.app.setQuitOnLastWindowClosed(False)

    def make(self,**settings):
        self.temp=tempfile.TemporaryDirectory();path=pathlib.Path(self.temp.name)/'settings.json'
        save_atomic(path,dict(appearance=dict(audio_muted=True),**settings))
        self.patch=patch.object(module,'SETTINGS',path);self.patch.start()
        self.pet=module.Pet(offline=True);self.pet.timer.stop();self.pet.slow_timer.stop()
        return self.pet

    def tearDown(self):
        if getattr(self.pet,'preferences',None):self.pet.preferences.hide()
        self.pet.hide();self.patch.stop();self.temp.cleanup()

    def test_only_the_bridal_preset_is_left(self):
        pet=self.make();self.assertEqual(list(module.PACKS),['花嫁']);self.assertEqual(pet.pack,'花嫁')

    def test_a_saved_original_preset_falls_back_to_bridal(self):
        pet=self.make(pack='原皮');self.assertEqual(pet.pack,'花嫁')
        for state,asset in module.PACKS['花嫁'].items():self.assertEqual(pet.binding(state)['asset'],asset,state)

    def test_imported_settings_with_the_original_preset_fall_back_too(self):
        pet=self.make();pet.apply_settings(dict(pet.settings,pack='原皮'))
        self.assertEqual(pet.pack,'花嫁');self.assertEqual(pet.binding('idle')['asset'],module.PACKS['花嫁']['idle'])

    def test_original_stickers_stay_in_the_library_and_a_chosen_one_is_kept(self):
        original=[a['id'] for a in module.CATALOG if a.get('skin')=='原皮']
        self.assertEqual(len(original),48)
        pet=self.make(pack='原皮',bindings=dict(pet=dict(asset=original[0])))
        self.assertEqual(pet.binding('pet')['asset'],original[0])
        self.assertEqual(pet.binding('idle')['asset'],module.PACKS['花嫁']['idle'])

    def test_the_settings_offer_no_skin_preset(self):
        pet=self.make();pet.open_preferences('桌面与声音');d=pet.preferences
        texts=[c.itemText(i) for c in d.findChildren(QComboBox) for i in range(c.count())]
        self.assertFalse([t for t in texts if '原皮' in t or '花嫁' in t],texts)


if __name__=='__main__':
    unittest.main()
