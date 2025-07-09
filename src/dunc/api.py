__all__ = [
    "is_install",
    "get_build_path",
    "get_install_path",
    "get_source_path",
    "get_project_file",
    "get_project_name",
    "get_project_version",
    "get_is_release",
    "get_is_local",
    "find_files",
    "install_files",
    "DunkError",
]
import shutil
import os
import sys
import ast
import glob
import platform


def is_build():
    return bool(os.environ.get("REZ_BUILD_ENV"))


def is_install():
    """
    Is the build in install mode?
    """
    return os.environ.get("REZ_BUILD_INSTALL") == "1"


def get_build_path():
    """
    Get the build path.
    """
    return os.environ["REZ_BUILD_PATH"]


def get_install_path():
    """
    Get the install path.
    """
    return os.environ["REZ_BUILD_INSTALL_PATH"]


def get_source_path():
    """
    Get the source path.
    """
    return os.environ["REZ_BUILD_SOURCE_PATH"]


def get_project_file():
    """
    Get the project file (package.py).
    """
    return os.environ["REZ_BUILD_PROJECT_FILE"]


def get_project_name():
    """
    Get the project name.
    """
    return os.environ["REZ_BUILD_PROJECT_NAME"]


def get_project_version():
    """
    Get the project version.
    """
    return os.environ["REZ_BUILD_PROJECT_VERSION"]


def get_is_release():
    """
    Get the build type.
    """
    return os.environ["REZ_BUILD_TYPE"] == "central"


def get_is_local():
    """
    Is the build local?
    """
    return os.environ["REZ_BUILD_TYPE"] == "local"


def find_files(
    pattern: str, recursive: bool = True, root: str = None
) -> list[tuple[str, str]]:
    """
    Find files matching the given pattern in the specified root directory.
    If root is None, it defaults to the source path.
    """

    if root is None:
        root = get_source_path()

    if root and not os.path.isabs(root):
        root = os.path.join(get_source_path(), root)

    if not os.path.exists(root):
        raise DunkError(f"Root directory '{root}' does not exist.")

    matches = glob.glob(os.path.join(root, pattern), recursive=recursive)
    files_only = [match for match in matches if os.path.isfile(match)]
    return [(root, os.path.relpath(match, root)) for match in files_only]


def _copy_file(src: str, dst: str, executable: bool = False, symlink: bool = False):
    """
    Copy a file from src to dst.
    If executable is True, make the file executable.
    """
    if not os.path.exists(os.path.dirname(dst)):
        os.makedirs(os.path.dirname(dst))

    if platform.system() == "Windows":
        # symlinks on windows are a mess, don't bother.
        print(f"[copy] {src} -> {dst}")
        shutil.copy2(src, dst)

    else:
        if os.path.exists(dst):
            os.remove(dst)

        if symlink:
            print(f"[link] {src} -> {dst}")
            os.symlink(src, dst)
        else:
            print(f"[copy] {src} -> {dst}")
            shutil.copy2(src, dst)

        if executable:
            print(f"[+exe] {dst}")
            os.chmod(dst, os.stat(dst).st_mode | 0o111)


def install_files(
    files: list[tuple[str, str]],
    install_path: str = None,
    symlink: bool = False,
    executable: bool = False,
):
    """
    Install the specified files.
    """
    if install_path is None:
        install_path = get_install_path()

    if install_path and not os.path.isabs(install_path):
        install_path = os.path.join(get_install_path(), install_path)

    for source_path, rel in files:
        src = os.path.join(source_path, rel)
        dst = os.path.join(install_path, rel)

        _copy_file(src, dst, executable=executable, symlink=symlink)


class DunkError(Exception):
    """Base class for all Dunk-related exceptions."""

    pass


def get_clobber():
    """
    Check if the clobber environment variable is set.
    If set, it indicates that the build directory should be removed before building.
    """
    return os.environ.get("DUNK_CLOBBER") == "1"


def extract_function(project_file: str, function_name: str, optional: bool = False):
    with open(project_file, "r") as file:
        source = file.read()

    tree = ast.parse(source)
    build_function = None

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            build_function = node
            break

    if build_function is None and optional:
        return None

    if build_function is None:
        raise ValueError(f"No {function_name} function found in the project file.")

    func_text = ast.unparse(build_function)

    function_globals = {}
    code = compile(func_text, project_file, "exec")
    exec(code, function_globals)
    return function_globals[function_name]


def execute():
    if not is_build():
        raise DunkError("This script should only be run in a build environment.")
    project_file = get_project_file()

    if not os.path.exists(project_file):
        raise DunkError(f"Project file '{project_file}' does not exist.")

    if not os.environ.get("REZ_BUILD_ENV"):
        raise DunkError(
            "REZ_BUILD_ENV is not set, are you running this in a build environment?"
        )

    build_func = extract_function(project_file, "build", optional=True)
    if build_func:
        print("Executing build function...")
        build_func()

    if is_install():
        print("Executing install function...")
        install_func = extract_function(project_file, "install")
        if not install_func:
            raise DunkError("No install function found in the project file.")
        install_func()


def main():
    try:
        print()
        execute()
        sys.exit(0)

    except DunkError as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
