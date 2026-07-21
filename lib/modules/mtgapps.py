import argparse
from collections.abc import Iterable
from pathlib import Path
import logging
from typing import override
import zipfile

from lib import modules
from lib.filesystem import CpioFs, ExtFs
from lib.modules import Module, ModuleRequirements

logger = logging.getLogger(__name__)

class  MTGappsModule(Module):
    NAME: str = 'mtgapps'

    @classmethod
    @override
    def add_args(cls, parser: argparse.ArgumentParser):
        modules.add_unsigned_module_args(parser, cls.NAME)

    def __init__(self, args: argparse.Namespace) -> None:
        self.zip: Path = modules.get_unsigned_module_args(
            args,
            self.NAME
        )

    @override
    def requirements(self) -> ModuleRequirements:
        return ModuleRequirements(
            boot_images=set(),
            ext_images={'system','product','system_ext'},
            selinux_patching=False,
        )
        
    @override
    def inject(
        self,
        boot_fs: dict[str, CpioFs],
        ext_fs: dict[str, ExtFs],
        sepolicies: Iterable[Path],
    ) -> None:
        logger.info(f'Injecting Mind The Gapps: {self.zip}')

        # Copy files. Built for Android 16 version of Mind The Gapps
        with zipfile.ZipFile(self.zip, 'r') as z:
            for path in z.namelist():
                if zipfile.Path(z, at=path).is_dir():
                    continue
                if path.startswith(('system/product', 'system/system_ext')):
                    f = path.replace('system/product/', '', 1)
                    f = f.replace('system/system_ext/', '', 1)
                    if any(s in path for s in (
                                        # 'GoogleTTS',
                                        # 'MarkupGoogle',
                                        'SpeechServicesByGoogle',
                                        'talkback',
                                        # 'GoogleRestore',
                                        'Velvet',
                                        'VelvetTitan',
                                        'Wellbeing',
                                        'SetupWizard',
                                        'AndroidAutoStub',
                                        'GoogleContactsSyncAdapter',
                                        # 'GoogleCalendarSyncAdapter',
                                        'PrebuiltExchange3Google',
                                        'GoogleFeedback',
                    )):
                        logger.info(f'... skipping {f}')
                        continue

                    # Extract file contents.
                    if path.startswith('system/system_ext'):
                        system_fs = ext_fs['system_ext']
                        modules.zip_extract(z, path, system_fs, output=path)
                    elif path.startswith('system/product'):
                        system_fs = ext_fs['product']
                        modules.zip_extract(z, path, system_fs, output=path)
                    elif path.startswith('system'):
                        system_fs = ext_fs['system']
                        modules.zip_extract(z, path, system_fs, output=path)