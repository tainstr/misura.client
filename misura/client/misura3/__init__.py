""" """
# TODO: migrate to new dataimport plugin mechanism
from traceback import print_exc
try:
    from convert import Converter
    from dialog import TestDialog
except:
    Converter = False
    TestDialog = False
    print_exc()


