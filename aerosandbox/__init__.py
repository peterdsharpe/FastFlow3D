from .common import *
from .atmosphere import *
from .aerodynamics import *
from .geometry import *
import aerosandbox.numpy as numpy
from .modeling import *
from .optimization import *
from .performance import *
from .propulsion import *
from .structures import *

__version__ = "3.0.10"

import webbrowser

def docs():
    """
    Opens the AeroSandbox documentation.
    """
    webbrowser.open_new(
        "https://github.com/peterdsharpe/AeroSandbox"
    ) # TODO: make this redirect to a hosted ReadTheDocs, or similar.