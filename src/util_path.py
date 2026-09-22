"""util"""

import os
import re
from glob import glob
from pathlib import Path

import yaml


def is_py_path_not_venv(full_path: str) -> bool:
    """ends with .py and not in venv"""
    if not full_path.endswith(".py"):
        return False
    if (f"{os.sep}.venv{os.sep}" in full_path) or (
        f"{os.sep}venv{os.sep}" in full_path
    ):
        return False

    return True


def has_no_extension(path: str) -> bool:
    """check if path has no extension"""
    return os.path.splitext(path)[1] == ""


def local_path_to_git_path(root_dir: str, local_path: str) -> str:
    """replace \\ to /, remove first /"""

    root_dir_sep = root_dir.replace("\\", "/")
    local_path_sep = local_path.replace("\\", "/")

    path_new = local_path_sep.removeprefix(root_dir_sep)
    path_new = path_new.replace("\\", "/")
    path_new = f"{path_new[1:]}" if path_new.startswith("/") else path_new
    return path_new


def git_path_to_local_path(root_dir: str, git_path: str) -> str:
    r"""
    root_dir=c:\a, git_path=b/c.py -> c:\a\b\c.py
    """
    path = f"{root_dir}{os.sep}{git_path}"
    path = path.replace("/", os.sep)
    return path


def to_namespace(root_dir: str, path: str) -> str:
    """remove extension, remove root_dir, replace \\ or / to ., remove first ."""

    path_new = os.path.splitext(path)[0]
    path_new = path_new.removeprefix(root_dir)
    path_new = path_new.replace("\\", ".")
    path_new = path_new.replace("/", ".")
    if path_new.startswith("."):
        path_new = path_new[1:]
    return path_new


def get_abs_path(root_dir: str, full_path: str) -> str:
    """
    get absolute path
    root_dir=c:\\a, full_path=c:\\a\\b\\c.py -> b\\c.py
    """

    if not full_path.startswith(root_dir):
        raise ValueError(f"{full_path} not starts with {root_dir}")

    return full_path.removeprefix(root_dir)


def glob_file_patterns(
    patterns: list[str], exclude_patterns: list[str] | None = None
) -> list[str]:
    """
    return path by glob.
    used Path to compare '\' and '/' as same
    """
    file_paths: list[Path] = []
    for file_pattern in patterns:
        file_paths_glob = glob(file_pattern, recursive=True)
        for file_path_cur in file_paths_glob:
            file_paths.append(Path(file_path_cur))

    if exclude_patterns:
        exclude_files: list[Path] = []
        for exclude_pattern in exclude_patterns:
            exclude_files_glob = glob(exclude_pattern, recursive=True)
            for file_path_cur in exclude_files_glob:
                exclude_files.append(Path(file_path_cur))

        file_paths = [f for f in file_paths if f not in exclude_files]

    return [str(file_path.resolve()) for file_path in file_paths]


def is_target_file(
    patterns: list[str],
    exclude_patterns: list[str],
    full_path: str,
) -> bool:
    """
    check if full_path matches patterns and not matches exclude_patterns
    """

    if not any(re.search(pattern, full_path) for pattern in patterns):
        return False

    if any(
        re.search(exclude_pattern, full_path) for exclude_pattern in exclude_patterns
    ):
        return False

    return True


def load_config[T](config_path: str, model: type[T]) -> T:
    """
    load yaml config

    Example:
        from util_path import ReplaceLiteralStringConfig
        load_config("./config/replace_literal_string.yaml", ReplaceLiteralStringConfig)
    """

    with open(config_path, encoding="utf-8") as f:
        # pyrefly: ignore [missing-attribute]
        return model.model_validate(yaml.safe_load(f))
