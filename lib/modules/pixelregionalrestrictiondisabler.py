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

class  PixelRegionalRestrictionDisabler(Module):
    NAME: str = 'pixelregionalrestrictiondisabler'

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
        logger.info(f'Injecting Pixel-Regional-Restrictions-Disabler: {self.zip}')

        system_fs = ext_fs['system']

        with zipfile.ZipFile(self.zip, 'r') as z:
            # Extract files into system.img
            modules.zip_extract(z, 'regionalrestrictiondisabler.sh', system_fs, output='system/bin/regionalrestrictiondisabler.sh')
            modules.zip_append_text(z, 'system.prop', system_fs, output='system/build.prop')
            modules.zip_extract(z, 'regionalrestrictiondisabler.rc', system_fs, output='system/etc/init/regionalrestrictiondisabler.rc')
        
