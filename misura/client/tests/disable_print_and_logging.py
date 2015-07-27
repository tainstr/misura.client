import logging
import sys
import os

# logging.disable(logging.CRITICAL)


def disable_print():
    sys.stdout = open(os.devnull, 'w')

# disable_print()
