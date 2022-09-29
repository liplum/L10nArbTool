from typing import List, Dict, TypeVar, Callable, Iterable, Any
from difflib import SequenceMatcher
import re
import os
from pathlib import Path
import platform

T = TypeVar("T")

all_true = ["true", "yes", "y", "ok"]

system_type = platform.system()


def to_bool(s: str, empty_means=False) -> bool:
    if len(s) == 0 and empty_means:  # empty_means True
        return True
    else:
        return s.lower() in all_true


def split_para(args: List[str],
               heading="", equal="=") -> Dict[str, str]:
    paras = {}
    for arg in args:
        arg.removeprefix(heading)
        name2para = arg.split(equal)
        if len(name2para) == 2:
            paras[name2para[0]] = name2para[1]
    return paras


def check_para_exist(test: Dict[str, str], required: List[str]):
    for name in required:
        if name not in test.keys():
            raise Exception(f"parameter \"{name}\" is missing")


def From(dic: Dict[str, T], *, Get: str, Or: T | Any = None) -> T:
    if Get not in dic:
        return Or
    return dic[Get]


def getAttrOrSet(obj, name: str, default: Callable[[], T]) -> T:
    if hasattr(obj, name):
        return getattr(obj, name)
    else:
        new = default()
        setattr(obj, name, new)
        return new


class Ref:
    def __init__(self, value=None):
        self.value = value


def contains(small, big) -> bool:
    for i in range(len(big) - len(small) + 1):
        for j in range(len(small)):
            if big[i + j] != small[j]:
                break
        else:
            return True
    return False


def read_fi(path: str, mode="r"):
    with open(path, mode=mode, encoding="UTF-8") as f:
        return f.read()


def delete_fi(path: str) -> bool:
    if os.path.exists(path):
        try:
            os.unlink(path)
            return True
        except:
            return False
    return True


# noinspection PyBroadException
def try_cast(template: T, attempt: str) -> T | None:
    try:
        if isinstance(template, str):
            return str(attempt)
        if isinstance(template, int):
            return int(attempt)
        if isinstance(template, bool):
            return to_bool(attempt)
    except:
        return None
    return None


def try_read_fi(path: str, mode="r") -> None | str:
    if os.path.isfile(path):
        return read_fi(path, mode)
    else:
        return None


def write_fi(path: str, content: str, mode="w"):
    with open(path, mode=mode, encoding="UTF-8") as f:
        f.write(content)


def append_fi(path: str, content: str, mode="a"):
    with open(path, mode=mode, encoding="UTF-8") as f:
        f.write(content)


def ensure_folder(path: str) -> bool:
    if os.path.exists(path):
        if os.path.isdir(path):
            return True
        else:
            return False
    else:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True


def fuzzy_match(target: str, candidates: Iterable[str]) -> tuple[str, float]:
    largest = None
    largest_num = 0.0
    for candidate in candidates:
        matcher = SequenceMatcher(isjunk=None, a=target, b=candidate)
        ratio = matcher.ratio()
        if largest is None or ratio > largest_num:
            largest = candidate
            largest_num = ratio
    return largest, largest_num


key_regex = re.compile("[A-Za-z0-9_]*$")


def validate_key(key: str) -> bool:
    if len(key) <= 0:
        return False
    if key[0].isupper():
        return False
    if " " in key:
        return False
    if key_regex.match(key) is None:
        return False
    return True


def env_var_str(name: str) -> str:
    if system_type == "Windows":
        return f"%{name}%"
    else:
        return f"${name}"
