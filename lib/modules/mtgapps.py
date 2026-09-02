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
        modules.add_mtgapps_signed_module_args(parser, cls.NAME)

    def __init__(self, args: argparse.Namespace) -> None:
        self.zip: Path = modules.get_mtgapps_signed_module_args(
            args,
            self.NAME
        )

    @override
    def requirements(self) -> ModuleRequirements:
        return ModuleRequirements(
            boot_images=set(),
            ext_images={'system'},  
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

        system_fs = ext_fs['system']

        # Copy files. Built for Android 16 version of Mind The Gapps
        with zipfile.ZipFile(self.zip, 'r') as z:
            for path in z.namelist():
                if zipfile.Path(z, at=path).is_dir():
                    continue
                if path.startswith(('system/product/', 'system/system_ext/')):
                    f = path.removeprefix('system/product/')
                    f = f.removeprefix('system/system_ext/')
                    if any(s in path for s in (
                                        # 'GoogleTTS',
                                        # 'MarkupGoogle',
                                        # 'SpeechServicesByGoogle',
                                        # 'talkback',
                                        # 'GoogleRestore',
                                        # 'Velvet',
                                        # 'VelvetTitan',
                                        # 'Wellbeing',
                                        # 'SetupWizard',
                                        # 'AndroidAutoStub',
                                        # 'GoogleContactsSyncAdapter',
                                        # 'GoogleCalendarSyncAdapter',
                                        # 'PrebuiltExchange3Google',
                                        # 'GoogleFeedback',
                    )):
                        logger.info(f'... skipping {f}')
                        continue

                    # Extract files into system.img
                    modules.zip_extract(z, path, system_fs, output=f'system/{f}')
                    modules.zip_extract(z, path, system_fs, output=f'system/{f}')
                elif path.startswith('system/'):
                     modules.zip_extract(z, path, system_fs, output=path)
