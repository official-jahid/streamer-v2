import os
import sys


class PathResolver:
    @staticmethod
    def app_root():
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.abspath(os.path.dirname(__file__))

    @staticmethod
    def data_dir():
        d = os.path.join(PathResolver.app_root(), 'data')
        os.makedirs(d, exist_ok=True)
        return d

    @staticmethod
    def tmp_dir():
        d = os.path.join(PathResolver.data_dir(), 'tmp')
        os.makedirs(d, exist_ok=True)
        return d

    @staticmethod
    def resource(relative_path):
        if getattr(sys, 'frozen', False):
            base = sys._MEIPASS
        else:
            base = PathResolver.app_root()
        return os.path.join(base, relative_path)

    @staticmethod
    def override_temp():
        tmp = PathResolver.tmp_dir()
        os.environ['TMP'] = tmp
        os.environ['TEMP'] = tmp
        os.environ['TMPDIR'] = tmp
        return tmp