# Windows port modifications by yaonikaixin999999, 2026-10-05.
# 2026-10-06: dark/light theming, per-monitor DPI awareness and a Bloodborne-styled launcher.
# SPDX-License-Identifier: GPL-2.0-or-later
"""Chinese graphics controls and the shared launcher theme for the Windows launcher."""

import ctypes
import math
import os
import tkinter as tk
from tkinter import ttk, filedialog

from windows_graphics import (
    BOOLEAN_LABELS,
    DEFAULTS,
    LOD_LABELS,
    PRESET_LABELS,
    UPSCALER_LABELS,
    render_description,
    validate_settings,
)

# Two palettes in the Bloodborne register: moonlit night and aged parchment.
# The accent is the gold of the game's logo; red stays reserved for errors.
PALETTES = {
    'dark': {
        'bg': '#14161a', 'surface': '#1c2026', 'field': '#22262d', 'tab_bg': '#191c21',
        'border': '#30353d', 'ink': '#e9e6dd', 'muted': '#9ba1a9',
        'accent': '#c9a227', 'accent_hover': '#dcb63c', 'on_accent': '#17130a',
        'accent_soft': '#2a2517', 'indicator': '#20262d', 'indicator_border': '#5a636e',
    },
    'light': {
        'bg': '#f2f1ec', 'surface': '#fbfaf6', 'field': '#ffffff', 'tab_bg': '#e9e7dd',
        'border': '#d8d4c8', 'ink': '#24201a', 'muted': '#6b6558',
        'accent': '#8a6d1f', 'accent_hover': '#6f5716', 'on_accent': '#fffdf4',
        'accent_soft': '#efe9d6', 'indicator': '#ffffff', 'indicator_border': '#b5ae9c',
    },
}

_SCALE = 1.0


def px(value):
    """A logical pixel count scaled for the current monitor DPI."""
    return int(round(value * _SCALE))


def ui_scale():
    return _SCALE


def enable_dpi_awareness():
    """Per-monitor DPI awareness. Must run before the first Tk window exists.

    SetProcessDpiAwarenessContext takes a handle, not an int: without argtypes
    ctypes passes a zero-extended 32-bit value and the call fails with
    ERROR_INVALID_PARAMETER (87). Check the result rather than assume success.
    """
    if os.name != 'nt':
        return
    user32 = ctypes.windll.user32
    try:
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.SetProcessDpiAwarenessContext.restype = ctypes.c_bool
        if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):  # per-monitor v2
            return
    except (AttributeError, OSError):
        pass
    try:
        if ctypes.windll.shcore.SetProcessDpiAwareness(2) == 0:  # S_OK
            return
    except (AttributeError, OSError):
        pass


def init_scale(root):
    """Adopt the real monitor DPI for both widgets and point sizes."""
    global _SCALE
    dpi = float(root.winfo_fpixels('1i'))
    if dpi <= 0:
        dpi = 96.0
    _SCALE = dpi / 96.0
    root.tk.call('tk', 'scaling', dpi / 72.0)
    return _SCALE


def detect_system_theme():
    """'light' or 'dark' from the Windows apps preference; dark on any failure."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize') as key:
            return 'light' if winreg.QueryValueEx(key, 'AppsUseLightTheme')[0] else 'dark'
    except OSError:
        return 'dark'


def _refresh_popdowns(root):
    """Re-apply the option database to combobox listboxes that already exist."""
    stack = [root]
    while stack:
        widget = stack.pop()
        try:
            stack.extend(widget.winfo_children())
        except tk.TclError:
            continue
        if isinstance(widget, ttk.Combobox):
            try:
                widget.tk.call('ttk::combobox::ConfigureListbox', widget)
            except tk.TclError:
                pass


def configure_style(root, theme=None):
    """Apply the launcher theme. Returns the palette; call again to switch themes."""
    import tkinter.font as tkfont
    palette = PALETTES.get(theme or detect_system_theme(), PALETTES['dark'])
    for name in ('TkDefaultFont', 'TkTextFont', 'TkMenuFont', 'TkHeadingFont'):
        tkfont.nametofont(name).configure(family='Microsoft YaHei UI', size=10)

    root.configure(background=palette['bg'])
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure(
        '.', background=palette['bg'], foreground=palette['ink'], font='TkDefaultFont',
        bordercolor=palette['border'], darkcolor=palette['surface'],
        lightcolor=palette['surface'], troughcolor=palette['field'],
        focuscolor=palette['accent'])

    style.configure('TNotebook', background=palette['bg'], borderwidth=0,
                    tabmargins=(0, 0, px(10), 0))
    style.configure('TNotebook.Tab', background=palette['tab_bg'], foreground=palette['muted'],
                    padding=(px(22), px(9)), borderwidth=0, focuscolor=palette['tab_bg'])
    style.map('TNotebook.Tab',
              background=[('selected', palette['surface']), ('active', palette['field'])],
              foreground=[('selected', palette['accent'])])

    style.configure('TButton', padding=(px(16), px(7)), background=palette['surface'],
                    foreground=palette['ink'], bordercolor=palette['border'],
                    borderwidth=1, relief='flat', focuscolor=palette['surface'])
    style.map('TButton',
              background=[('active', palette['field']), ('pressed', palette['field']),
                          ('disabled', palette['bg'])],
              foreground=[('disabled', palette['muted'])],
              bordercolor=[('active', palette['accent'])])
    style.configure('Primary.TButton', background=palette['accent'],
                    foreground=palette['on_accent'], bordercolor=palette['accent'],
                    font=('Microsoft YaHei UI', 10, 'bold'), focuscolor=palette['accent'])
    style.map('Primary.TButton',
              background=[('active', palette['accent_hover']), ('pressed', palette['accent_hover']),
                          ('disabled', palette['border'])],
              foreground=[('disabled', palette['muted'])],
              bordercolor=[('disabled', palette['border'])])

    style.configure('TCombobox', padding=px(6), fieldbackground=palette['field'],
                    background=palette['field'], foreground=palette['ink'],
                    arrowcolor=palette['muted'], bordercolor=palette['border'],
                    lightcolor=palette['field'], darkcolor=palette['field'],
                    selectbackground=palette['accent'], selectforeground=palette['on_accent'])
    style.map('TCombobox',
              fieldbackground=[('readonly', palette['field']), ('disabled', palette['bg'])],
              foreground=[('readonly', palette['ink']), ('disabled', palette['muted'])],
              arrowcolor=[('disabled', palette['muted'])],
              bordercolor=[('focus', palette['accent'])])

    style.configure('TEntry', padding=px(7), fieldbackground=palette['field'],
                    foreground=palette['ink'], insertcolor=palette['ink'],
                    bordercolor=palette['border'], lightcolor=palette['field'],
                    darkcolor=palette['field'])
    style.map('TEntry', bordercolor=[('focus', palette['accent'])])
    style.configure('TSpinbox', padding=px(5), fieldbackground=palette['field'],
                    foreground=palette['ink'], insertcolor=palette['ink'],
                    arrowcolor=palette['muted'], bordercolor=palette['border'],
                    lightcolor=palette['field'], darkcolor=palette['field'])
    style.map('TSpinbox', bordercolor=[('focus', palette['accent'])])

    # clam draws an X-shaped mark for the selected state; painting the mark in the
    # fill colour turns it into a clean solid-filled box instead (no ambiguity).
    style.configure('TCheckbutton', background=palette['bg'], foreground=palette['ink'],
                    focuscolor=palette['bg'], indicatorbackground=palette['indicator'],
                    indicatorforeground=palette['indicator'],
                    upperbordercolor=palette['indicator_border'],
                    lowerbordercolor=palette['indicator_border'],
                    indicatorsize=px(14), bordercolor=palette['border'], padding=px(3))
    style.map('TCheckbutton',
              indicatorbackground=[('selected', palette['accent']), ('pressed', palette['indicator'])],
              indicatorforeground=[('selected', palette['accent'])],
              upperbordercolor=[('selected', palette['accent'])],
              lowerbordercolor=[('selected', palette['accent'])],
              background=[('active', palette['bg'])])

    style.configure('TScale', background=palette['bg'], troughcolor=palette['field'],
                    bordercolor=palette['border'], lightcolor=palette['field'],
                    darkcolor=palette['field'])
    style.configure('TSeparator', background=palette['border'])
    style.configure('TLabelframe', background=palette['bg'], bordercolor=palette['border'])
    style.configure('TLabelframe.Label', background=palette['bg'], foreground=palette['muted'])

    style.configure('Title.TLabel', font=('Microsoft YaHei UI', 24, 'bold'),
                    foreground=palette['ink'])
    style.configure('Logo.TLabel', font=('Georgia', 10), foreground=palette['accent'])
    style.configure('Section.TLabel', font=('Microsoft YaHei UI', 12, 'bold'),
                    foreground=palette['ink'])
    style.configure('Muted.TLabel', foreground=palette['muted'])
    style.configure('Summary.TLabel', background=palette['accent_soft'],
                    foreground=palette['ink'], padding=(px(12), px(9)))

    root.option_add('*TCombobox*Listbox.background', palette['field'], priority='interactive')
    root.option_add('*TCombobox*Listbox.foreground', palette['ink'], priority='interactive')
    root.option_add('*TCombobox*Listbox.selectBackground', palette['accent'], priority='interactive')
    root.option_add('*TCombobox*Listbox.selectForeground', palette['on_accent'], priority='interactive')
    _refresh_popdowns(root)
    return palette


class GraphicsPanel(ttk.Frame):
    """Edit a settings snapshot and report only the user's changed fields."""

    def __init__(self, parent, settings, *, notebook=None):
        super().__init__(parent, padding=(px(24), px(20)))
        self._initial = validate_settings({**DEFAULTS, **settings})
        self._vars = {}
        self._labels = {}
        self._scales = {}
        self._syncing_scale = False
        self._forced_dirty = set()
        self.dirty_keys = set()
        self._output_res = self._initial['output_res']
        self._ready = False
        self._groups = {}

        if notebook is None:
            notebook = ttk.Notebook(self)
            notebook.pack(fill='both', expand=True)
            quality = ttk.Frame(notebook, padding=px(20))
        else:
            quality = self
        effects = ttk.Frame(notebook, padding=(px(24), px(20)))
        advanced = ttk.Frame(notebook, padding=(px(24), px(20)))
        notebook.add(quality, text='画面质量')
        notebook.add(effects, text='游戏特效')
        notebook.add(advanced, text='高级选项')
        for tab in (quality, effects, advanced):
            tab.columnconfigure(0, minsize=px(150))
            tab.columnconfigure(1, weight=1)

        self._heading(quality, '画面质量', '先选输出分辨率，再选择抗锯齿或超分模式。')
        self._choice(quality, 2, '输出分辨率', 'output_res', {
            '720p · 1280 × 720': '1280x720', '1080p · 1920 × 1080': '1920x1080',
            '1440p · 2560 × 1440': '2560x1440', '4K · 3840 × 2160': '3840x2160'})
        available = {label: value for label, value in UPSCALER_LABELS.items() if value != 'fsr411'}
        self.upscaler_control = self._choice(quality, 3, '超分 / 抗锯齿', 'upscaler',
                                             UPSCALER_LABELS, selectable=available)
        self.preset_control = self._choice(self._group(quality, 4, 'fsr'), 0,
                                            '画质档位', 'preset', PRESET_LABELS)
        self.dlss_control = self._choice(self._group(quality, 4, 'dlss'), 0,
            'DLSS 档位', 'dlss_mode', {'DLAA · 原生抗锯齿': 'dlaa', '画质': 'quality',
                                     '平衡': 'balanced', '性能': 'performance', '自定义': 'custom'})
        self._number(self._group(quality, 5, 'custom'), 0, '渲染比例（%）', 'dlss_scale', 33, 100)
        self.summary = tk.StringVar()
        ttk.Label(quality, textvariable=self.summary, style='Summary.TLabel',
                  wraplength=px(700)).grid(row=6, column=0, columnspan=2, sticky='ew',
                                           pady=(px(18), px(8)))
        self.algorithm_hint = tk.StringVar()
        ttk.Label(quality, textvariable=self.algorithm_hint, style='Muted.TLabel',
                  wraplength=px(720)).grid(row=7, column=0, columnspan=2, sticky='w',
                                           pady=(0, px(16)))
        ttk.Separator(quality).grid(row=8, column=0, columnspan=2, sticky='ew', pady=(0, px(12)))
        self._check(quality, 9, 'sharpen')
        self._number(self._group(quality, 10, 'sharpness'), 0, '锐化强度', 'sharpness', 0, 2)
        ttk.Label(quality, text='以上为下次启动请求的分辨率，实际运行状态以游戏日志为准。',
                  style='Muted.TLabel', wraplength=px(720)).grid(row=11, column=0, columnspan=2,
                                                                 sticky='w', pady=(px(16), 0))

        self._heading(effects, '游戏特效', '按喜好调整画面风格与细节。')
        self._choice(effects, 2, '模型细节', 'model_lod', LOD_LABELS)
        effect_keys = ('effect_chromatic_aberration', 'effect_dof', 'effect_motion_blur',
                       'effect_ssao', 'effect_game_aa', 'effect_dynamic_shadows', 'effect_ssr')
        for row, key in enumerate(effect_keys, 3):
            self._check(effects, row, key)
        ttk.Separator(effects).grid(row=10, column=0, columnspan=2, sticky='ew', pady=px(12))
        self._check(effects, 11, 'show_fps')
        self._check(effects, 12, 'skip_intro')

        self._heading(advanced, '高级选项', '仅显示当前算法相关的选项；通常保留现有值即可。')
        temporal = self._group(advanced, 2, 'temporal')
        self._check(temporal, 0, 'jitter')
        self._check(temporal, 1, 'object_motion')
        dll = self._group(advanced, 3, 'dll')
        ttk.Label(dll, text='自选 DLSS 文件', style='Section.TLabel').grid(
            row=0, column=0, columnspan=2, sticky='w', pady=(px(18), px(6)))
        ttk.Label(dll, text='选择包含 nvngx_dlss.dll 的文件夹。留空使用内置版本。',
                  style='Muted.TLabel', wraplength=px(720)).grid(row=1, column=0, columnspan=2,
                                                                  sticky='w', pady=(0, px(10)))
        self._vars['dlss_dir'] = tk.StringVar(value=self._initial['dlss_dir'])
        self._vars['dlss_dir'].trace_add('write', lambda *_: self._changed('dlss_dir'))
        ttk.Entry(dll, textvariable=self._vars['dlss_dir']).grid(row=2, column=0, columnspan=2,
                                                                 sticky='ew')
        actions = ttk.Frame(dll)
        actions.grid(row=3, column=0, columnspan=2, sticky='w', pady=(px(10), 0))
        ttk.Button(actions, text='选择文件夹…', command=self._pick_dlss).pack(side='left')
        ttk.Button(actions, text='使用内置版本',
                   command=lambda: self._vars['dlss_dir'].set('')).pack(side='left', padx=px(8))
        self.dll_status = tk.StringVar()
        ttk.Label(dll, textvariable=self.dll_status, style='Muted.TLabel',
                  wraplength=px(720)).grid(row=4, column=0, columnspan=2, sticky='w',
                                           pady=(px(10), 0))
        self._check(self._group(advanced, 4, 'exposure'), 0, 'fsr4_auto_exposure')
        reactive = self._group(advanced, 5, 'reactive')
        self._check(reactive, 0, 'reactive')
        ttk.Label(reactive, text='帮助处理透明物体与粒子；遇到拖影时可尝试开启。',
                  style='Muted.TLabel', wraplength=px(720)).grid(row=1, column=0, columnspan=2,
                                                                  sticky='w', pady=(px(2), px(12)))
        params = self._group(reactive, 2, 'reactive_params')
        self._number(params, 0, '遮罩强度', 'reactive_scale', 0, 16)
        self._number(params, 1, '遮罩阈值', 'reactive_threshold', 0, 1)
        self._number(params, 2, '遮罩上限', 'reactive_max', 0, 1)
        empty = self._group(advanced, 6, 'empty')
        ttk.Label(empty, text='当前关闭超分与时域抗锯齿，无需配置高级参数。',
                  style='Muted.TLabel').grid(row=0, column=0, sticky='w')
        self._ready = True
        self.refresh_summary()

    @staticmethod
    def _heading(parent, title, description):
        ttk.Label(parent, text=title, style='Section.TLabel').grid(
            row=0, column=0, columnspan=2, sticky='w')
        ttk.Label(parent, text=description, style='Muted.TLabel', wraplength=px(720)).grid(
            row=1, column=0, columnspan=2, sticky='w', pady=(px(5), px(18)))

    def _group(self, parent, row, name):
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=0, columnspan=2, sticky='ew')
        frame.columnconfigure(0, minsize=px(150))
        frame.columnconfigure(1, weight=1)
        self._groups[name] = frame
        return frame

    def _changed(self, key):
        if not self._ready:
            return
        raw = self._raw_values()
        if raw.get(key) != self._initial.get(key) or key in self._forced_dirty:
            self.dirty_keys.add(key)
        else:
            self.dirty_keys.discard(key)
        self.refresh_summary()

    def _choice(self, parent, row, title, key, labels, *, selectable=None):
        self._labels[key] = labels
        initial = self._initial.get(key, DEFAULTS[key])
        label = next((label for label, value in labels.items()
                      if str(value) == str(initial)), next(iter(labels)))
        var = tk.StringVar(value=label)
        self._vars[key] = var
        ttk.Label(parent, text=title).grid(row=row, column=0, sticky='w',
                                           padx=(0, px(16)), pady=px(4))
        control = ttk.Combobox(parent, textvariable=var, state='readonly',
                               values=list(selectable if selectable is not None else labels))
        control.grid(row=row, column=1, sticky='ew', pady=px(4))
        var.trace_add('write', lambda *_: self._changed(key))
        return control

    def _check(self, parent, row, key):
        var = tk.BooleanVar(value=self._initial.get(key, DEFAULTS[key]) == '1')
        self._vars[key] = var
        ttk.Checkbutton(parent, text=BOOLEAN_LABELS[key], variable=var).grid(
            row=row, column=0, columnspan=2, sticky='w', pady=px(3),
        )
        var.trace_add('write', lambda *_: self._changed(key))

    def _number(self, parent, row, title, key, minimum, maximum):
        var = tk.StringVar(value=self._initial.get(key, DEFAULTS[key]))
        self._vars[key] = var
        scale_var = tk.DoubleVar(value=float(var.get()))
        self._scales[key] = scale_var
        ttk.Label(parent, text=title).grid(row=row, column=0, sticky='w',
                                           padx=(0, px(16)), pady=px(5))
        controls = ttk.Frame(parent)
        controls.grid(row=row, column=1, sticky='ew', pady=px(5))
        controls.columnconfigure(0, weight=1)
        scale = ttk.Scale(controls, from_=minimum, to=maximum, variable=scale_var)
        scale.grid(row=0, column=0, sticky='ew', padx=(0, px(12)))
        ttk.Spinbox(controls, from_=minimum, to=maximum, increment=0.05,
                    textvariable=var, width=7, format='%.2f').grid(row=0, column=1)

        def from_scale(*_):
            if self._syncing_scale:
                return
            self._syncing_scale = True
            try:
                var.set(f'{scale_var.get():.2f}')
            finally:
                self._syncing_scale = False

        def from_entry(*_):
            if not self._syncing_scale:
                try:
                    number = float(var.get())
                    if math.isfinite(number) and minimum <= number <= maximum:
                        self._syncing_scale = True
                        scale_var.set(number)
                except (ValueError, tk.TclError):
                    pass
                finally:
                    self._syncing_scale = False
            self._changed(key)

        scale_var.trace_add('write', from_scale)
        var.trace_add('write', from_entry)

    def _raw_values(self):
        values = {'output_res': self._output_res}
        for key, variable in self._vars.items():
            value = variable.get()
            if key in self._labels:
                values[key] = str(self._labels[key][value])
            elif isinstance(variable, tk.BooleanVar):
                values[key] = '1' if value else '0'
            else:
                values[key] = str(value)
        return values

    def values(self):
        """Return validated control values without unrelated ini fields."""
        raw = self._raw_values()
        validated = validate_settings({**self._initial, **raw})
        return {key: validated[key] for key in raw}

    def changes(self):
        """Return edits only, so a stale window preserves in-game changes."""
        values = self.values()
        return {key: values[key] for key in self.dirty_keys}

    def mark_saved(self):
        self._initial.update(self.values())
        self._forced_dirty.clear()
        self.dirty_keys.clear()

    def set_profile(self, output_res, preset):
        """Apply an explicit resolution profile selected by the launcher."""
        preset = str(preset)
        candidate = validate_settings({**self._initial, 'output_res': output_res,
                                       'preset': preset})
        self._output_res = candidate['output_res']
        self._vars['output_res'].set(next(label for label, value in self._labels['output_res'].items() if value == candidate['output_res']))
        self._forced_dirty.update(('output_res', 'preset'))
        self.dirty_keys.update(('output_res', 'preset'))
        self._vars['preset'].set(next(label for label, value in PRESET_LABELS.items()
                                     if str(value) == candidate['preset']))
        self.refresh_summary()

    def _pick_dlss(self):
        directory=filedialog.askdirectory(title='选择包含 nvngx_dlss.dll 的目录')
        if directory: self._vars['dlss_dir'].set(directory)

    def refresh_summary(self):
        from pathlib import Path
        raw = self._raw_values()
        method = raw['upscaler']
        visibility = {
            'fsr': method in ('fsr3', 'fsr4', 'fsr411'), 'dlss': method == 'dlss',
            'custom': method == 'dlss' and raw['dlss_mode'] == 'custom',
            'sharpness': raw['sharpen'] == '1', 'temporal': method != 'off',
            'dll': method == 'dlss', 'exposure': method == 'fsr4',
            'reactive': method == 'fsr3', 'reactive_params': raw['reactive'] == '1',
            'empty': method == 'off',
        }
        for name, visible in visibility.items():
            self._groups[name].grid() if visible else self._groups[name].grid_remove()
        if method == 'dlss':
            hints = {'dlaa': 'DLAA 按原生分辨率进行抗锯齿，不降低场景渲染分辨率。',
                     'quality': '画质：以约 67% 的宽高渲染，再重建到输出分辨率。',
                     'balanced': '平衡：以约 58% 的宽高渲染，兼顾画质与帧率。',
                     'performance': '性能：以约 50% 的宽高渲染。尺寸会按渲染器要求对齐。',
                     'custom': '比例按宽高计算，33–100%；100% 为原生抗锯齿。'}
            self.algorithm_hint.set(hints[raw['dlss_mode']])
        else:
            self.algorithm_hint.set({
                'fsr4': 'FSR 4（INT8）的显卡开销较高，可调低档位以提高帧率。',
                'fsr411': '此 Windows 版本暂不支持 FSR 4.1.1，请选择其他算法。',
                'taa': '使用时域抗锯齿，无需选择超分档位。',
                'off': '关闭超分与时域抗锯齿，无需选择画质档位。',
                'fsr3': '降低场景渲染分辨率，再重建到输出分辨率；原生档位不降分辨率。',
            }[method])
        directory = raw['dlss_dir'].strip()
        self.dll_status.set('当前使用内置 DLSS。' if not directory else
            ('已找到 nvngx_dlss.dll；重启游戏后加载。' if (Path(directory) / 'nvngx_dlss.dll').is_file()
             else '此目录中未找到 nvngx_dlss.dll，请重新选择。'))
        try:
            description = render_description(validate_settings({**self._initial, **raw}))
            if method == 'dlss':
                mode = next(label for label, value in self._labels['dlss_mode'].items() if value == raw['dlss_mode'])
                description = mode + '  ·  ' + description
            self.summary.set(description)
        except ValueError as error:
            self.summary.set(str(error))
