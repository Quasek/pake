import subprocess

import ui

def execute(command, capture_output = False):
    out = ''
    try:
        if capture_output:
            out = subprocess.check_output(command, shell=True)
        else:
            subprocess.check_call(command, shell=True)
    except subprocess.CalledProcessError as e:
        raise Exception("command exited with error({}): {}".format(str(e.returncode), command))

    ui.debug("command completed: " + command)
    return out

