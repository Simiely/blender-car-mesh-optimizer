from . import analyze
from . import classify
from . import detect_features
from . import decimate
from . import export


def register():
    analyze.register()
    classify.register()
    detect_features.register()
    decimate.register()
    export.register()


def unregister():
    export.unregister()
    decimate.unregister()
    detect_features.unregister()
    classify.unregister()
    analyze.unregister()