import json
import logging
import subprocess
import pwd
import os

from PySide6.QtCore import QLocale

from src.enums import Desktop
from src.plugins._plugin import PluginDesktopDependent, PluginCommandline

logger = logging.getLogger(__name__)


def test_gnome_availability(command) -> bool:
    # Runs the first entry in the command list with --help
    try:
        # if not available, you might want to run https://gist.github.com/atiensivu/fcc3183e9a6fd74ec1a283e3b9ad05f0
        # or you have to install that extension
        process = subprocess.run(
            [command[0], 'get', command[2], command[3]],
            stdout=subprocess.DEVNULL
        )
        return process.stdout == 0
    except FileNotFoundError:
        # if no such command is available, the plugin is not available
        return False


class System(PluginDesktopDependent):
    def __init__(self, desktop: Desktop):
        match desktop:
            case Desktop.KDE:
                super().__init__(_Kde())
            case Desktop.GNOME:
                super().__init__(_Gnome())
            case Desktop.CINNAMON:
                super().__init__(_Cinnamon())
            case _:
                super().__init__(None)


class _Cinnamon(PluginCommandline):
    name = 'System'

    def __init__(self):
        super().__init__(['gsettings', 'set', 'org.cinnamon.theme', 'name', '{theme}'])

    @property
    def available(self) -> bool:
        return test_gnome_availability(self.command)


class _Gnome(PluginCommandline):
    name = 'System'

    # TODO allow using the default themes, not only user themes

    def __init__(self):
        super().__init__(['gsettings', 'set', 'org.gnome.shell.extensions.user-theme', 'name', '{theme}'])

    @property
    def available(self) -> bool:
        return test_gnome_availability(self.command)


def get_readable_kde_theme_name(file) -> str:
    """Searches for the long_name in the file and maps it to the found short name"""

    for line in file:
        if 'Name=' in line:
            name: str = ''
            write: bool = False
            for letter in line:
                if letter == '\n':
                    write = False
                if write:
                    name += letter
                if letter == '=':
                    write = True
            return name


def get_name_key(meta):
    locale = filter(
        lambda name: name in meta['KPlugin'],
        [f'Name[{QLocale().name()}]',
         f'Name[{QLocale().language()}]',
         'Name']
    )
    return next(locale)


class _Kde(PluginCommandline):
    name = 'System'
    translations = {}

    def __init__(self):
        super().__init__(['lookandfeeltool', '-a', '{theme}'])
        self.theme_light = 'org.kde.breeze.desktop'
        self.theme_dark = 'org.kde.breezedark.desktop'

    def set_theme(self, theme: str) -> None:
        # TODO remove this once https://bugs.kde.org/show_bug.cgi?id=446074 is fixed
        super().set_theme(theme)
        super().set_theme(theme)

    @property
    def available_themes(self) -> dict:
        if self.translations != {}:
            return self.translations

        # aliases for path to use later on
        user = pwd.getpwuid(os.getuid())[0]
        path = "/home/" + user + "/.local/share/plasma/look-and-feel/"

        # asks the system what themes are available
        # noinspection SpellCheckingInspection
        long_names = subprocess.check_output(["lookandfeeltool", "-l"], universal_newlines=True)
        long_names = long_names.splitlines()
        long_names.sort()

        # get the actual name
        for long_name in long_names:
            # trying to get the Desktop file
            try:
                # json in newer versions
                with open(f'/usr/share/plasma/look-and-feel/{long_name}/metadata.json', 'r') as file:
                    meta = json.load(file)
                    key = get_name_key(meta)
                    self.translations[long_name] = meta['KPlugin'][key]
            except OSError:
                try:
                    # load the name from the metadata.desktop file
                    with open(f'/usr/share/plasma/look-and-feel/{long_name}/metadata.desktop', 'r') as file:
                        self.translations[long_name] = get_readable_kde_theme_name(file)
                except OSError:
                    # check the next path if the themes exist there
                    try:
                        # load the name from the metadata.desktop file
                        with open(f'{path}{long_name}/metadata.desktop', 'r') as file:
                            # search for the name
                            self.translations[long_name] = get_readable_kde_theme_name(file)
                    except OSError:
                        # if no file exist lets just use the long name
                        self.translations[long_name] = long_name

        return self.translations
