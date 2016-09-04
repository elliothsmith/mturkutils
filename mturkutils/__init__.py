import os
from .base import *

__version__ = '0.1.0'

MTURKLIB = os.path.abspath(os.path.join(__path__[0], os.pardir, 'lib')) + '/'
JSCRIPTS = [MTURKLIB + 'dltk.js',
            MTURKLIB + 'dltkexpr.js',
            MTURKLIB + 'dltkrsvp.js']