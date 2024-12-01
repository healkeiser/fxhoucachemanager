# Internal
from fxhoucachemanager import fxview

if __import__("os").getenv("DEBUG_CODE") == "1":
    __import__("importlib").reload(fxview)


def run():
    import hou

    window = fxview.FXCacheManagerMainWindow(parent=hou.qt.mainWindow())
    window.show()
