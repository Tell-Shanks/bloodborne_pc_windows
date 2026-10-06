# Windows port modifications by yaonikaixin999999, 2026-10-05.
# SPDX-License-Identifier: GPL-2.0-or-later
"""Windows launcher for the native bbport experiment. Requires the user's game dump."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from prepare import sfo
from patches import read_settings,scaled_sizes
from windows_graphics import load_settings,save_settings

PROFILES={
    '1080p':('1920x1080',1),
    '1440p':('2560x1440',1),
    '4k':('3840x2160',2),
    '4k-quality':('3840x2160',1),
    '4k-native':('3840x2160',0),
}
SUPPORTED_TITLES=('CUSA03173','CUSA03023')
LANGUAGES={'auto':None,'zh-cn':11,'zh-tw':10,'en':1}
LANGUAGE_LABELS={'自动（优先中文）':'auto','简体中文':'zh-cn','繁体中文':'zh-tw','English':'en'}
CONTROLLER_LAYOUTS=('ps4','xbox')
CONTROLLER_LABELS={'原版（A=✕ / B=○）':'ps4','Xbox（A确认 / B返回）':'xbox'}
CONTROLLER_HINTS={'ps4':'原版对应：○=B，✕=A，△=Y，□=X',
                  'xbox':'Xbox 对应：○=A，✕=B，△=X，□=Y'}
FPS_LABELS={'30 帧 · 原版':'30','60 帧 · 推荐':'60','90 帧 · 实验':'90',
            '跟随显示器（最高 120 帧）· 实验':'uncap'}
FPS_CHOICES=tuple(FPS_LABELS.values())

def read_preferences():
    preferences={'game_dir':'','resolution':'1080p','language':'auto','fullscreen':False,
                 'controller_layout':'ps4','fps':'60','theme':'auto'}
    # Older launchers only saved launch.json. Recover the last profile on upgrade,
    # then prefer choices saved by the current launcher's window or command line.
    for path in (ROOT/'out/windows-data/launch.json',ROOT/'user/launcher.json'):
        try:
            saved=json.loads(path.read_text(encoding='utf-8'))
        except (OSError,ValueError):
            continue
        if not isinstance(saved,dict): continue
        if isinstance(saved.get('game_dir'),str): preferences['game_dir']=saved['game_dir']
        if isinstance(saved.get('resolution'),str) and saved['resolution'] in PROFILES:
            preferences['resolution']=saved['resolution']
        if isinstance(saved.get('language'),str) and saved['language'] in LANGUAGES:
            preferences['language']=saved['language']
        if isinstance(saved.get('fullscreen'),bool): preferences['fullscreen']=saved['fullscreen']
        if isinstance(saved.get('controller_layout'),str) and saved['controller_layout'] in CONTROLLER_LAYOUTS:
            preferences['controller_layout']=saved['controller_layout']
        if isinstance(saved.get('fps'),str) and saved['fps'] in FPS_CHOICES:
            preferences['fps']=saved['fps']
        if saved.get('theme') in ('auto','light','dark'):
            preferences['theme']=saved['theme']
    return preferences

def save_preferences(preferences):
    path=ROOT/'user/launcher.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(preferences,ensure_ascii=False,indent=2),encoding='utf-8')

def resolve_language(game,selection='auto'):
    if selection not in LANGUAGES:
        raise ValueError(f'不支持的语言选项：{selection}')
    folders={'zh-cn':'zhocn','zh-tw':'zhotw'}
    def available(language):
        directory=Path(game)/'dvdroot_ps4/msg'/folders[language]
        return all((directory/name).is_file() and (directory/name).stat().st_size>0
                   for name in ('menu.msgbnd.dcx','item.msgbnd.dcx'))
    if selection=='auto':
        selection=next((language for language in folders if available(language)),'en')
    elif selection in folders and not available(selection):
        raise ValueError(f'游戏缺少所选中文资源：dvdroot_ps4/msg/{folders[selection]}')
    return selection,LANGUAGES[selection]

def validate_game(game):
    game=Path(game).resolve()
    required=('eboot.bin','sce_sys/param.sfo','sce_module/libc.prx','sce_module/libSceFios2.prx')
    missing=[name for name in required if not (game/name).is_file() or (game/name).stat().st_size==0]
    if missing:
        raise ValueError('游戏文件不完整：'+', '.join(missing))
    if not (game/'dvdroot_ps4').is_dir():
        raise ValueError('缺少 dvdroot_ps4 游戏数据目录。')
    values=sfo((game/'sce_sys/param.sfo').read_bytes())
    if values.get('TITLE_ID') not in SUPPORTED_TITLES:
        raise ValueError(f"当前移植支持 CUSA03173、CUSA03023，当前是 {values.get('TITLE_ID')}。")
    if values.get('APP_VER') not in ('01.09','1.09'):
        raise ValueError(f"此移植需要游戏 1.09，当前是 {values.get('APP_VER')}。")
    return game

def write_profile(path,name):
    output,preset=PROFILES[name]
    return save_settings(path,{'preset':str(preset),'output_res':output,'live_resolution':'0'})

def runtime_environment():
    env=os.environ.copy()
    env.update(PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    candidates=[ROOT/'dist/windows',ROOT.parent/'tools-local/msys64/ucrt64/bin',Path('C:/msys64/ucrt64/bin')]
    env['PATH']=os.pathsep.join(str(p) for p in candidates if p.is_dir())+os.pathsep+env.get('PATH','')
    # The launcher configuration also drives the offline resolution patches.
    for key in ('BB_UPSCALER','BB_UPSCALE_PRESET','BB_RENDER_RES','BB_OUTPUT_RES',
                'BB_DMEM_MB','BB_LIVE_RES','BB_FPS','BB_FPS_LIMIT','BB_VBLANK_HZ','BB_LANGUAGE','BB_FULLSCREEN','BB_PAD_LAYOUT',
                'BB_CONFIG','BB_FSR_SHARPNESS','BB_JITTER','BB_REACTIVE','BB_REACTIVE_SCALE',
                'BB_REACTIVE_THRESHOLD','BB_REACTIVE_MAX','BB_OBJECT_MOTION','BB_FSR4_DIR','BB_FSR4_OPT'):
        env.pop(key,None)
    return env

def renderer_path():
    packaged=ROOT/'dist/windows/bb-probe.exe'
    return packaged if packaged.is_file() else ROOT/'out/windows/bin/bb-probe.exe'

def execute(command,env):
    subprocess.run([str(v) for v in command],cwd=ROOT,env=env,check=True)

def launch(game,resolution=None,prepare_only=False,*,language=None,fullscreen=None,controller_layout=None,fps=None):
    game=validate_game(game)
    preferences=read_preferences()
    language=preferences['language'] if language is None else language
    fullscreen=preferences['fullscreen'] if fullscreen is None else fullscreen
    controller_layout=preferences['controller_layout'] if controller_layout is None else controller_layout
    fps=preferences['fps'] if fps is None else fps
    if fps not in FPS_CHOICES:
        raise ValueError(f'不支持的帧率选项：{fps}')
    if controller_layout not in CONTROLLER_LAYOUTS:
        raise ValueError(f'不支持的手柄按键方案：{controller_layout}')
    resolved_language,language_id=resolve_language(game,language)
    executable=renderer_path()
    if not executable.is_file() and not prepare_only:
        raise ValueError('完整 Windows 渲染器尚未构建，请运行 build_windows.ps1。诊断版本不能用于游戏。')
    data=ROOT/'out/windows-data'
    data.mkdir(parents=True,exist_ok=True)
    config=ROOT/'bbport.ini'
    if resolution: settings=write_profile(config,resolution)
    elif config.is_file(): settings=load_settings(config)
    else: settings=write_profile(config,preferences['resolution'])
    preferences.update(game_dir=str(game),resolution=resolution or preferences['resolution'],
                       language=language,fullscreen=fullscreen,controller_layout=controller_layout,fps=fps)
    save_preferences(preferences)
    env=runtime_environment()
    env.update(BB_LANGUAGE=str(language_id),BB_FULLSCREEN='1' if fullscreen else '0',
               BB_PAD_LAYOUT=controller_layout,BB_CONFIG=str(config),BB_FPS=fps,
               BB_FSR4_DIR=str(ROOT/'fsr4_shaders'),BB_FSR4_OPT='1',
               BB_VBLANK_HZ='0' if fps=='uncap' else '90' if fps=='90' else '60')
    for script in ('prepare.py','link_libc.py','link_modules.py','content_profile.py'):
        command=[sys.executable,ROOT/'scripts'/script,game,'--out',data]
        if script in ('link_libc.py','link_modules.py'): command+=['--target','windows']
        execute(command,env)
    if settings.get('upscaler')=='dlss':
        selected=Path(settings.get('dlss_dir') or ROOT/'dlss').expanduser().resolve()
        if not (selected/'nvngx_dlss.dll').is_file(): raise ValueError(f'DLSS DLL 不存在：{selected / "nvngx_dlss.dll"}')
        env['BB_DLSS_DIR']=str(selected)
        settings['preset']={'dlaa':'0','quality':'1','balanced':'2','performance':'3','custom':('4' if float(settings.get('dlss_scale','67'))<50 else '3' if float(settings.get('dlss_scale','67'))<58 else '1')}[settings.get('dlss_mode','quality')]
        save_settings(config,{'preset':settings['preset']})
    sizes=scaled_sizes(settings)
    patch=[sys.executable,ROOT/'scripts/patches.py','--out',data,'--fps',fps,
           '--settings',config,'--game-dir',game]
    if sizes:
        render,output=sizes
        render_text=f'{render[0]}x{render[1]}'
        output_text=f'{output[0]}x{output[1]}'
        patch+=['--render-res',render_text,'--output-res',output_text]
        env.update(BB_RENDER_RES=render_text,BB_OUTPUT_RES=output_text,BB_DMEM_MB='9152')
    else:
        for key in ('BB_RENDER_RES','BB_OUTPUT_RES','BB_DMEM_MB'): env.pop(key,None)
    execute(patch,env)
    saved=ROOT/'user'
    saved.mkdir(exist_ok=True)
    state={'game_dir':str(game),'resolution':preferences['resolution'],
           'fps':fps,'target_fps':int(fps) if fps!='uncap' else 'display',
           'output_res':settings.get('output_res'),'upscaler':settings.get('upscaler','fsr3'),
           'language':language,'resolved_language':resolved_language,'language_id':language_id,
           'fullscreen':fullscreen,'controller_layout':controller_layout,'gameplay_verified':False}
    (data/'launch.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    if prepare_only: return
    env.update(BB_FRAME_STATS='1',BB_FRAMES_AHEAD='1',BB_LIVE_RES='0')
    args=[executable,data/'boot-linked.bin','--content-profile',data/'content.bin',
          '--patches',data/'patches.bin','--app0',game,'--user',saved,'--timeout','0']
    # Restart requests exit with 75: let the old GPU process fully release its device first.
    while True:
        code=subprocess.call([str(v) for v in args],cwd=ROOT,env=env)
        if code!=75:
            if code: raise subprocess.CalledProcessError(code,args)
            break
        return launch(game,resolution=None,language=language,fullscreen=fullscreen,controller_layout=controller_layout,fps=fps)

def gui(game_dir=None,resolution=None,language=None,fullscreen=None,controller_layout=None,fps=None):
    import tkinter as tk
    from tkinter import filedialog,messagebox,ttk
    from windows_graphics_ui import (GraphicsPanel, configure_style, detect_system_theme,
                                     enable_dpi_awareness, init_scale, px, ui_scale)
    enable_dpi_awareness()
    root=tk.Tk()
    root.title('血源 · Windows 实验版')
    root.withdraw()
    init_scale(root)
    preferences=read_preferences()
    theme=preferences.get('theme','auto')
    if theme not in ('light','dark'): theme=detect_system_theme()
    palette=configure_style(root,theme)
    icon_path=ROOT/'256x256.png'
    if icon_path.is_file():
        icon=tk.PhotoImage(file=str(icon_path))
        root.iconphoto(True,icon)
    outer=ttk.Frame(root,padding=px(20)); outer.pack(fill='both',expand=True)
    header=ttk.Frame(outer); header.pack(fill='x',pady=(0,px(16)))
    hero=tk.Label(header,borderwidth=0,background=palette['bg'])
    hero.pack(side='left')
    def hero_image(name):
        suffix='@2x' if ui_scale()>=1.5 else ''
        path=ROOT/'launcher_assets'/f'hero_{name}{suffix}.png'
        return tk.PhotoImage(file=str(path)) if path.is_file() else None
    titles=ttk.Frame(header); titles.pack(side='left',padx=(px(22),0),anchor='n')
    ttk.Label(titles,text='血源',style='Title.TLabel').pack(anchor='w',pady=(px(8),0))
    ttk.Label(titles,text='BLOODBORNE',style='Logo.TLabel').pack(anchor='w')
    ttk.Label(titles,text='Windows 实验版',style='Muted.TLabel').pack(anchor='w',pady=(px(4),0))
    theme_button=ttk.Button(header,command=lambda: toggle_theme())
    theme_button.pack(side='right',anchor='n',pady=(px(8),0))
    def apply_theme(name):
        nonlocal palette
        palette=configure_style(root,name)
        image=hero_image(name)
        if image is not None: hero.configure(image=image); hero.image=image
        hero.configure(background=palette['bg'])
        theme_button.configure(text='浅色模式' if name=='dark' else '深色模式')
        preferences['theme']=name
    def toggle_theme():
        apply_theme('light' if preferences.get('theme','dark')=='dark' else 'dark')
    apply_theme(theme)
    tabs=ttk.Notebook(outer); tabs.pack(fill='both',expand=True)
    frame=ttk.Frame(tabs,padding=(px(24),px(20))); tabs.add(frame,text='游戏启动')
    initial_graphics=load_settings(ROOT/'bbport.ini')
    graphics=GraphicsPanel(tabs,initial_graphics,notebook=tabs)
    frame.columnconfigure(0,minsize=px(96))
    frame.columnconfigure(1,weight=1)
    ttk.Label(frame,text='游戏与启动',style='Section.TLabel').grid(row=0,column=0,columnspan=2,sticky='w')
    ttk.Label(frame,text='游戏目录需包含 eboot.bin（1.09 已解密数据）。',style='Muted.TLabel').grid(
        row=1,column=0,columnspan=2,sticky='w',pady=(px(5),px(18)))
    game=tk.StringVar(value=str(game_dir) if game_dir else preferences['game_dir'])
    row=ttk.Frame(frame); row.grid(row=2,column=0,columnspan=2,sticky='ew')
    ttk.Entry(row,textvariable=game).pack(side='left',fill='x',expand=True)
    def pick():
        selected=filedialog.askdirectory(title='选择含 eboot.bin 的血源 1.09 游戏文件夹')
        if selected: game.set(selected)
    ttk.Button(row,text='选择文件夹',command=pick).pack(side='right',padx=(px(8),0))
    profile=resolution or preferences['resolution']
    output=PROFILES[profile][0] if resolution or not (ROOT/'bbport.ini').exists() else initial_graphics['output_res']
    if resolution or not (ROOT/'bbport.ini').exists():
        output,preset=PROFILES[profile]; graphics.set_profile(output,str(preset))
    ttk.Label(frame,text='分辨率与 DLSS / FSR 档位在「画面质量」页设置。',style='Muted.TLabel').grid(
        row=3,column=0,columnspan=2,sticky='w',pady=(px(10),px(22)))
    ttk.Label(frame,text='游戏帧率').grid(row=4,column=0,sticky='w',pady=px(6))
    selected_fps=preferences['fps'] if fps is None else fps
    chosen_fps=tk.StringVar(value=next(label for label,value in FPS_LABELS.items() if value==selected_fps))
    ttk.Combobox(frame,textvariable=chosen_fps,values=list(FPS_LABELS),state='readonly',
                 width=32).grid(row=4,column=1,sticky='w',pady=px(6))
    selection=preferences['language'] if language is None else language
    chosen_language=tk.StringVar(value=next(label for label,value in LANGUAGE_LABELS.items() if value==selection))
    ttk.Label(frame,text='游戏语言').grid(row=5,column=0,sticky='w',pady=px(6))
    language_row=ttk.Frame(frame); language_row.grid(row=5,column=1,sticky='w',pady=px(6))
    ttk.Combobox(language_row,textvariable=chosen_language,values=list(LANGUAGE_LABELS),
                 state='readonly',width=20).pack(side='left')
    chosen_fullscreen=tk.BooleanVar(value=preferences['fullscreen'] if fullscreen is None else fullscreen)
    ttk.Checkbutton(language_row,text='全屏运行',variable=chosen_fullscreen).pack(side='left',padx=(px(18),0))
    layout=preferences['controller_layout'] if controller_layout is None else controller_layout
    chosen_controller=tk.StringVar(value=next(label for label,value in CONTROLLER_LABELS.items() if value==layout))
    ttk.Label(frame,text='手柄按键').grid(row=6,column=0,sticky='w',pady=px(6))
    ttk.Combobox(frame,textvariable=chosen_controller,values=list(CONTROLLER_LABELS),
                 state='readonly',width=32).grid(row=6,column=1,sticky='w',pady=px(6))
    controller_hint=tk.StringVar(value=CONTROLLER_HINTS[layout])
    def update_controller_hint(*_):
        controller_hint.set(CONTROLLER_HINTS[CONTROLLER_LABELS[chosen_controller.get()]])
    chosen_controller.trace_add('write',update_controller_hint)
    ttk.Label(frame,textvariable=controller_hint,style='Muted.TLabel').grid(
        row=7,column=1,sticky='w',pady=(0,px(14)))
    ttk.Separator(frame).grid(row=8,column=0,columnspan=2,sticky='ew',pady=px(8))
    ttk.Label(frame,text='30 帧使用原版时序；90 帧与高刷新率为实验选项。',style='Muted.TLabel').grid(
        row=9,column=0,columnspan=2,sticky='w',pady=(px(8),0))
    status=tk.StringVar(value='启动游戏时会保存设置；画面修改在下次启动生效。')
    ttk.Label(outer,textvariable=status,style='Muted.TLabel',wraplength=px(860)).pack(
        anchor='w',pady=(px(12),0))
    process=None
    log_handle=None
    def save_choices():
        output=graphics.values()['output_res']
        profile={'1280x720':'1080p','1920x1080':'1080p','2560x1440':'1440p','3840x2160':'4k'}[output]
        preferences.update(game_dir=game.get(),resolution=profile,
                           language=LANGUAGE_LABELS[chosen_language.get()],fullscreen=chosen_fullscreen.get(),
                           controller_layout=CONTROLLER_LABELS[chosen_controller.get()],fps=FPS_LABELS[chosen_fps.get()])
        graphics.values() # validate every field before saving any changes
        changes=graphics.changes()
        if changes: save_settings(ROOT/'bbport.ini',changes)
        save_preferences(preferences)
        graphics.mark_saved()
    def save_only():
        try:
            save_choices(); status.set('设置已保存，下次启动游戏时生效。')
        except (ValueError,OSError) as error: messagebox.showerror('无法保存设置',str(error))
    def close():
        try: save_choices()
        except (ValueError,OSError) as error:
            messagebox.showerror('无法保存设置',str(error))
            return
        root.destroy()
    root.protocol('WM_DELETE_WINDOW',close)
    def monitor():
        nonlocal process,log_handle
        code=process.poll()
        if code is None:
            root.after(500,monitor)
            return
        log_handle.close(); log_handle=None; process=None
        start_button.configure(state='normal')
        status.set('游戏已退出。' if code==0 else '启动失败，日志已保存到 out/windows-data/last-run.log。')
        if code:
            messagebox.showerror('运行失败',f'退出码：{code}\n请查看 {ROOT / "out/windows-data/last-run.log"}')
    def start():
        nonlocal process,log_handle
        try:
            validate_game(game.get())
            resolve_language(game.get(),LANGUAGE_LABELS[chosen_language.get()])
            if not renderer_path().is_file(): raise ValueError('缺少完整 Windows 程序，请先运行 build_windows.ps1。')
            save_choices()
            log_path=ROOT/'out/windows-data/last-run.log'
            log_path.parent.mkdir(parents=True,exist_ok=True)
            log_handle=log_path.open('w',encoding='utf-8')
            child_env=runtime_environment(); child_env.update(PYTHONIOENCODING='utf-8',PYTHONUNBUFFERED='1')
            process=subprocess.Popen([sys.executable,str(ROOT/'run_windows.py'),'--game',game.get(),
                              '--language',LANGUAGE_LABELS[chosen_language.get()],
                              '--fps',FPS_LABELS[chosen_fps.get()],
                              '--controller-layout',CONTROLLER_LABELS[chosen_controller.get()],
                              '--fullscreen' if chosen_fullscreen.get() else '--windowed'],cwd=ROOT,env=child_env,
                              stdout=log_handle,stderr=subprocess.STDOUT,
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            start_button.configure(state='disabled'); status.set('正在准备或运行；日志实时保存在 out/windows-data/last-run.log。')
            root.after(500,monitor)
        except (ValueError,OSError) as error:
            if log_handle: log_handle.close(); log_handle=None
            messagebox.showerror('无法启动',str(error))
    buttons=ttk.Frame(outer); buttons.pack(fill='x',pady=(px(12),0))
    ttk.Button(buttons,text='保存设置',command=save_only).pack(side='left')
    start_button=ttk.Button(buttons,text='保存并启动游戏',command=start,style='Primary.TButton')
    start_button.pack(side='right')
    # Size the window to the tallest tab so no control is clipped, then show it.
    root.update_idletasks()
    need=root.winfo_reqheight()
    for tab_id in tabs.tabs():
        tabs.select(tab_id)
        root.update_idletasks()
        need=max(need,root.winfo_reqheight())
    tabs.select(0)
    root.geometry(f'{px(940)}x{max(px(760),need)}')
    root.minsize(px(880),px(700))
    root.deiconify()
    root.mainloop()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game',type=Path)
    parser.add_argument('--resolution',choices=PROFILES)
    parser.add_argument('--fps',choices=FPS_CHOICES,help='30、60、90 帧或跟随显示器（最高 120 帧）；省略时沿用已保存的选择。')
    parser.add_argument('--language',choices=LANGUAGES,help='游戏语言；自动优先使用已有简体、繁体中文资源。')
    parser.add_argument('--controller-layout',choices=CONTROLLER_LAYOUTS,
                        help='手柄按键方案：xbox 为 ○=A、✕=B、△=X、□=Y；省略时沿用已保存的设置。')
    display=parser.add_mutually_exclusive_group()
    display.add_argument('--fullscreen',dest='fullscreen',action='store_true',default=None,
                         help='全屏运行。省略时沿用已保存的设置。')
    display.add_argument('--windowed','--no-fullscreen',dest='fullscreen',action='store_false',
                         help='窗口运行。省略时沿用已保存的设置。')
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--gui',action='store_true')
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    if args.gui: gui(args.game,args.resolution,args.language,args.fullscreen,args.controller_layout,args.fps); return 0
    if args.check:
        print(json.dumps({'windows':os.name=='nt','renderer_built':renderer_path().is_file(),
                          'game_dir':str(args.game) if args.game else None,'target_fps':60,
                          'profiles':list(PROFILES),'languages':list(LANGUAGES),
                          'controller_layouts':list(CONTROLLER_LAYOUTS),'frame_rates':list(FPS_CHOICES),
                          'gameplay_verified':False},ensure_ascii=False,indent=2))
        if args.game: validate_game(args.game)
        return 0
    if not args.game: parser.error('请指定 --game 游戏目录，或使用 --gui。')
    launch(args.game,args.resolution,args.prepare_only,language=args.language,fullscreen=args.fullscreen,
           controller_layout=args.controller_layout,fps=args.fps)
    return 0

if __name__=='__main__':
    try: sys.exit(main())
    except (ValueError,OSError,subprocess.CalledProcessError) as error:
        print(f'无法启动：{error}',file=sys.stderr)
        sys.exit(1)
