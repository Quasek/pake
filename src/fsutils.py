import os
import errno
import itertools

import ui
import shell

BUILD_ROOT = os.path.normpath(os.getcwd() + "/__build")

def mkdir_recursive(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

def make_build_dir(configuration_name):
    mkdir_recursive(build_dir(configuration_name))


def build_dir(configuration_name):
    return os.path.normpath(BUILD_ROOT + "/" + configuration_name)


def is_newer_than(prerequisite, target):
    if os.path.isfile(target):
        ret = get_mtime(prerequisite) > get_mtime(target)
        ui.debug("is {} newer than {} = {!s}".format(prerequisite, target, ret))
        return ret
    else:
        ui.debug(target + " doesn't exist, treating like older")
        return True


def is_any_newer_than(prerequisites, target):
    return any(map(lambda pre: is_newer_than(pre, target), prerequisites))


def get_mtime(filename):
    return os.path.getmtime(filename)


def __is_pake_file(filename):
    return os.path.splitext(filename)[1] == ".pake"


def __filter_pake_files(dirpath, filenames):
    return filter(__is_pake_file,
                  [os.path.join(dirpath, f) for f in filenames
                   if not dirpath.startswith(BUILD_ROOT)])


def __flatten(nested_list):
    return list(itertools.chain(*nested_list))


def _find_pake_files(path=os.getcwd()):
    return __flatten(__filter_pake_files(dirpath, filenames)
                     for (dirpath, _, filenames) in os.walk(path))

pake_files = _find_pake_files()
