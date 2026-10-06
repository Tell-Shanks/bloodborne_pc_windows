import sys,unittest,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from windows_graphics import save_settings,load_settings,render_description,validate_settings
from scripts.patches import scaled_sizes
class DlssSettingsTests(unittest.TestCase):
 def test_sizes(self):
  expected={'dlaa':(3840,2160),'quality':(2560,1440),'balanced':(2228,1252),'performance':(1924,1084),'custom':(2880,1620)}
  for mode,size in expected.items():
   with self.subTest(mode=mode): self.assertEqual(scaled_sizes({'upscaler':'dlss','output_res':'3840x2160','dlss_mode':mode,'dlss_scale':'75'}),(size,(3840,2160)))
 def test_native_does_not_inherit_fsr_preset(self):
  self.assertEqual(scaled_sizes({'upscaler':'dlss','output_res':'3840x2160','dlss_mode':'dlaa','preset':'4'})[0],(3840,2160))
 def test_custom_invalid(self):
  for value in ('nan','inf','0','101','32'):
   with self.subTest(value=value),self.assertRaises(ValueError): validate_settings({'dlss_scale':value})
 def test_path_and_mode_roundtrip(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'settings.ini'
   settings={'upscaler':'dlss','dlss_mode':'custom','dlss_scale':'75','dlss_dir':'E:/游戏/DLSS 自选'}
   save_settings(p,settings)
   actual=load_settings(p)
   self.assertEqual(actual['dlss_dir'],settings['dlss_dir']);self.assertEqual(actual['dlss_mode'],'custom')
 def test_dlaa_summary(self):
  self.assertIn('3840×2160',render_description({'upscaler':'dlss','dlss_mode':'dlaa','output_res':'3840x2160'}))
if __name__=='__main__':unittest.main()
