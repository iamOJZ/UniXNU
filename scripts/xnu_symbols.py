"""Symbol names of the XNU kernel of a build tree, for the archives that must not collide with it."""
import subprocess
from pathlib import Path

OBJ = 'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837'


def defined_names(paths, global_only):
    """Defined symbol names of Mach-O files and archives."""
    names = set()
    paths = [str(path) for path in paths]
    for start in range(0, len(paths), 200):
        batch = paths[start:start + 200]
        flags = [*(['-g'] if global_only else []), '-U', '-j']
        try:
            output = subprocess.check_output(['xcrun', 'nm', *flags, *batch], text=True,
                                             stderr=subprocess.DEVNULL)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # On Linux the xcrun shim falls back to the system nm when the toolchain
            # directories in $XNU_TOOLCHAIN_BIN are not visible to this process, and GNU
            # nm cannot read Mach-O objects. llvm-nm understands them and takes the same
            # -g/-U/-j flags.
            output = subprocess.check_output(['llvm-nm', *flags, *batch], text=True)
        names |= {line.strip() for line in output.splitlines() if line.startswith('_')}
    return names


def kernel_names(root, global_only=True):
    """Names of the XNU kernel alone: the recorded checkpoint kernel if present, else the objects of this tree's XNU link
    (link.filelist, written by every kernel pass before it links). A kernel linked with the archives of this tree would
    contain their own names, so it is not used."""
    root = Path(root)
    checkpoint = root / 'build/xnu/checkpoints/native-4k-user-abi/kernel.macho'
    if checkpoint.is_file():
        return defined_names([checkpoint], global_only)
    filelist = root / OBJ / 'link.filelist'
    if not filelist.is_file():
        raise SystemExit('No XNU symbol names: run a kernel pass first (it writes link.filelist)')
    names = defined_names([line.strip() for line in filelist.read_text().splitlines() if line.strip()], global_only)
    # The link also exports aliases (all-alias.exp: "_real _alias") that no object defines under that name.
    aliases = root / OBJ / 'all-alias.exp'
    if aliases.is_file():
        names |= {word for line in aliases.read_text().splitlines() for word in line.split() if word.startswith('_')}
    return names
