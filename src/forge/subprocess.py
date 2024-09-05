from __future__ import annotations

import shlex
import subprocess as stdlib_subprocess

from forge.logger import log

# Pass through check_output without logging
check_output = stdlib_subprocess.check_output
CalledProcessError = stdlib_subprocess.CalledProcessError


def run(logfile, *args, **kwargs):
    """A wrapper around subprocess.run() that logs all output.

    Subprocesses will always be run in check mode, with UTF-8 text output, and stderr
    redirected to stdout, and stdout being piped so it can be logged.

    :param logfile: An open file handle to which all output will be logged.
    :param args: The args to pass to subprocess.run
    :param kwargs: The keyword arguments to pass to subprocess.run.
    """
    # stdout/err must be piped so the output streamer can print it.
    kwargs["stdout"] = stdlib_subprocess.PIPE
    kwargs["stderr"] = stdlib_subprocess.STDOUT
    # use line-buffered output by default
    kwargs["bufsize"] = 0
    # use text mode
    kwargs["encoding"] = "UTF-8"
    kwargs["text"] = True
    kwargs["errors"] = "ignore"

    log(logfile)
    log(logfile, f">>> {shlex.join(str(arg) for arg in args[0])}", debug=True)
    for key, value in kwargs.get("env", {}).items():
        log(logfile, f"    {key}={shlex.quote(value)}", debug=True)
    log(logfile, "-" * 80, debug=True)

    with stdlib_subprocess.Popen(*args, **kwargs) as process:
        while (return_code := process.poll()) is None:
            output = process.stdout.readline()
            if output:
                log(logfile, output.strip())

        log(logfile, "-" * 80, debug=True)
        log(logfile, f"<<< Return code: {return_code}", debug=True)

    if return_code:
        raise stdlib_subprocess.CalledProcessError(return_code, args)

    return stdlib_subprocess.CompletedProcess(args, return_code)
