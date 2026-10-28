# SPDX-FileCopyrightText: 2024-2026 Andrew Gunnerson
# SPDX-License-Identifier: GPL-3.0-only

from abc import ABC, abstractmethod
import argparse
from collections.abc import Iterable
import dataclasses
import functools
import logging
from pathlib import Path, PurePosixPath, PurePath
import shutil
import subprocess
import tempfile
import zipfile
import os
import gnupg

from cryptography.exceptions import InvalidSignature
from lib.filesystem import CpioFs, ExtFs
from lib.mtgapp_verifier import SignedFile


logger = logging.getLogger(__name__)


# https://codeberg.org/chenxiaolong/chenxiaolong
# https://gitlab.com/chenxiaolong/chenxiaolong
# https://github.com/chenxiaolong/chenxiaolong
SSH_PUBLIC_KEY_CHENXIAOLONG = \
    'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDOe6/tBnO7xZhAWXRj3ApUYgn+XZ0wnQiXM8B7tPgv4'


class MissingArgs(Exception):
    pass

def verify_ssh_sig(zip: Path, sig: Path, public_key: str):
    logger.info(f'Verifying SSH signature: {zip}')

    with tempfile.NamedTemporaryFile(delete_on_close=False) as f_trusted:
        f_trusted.write(b'trusted ')
        f_trusted.write(public_key.encode('UTF-8'))
        f_trusted.close()

        with open(zip, 'rb') as f_zip:
            subprocess.check_call([
                'ssh-keygen',
                '-Y', 'verify',
                '-f', f_trusted.name,
                '-I', 'trusted',
                '-n', 'file',
                '-s', sig,
            ], stdin=f_zip)

def verify_mtgapps_sig(zip: Path, cert: Path):
    logger.info(f'Verifying MindTheGapps signature: {zip}')
    # Disable SHA1 support
    os.environ["OPENSSL_ENABLE_SHA1_SIGNATURES"] = "0"

    signed_file = SignedFile(zip)
    try:
        signed_file.verify(cert)
        logger.info("MindTheGapps signature verified successfully")
    except (InvalidSignature,
            ValueError,
            TypeError,
            OSError) as e:
        logger.error(f"Failed to verify MindTheGapps signature: {e}")

def is_pgp_signature_valid(zip: Path, asc: Path, public_key_fingerprint: str) -> bool:
    logger.info(f'Verifying PGP signature: {zip}')

    gpg = gnupg.GPG()
    with open(asc, "rb") as asc:
        verified = gpg.verify_file(asc,zip)
    if verified.status == "signature valid" and verified.pubkey_fingerprint == public_key_fingerprint:
        return True
    else:
        return False

def add_signed_module_args(parser: argparse.ArgumentParser, name: str):
    parser.add_argument(
        f'--module-{name}',
        type=Path,
        help=f'{name} module zip',
    )
    parser.add_argument(
        f'--module-{name}-sig',
        type=Path,
        help=f'{name} module zip signature',
    )


def get_signed_module_args(args: argparse.Namespace, name: str, public_key: str) -> Path:
    zip: Path | None = getattr(args, f'module_{name}')
    if zip is None:
        raise MissingArgs()

    sig: Path | None = getattr(args, f'module_{name}_sig')
    if sig is None:
        sig = Path(f'{zip}.sig')

    verify_ssh_sig(zip, sig, public_key)

    return zip

def add_pgp_signed_module_args(parser: argparse.ArgumentParser, name: str):
    parser.add_argument(
        f'--module-{name}',
        type=Path,
        help=f'{name} module zip',
    )
    parser.add_argument(
        f'--module-{name}-asc',
        type=Path,
        help=f'{name} module PGP signature',
    )

def get_pgp_signed_module_args(args: argparse.Namespace, name: str, public_key_fingerprint: str) -> Path:
    zip: Path | None = getattr(args, f'module_{name}')
    if zip is None:
        raise MissingArgs()

    asc: Path | None = getattr(args, f'module_{name}_asc')
    if asc is None:
        asc = Path(f'{zip}.asc')

    if not is_pgp_signature_valid(zip, asc, public_key_fingerprint):
        logger.error(f'Failed to verify PGP signature for {zip}')
        raise Exception
    else:
        return zip

def add_mtgapps_signed_module_args(parser: argparse.ArgumentParser, name: str):
    parser.add_argument(
        f'--module-{name}',
        type=Path,
        help=f'{name} module zip',
    )
    parser.add_argument(
        f'--module-{name}-cert',
        type=Path,
        help=f'{name} MindTheGapps OTA cert',
    )

def get_mtgapps_signed_module_args(args: argparse.Namespace, name: str) -> Path:
    zip: Path | None = getattr(args, f'module_{name}')
    if zip is None:
        raise MissingArgs()

    cert: Path | None = getattr(args, f'module_{name}_cert')
    if cert is None:
        cert = PurePath.parent(zip) / 'release.x509.pem'


    verify_mtgapps_sig(zip, cert)

    return zip

def add_unsigned_module_args(parser: argparse.ArgumentParser, name: str):
    parser.add_argument(
        f'--module-{name}',
        type=Path,
        help=f'{name} module zip',
    )

def get_unsigned_module_args(args: argparse.Namespace, name: str) -> Path:
    zip: Path | None = getattr(args, f'module_{name}')
    if zip is None:
        raise MissingArgs()

    return zip

def zip_extract(
    zip: zipfile.ZipFile,
    name: str,
    fs: ExtFs,
    mode: int = 0o644,
    parent_mode: int = 0o755,
    output: str | None = None,
):
    path = PurePosixPath(output or name)

    fs.mkdir(path.parent, mode=parent_mode, parents=True, exist_ok=True)
    with fs.open(path, 'wb', mode=mode) as f_out:
        with zip.open(name, 'r') as f_in:
            shutil.copyfileobj(f_in, f_out)

def zip_append_text(
    zip: zipfile.ZipFile,
    name: str,
    fs: ExtFs,
    mode: int = 0o644,
    parent_mode: int = 0o755,
    output: str | None = None,
):
    path = PurePosixPath(output or name)

    fs.mkdir(path.parent, mode=parent_mode, parents=True, exist_ok=True)
    with fs.open(path, 'r+b', mode=mode) as f_out:
        with zip.open(name, 'r') as f_in:
            original_text = f_out.read()
            modified_text = original_text + f_in.read()
            f_out.write(modified_text)

@dataclasses.dataclass
class ModuleRequirements:
    boot_images: set[str]
    ext_images: set[str]
    selinux_patching: bool


class Module(ABC):
    @classmethod
    @abstractmethod
    def add_args(cls, parser: argparse.ArgumentParser):
        ...

    @abstractmethod
    def __init__(self, args: argparse.Namespace):
        ...

    @abstractmethod
    def requirements(self) -> ModuleRequirements:
        ...

    @abstractmethod
    def inject(
        self,
        boot_fs: dict[str, CpioFs],
        ext_fs: dict[str, ExtFs],
        sepolicies: Iterable[Path],
    ) -> None:
        ...


@functools.cache
def all_modules() -> list[type[Module]]:
    from lib.modules.alterinstaller import AlterInstallerModule
    from lib.modules.bcr import BCRModule
    from lib.modules.custota import CustotaModule
    from lib.modules.msd import MSDModule
    from lib.modules.oemunlockonboot import OEMUnlockOnBootModule
    from lib.modules.mtgapps import MTGappsModule
    from lib.modules.fdroid import FdroidPrivilegedExtension
    from lib.modules.pixelregionalrestrictiondisabler import PixelRegionalRestrictionDisabler

    return [
        AlterInstallerModule,
        BCRModule,
        CustotaModule,
        MSDModule,
        OEMUnlockOnBootModule,
        MTGappsModule,
        FdroidPrivilegedExtension,
        PixelRegionalRestrictionDisabler,
    ]
