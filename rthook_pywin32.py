import sys
import os


def _add_win32_path():
    base = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    win32_dir = os.path.join(base, 'win32')
    if os.path.isdir(win32_dir) and win32_dir not in sys.path:
        sys.path.insert(0, win32_dir)
    sys32_dir = os.path.join(base, 'pywin32_system32')
    if os.path.isdir(sys32_dir):
        os.environ.setdefault('PATH', '')
        os.environ['PATH'] = sys32_dir + os.pathsep + os.environ['PATH']


_add_win32_path()
