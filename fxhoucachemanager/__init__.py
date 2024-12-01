# Internal
from fxhoucachemanager import (
    fxenvironment,
    fxmodel,
    fxview,
    fxsettings,
    fxwidgets,
)


# Create user data
fxenvironment.create_user_data()

# Reload modules if in debug mode
if __import__("os").getenv("DEBUG_CODE") == "1":
    from importlib import reload

    # Reload modules
    reload(fxenvironment)
    reload(fxmodel)
    reload(fxview)
    reload(fxsettings)
    reload(fxwidgets)
