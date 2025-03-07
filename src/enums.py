from enum import Enum


class Modes(Enum):
    """Different modes for determining the theme that should be used"""

    MANUAL = 'manual'
    SCHEDULED = 'manual time'
    FOLLOW_SUN = 'sunset to sunrise'


class Desktop(Enum):
    KDE = 'kde'
    GNOME = 'gnome'
    CINNAMON = 'cinnamon'
    UNKNOWN = 'unknown'
