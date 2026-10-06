import sys
import unittest
import tkinter as tk
from tkinter import ttk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from windows_graphics_ui import GraphicsPanel, configure_style
from windows_graphics import DEFAULTS


class LauncherUiTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        configure_style(self.root)
        self.tabs = ttk.Notebook(self.root)
        self.panel = GraphicsPanel(self.tabs, DEFAULTS | {
            'upscaler': 'dlss', 'dlss_mode': 'balanced', 'preset': '0', 'output_res': '3840x2160'}, notebook=self.tabs)

    def tearDown(self):
        self.root.destroy()

    def choose(self, key, value):
        p = self.panel
        p._vars[key].set(next(label for label, item in p._labels[key].items() if item == value))

    def visible(self, group):
        return self.panel._groups[group].winfo_manager() == 'grid'

    def test_dlss_mode_is_editable_and_matches_summary(self):
        self.assertEqual(str(self.panel.dlss_control['state']), 'readonly')
        self.assertTrue(self.visible('dlss'))
        self.assertFalse(self.visible('fsr'))
        self.assertIn('平衡', self.panel.summary.get())
        self.assertIn('2228×1252', self.panel.summary.get())
        self.assertEqual(self.panel.changes(), {})
        self.choose('dlss_mode', 'dlaa')
        self.assertIn('场景渲染 3840×2160', self.panel.summary.get())
        self.assertEqual(self.panel.changes(), {'dlss_mode': 'dlaa'})

    def test_switch_preserves_separate_modes_and_relevant_controls(self):
        self.choose('upscaler', 'fsr4')
        self.assertTrue(self.visible('fsr'))
        self.assertTrue(self.visible('exposure'))
        self.assertFalse(self.visible('dll'))
        self.assertFalse(self.visible('reactive'))
        self.choose('preset', '3')
        self.choose('upscaler', 'dlss')
        self.assertEqual(self.panel.values()['dlss_mode'], 'balanced')
        self.assertEqual(self.panel.values()['preset'], '3')
        self.assertFalse(self.visible('exposure'))
        self.choose('upscaler', 'taa')
        self.assertFalse(self.visible('dlss'))
        self.assertFalse(self.visible('fsr'))

    def test_custom_ratio_and_resolution_update_together(self):
        self.choose('dlss_mode', 'custom')
        self.assertTrue(self.visible('custom'))
        self.panel._vars['dlss_scale'].set('75')
        self.assertIn('2880×1620', self.panel.summary.get())
        self.choose('output_res', '2560x1440')
        self.assertEqual(self.panel.changes()['output_res'], '2560x1440')
        self.assertIn('输出 2560×1440', self.panel.summary.get())
        self.panel.mark_saved()
        self.assertEqual(self.panel.changes(), {})

    def test_profile_uses_same_resolution_control(self):
        self.panel.set_profile('1920x1080', '1')
        self.assertEqual(self.panel.values()['output_res'], '1920x1080')
        self.assertEqual(len(self.tabs.tabs()), 3)


if __name__ == '__main__':
    unittest.main()
