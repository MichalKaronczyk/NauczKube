# PyInstaller — wersja binarna wymagana przez regulamin konkursu.
#
# Budowanie (po `npm run build` we frontendzie):
#   cd backend && pyinstaller naucz-kube.spec --noconfirm
# Wynik: dist/naucz-kube(.exe) — uruchamia serwer i otwiera przeglądarkę
# pod http://127.0.0.1:8000

from PyInstaller.utils.hooks import collect_submodules

hidden = [
    *collect_submodules('uvicorn'),
    *collect_submodules('sympy'),
    'app.main',
    'anyio._backends._asyncio',
    'sqlalchemy.dialects.sqlite',
    'argon2',
]

datas = [
    ('catalog', 'catalog'),
    ('app/ai/prompts', 'app/ai/prompts'),
    ('static', 'static'),
]

a = Analysis(
    ['run_app.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=['matplotlib', 'tkinter', 'IPython', 'pytest', 'playwright'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='naucz-kube',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
