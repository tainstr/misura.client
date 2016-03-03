""" """
# TODO: migrate to new dataimport plugin mechanism
try:
    from convert import Converter
    from dialog import TestDialog
except:
    Converter = False
    TestDialog = False


