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

class FdroidPrivilegedExtension(Module):
    NAME: str = 'fdroid'

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
        # FIXME add PGP signature verification
        #verify_ssh_sig(module_zip, module_sig, SSH_PUBLIC_KEY_CHENXIAOLONG)

        logger.info(f'Injecting FDroid: {self.zip}')
        logger.info(f'This is not necessary for background updates on android > 13')
        
        system_fs = ext_fs['system']
        with zipfile.ZipFile(self.zip, 'r') as z:
            etc = 'system/etc/permissions/permissions_org.fdroid.fdroid.privileged.xml'
            apk = 'system/app/F-Droid/F-Droid.apk'
            priv = 'system/priv-app/F-DroidPrivilegedExtension/F-DroidPrivilegedExtension.apk'

            # Add to filesystem entries.
            # add_file_entry(entries, contexts, f'/{etc}', 0o644)
            # add_file_entry(entries, contexts, f'/{apk}', 0o644)
            # add_file_entry(entries, contexts, f'/{priv}', 0o644)

            # Extract file contents.
            tree_etc = system_fs.tree / etc
            tree_apk = system_fs.tree / apk
            tree_priv = system_fs.tree / priv
            tree_etc.parent.mkdir(parents=True, exist_ok=True)
            tree_apk.parent.mkdir(parents=True, exist_ok=True)
            tree_priv.parent.mkdir(parents=True, exist_ok=True)
            modules.zip_extract(
                z,
                'permissions_org.fdroid.fdroid.privileged.xml',
                system_fs,
                output=etc
            )
            modules.zip_extract(
                z,
                'F-Droid.apk',
                system_fs,
                output=apk
            )
            modules.zip_extract(
                z,
                'F-DroidPrivilegedExtension.apk',
                system_fs,
                output=priv
           )

