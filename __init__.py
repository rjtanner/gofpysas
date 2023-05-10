# __init__.py for pysas
#
#

from . import sastask
from . import parser
from . import param
from . import error
from . import runtask
from .version import *
from .startsas import startsas
from .odfcontrol import odfcontrol

__version__ = f'pysas - (pysas-{VERSION}) [{SAS_RELEASE}-{SAS_AKA}]'
