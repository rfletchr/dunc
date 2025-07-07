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


def find_files(pattern: str, recursive: bool = True, root: str = None) -> list[str]:
    """
    Find files matching the given pattern in the specified root directory.
    If root is None, it defaults to the source path.
    """

    if root is None:
        root = get_source_path()

    if not os.path.exists(root):
        raise DunkError(f"Root directory '{root}' does not exist.")

    matches = glob.glob(os.path.join(root, pattern), recursive=recursive)
    rel_matches = [os.path.relpath(m, root) for m in matches]

    return rel_matches


def install_files(
    files: list[str],
    install_path: str = None,
    symlink: bool = False,
    executable: bool = False,
):
    """
    Install the specified files.
    """
    if install_path is None:
        install_path = get_install_path()

    source_path = get_source_path()

    is_windows = platform.system() == "Windows"
    symlink = symlink and get_is_local() and not is_windows

    file_len = max(len(file) for file in files)

    for file in files:
        if os.path.isabs(file):
            raise DunkError(f"path must be relative, not absolute: '{file}'")

        source_file = os.path.join(source_path, file)
        install_file = os.path.join(install_path, file)
        os.makedirs(os.path.dirname(install_file), exist_ok=True)

        padded_name = file.ljust(file_len + 2, " ")

        if symlink:
            print(f"- [link] {padded_name} -> {install_file}")
            try:
                os.symlink(source_file, install_file)
            except FileExistsError:
                os.remove(install_file)
                os.symlink(source_file, install_file)
        else:
            print(f"- [copy] {padded_name} -> {install_file}")

            with open(source_file, "rb") as src, open(install_file, "wb") as dst:
                dst.write(src.read())

        if executable and not is_windows:
            existing_bitmask = os.stat(install_file).st_mode
            mask_with_exec = existing_bitmask | 0o111
            os.chmod(install_file, mask_with_exec)


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
        install_func()


def main():
    try:
        print()
        execute()
        sys.exit(0)

    except DunkError as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
