import traceback


def log(log_file, *args, debug=False, **kwargs):
    """Log output to the screen, and to the log file.

    :param log_file: An open file handle to write log content to
    :param args: The arguments to pass to print
    :param debug: Is the output debug-specific? Debug output is only output to the log
        file.
    :param kwargs: Additional keyword arguments to pass to print.
    """
    if not debug:
        print(*args, **kwargs)
    if log_file:
        print(*args, **kwargs, file=log_file)


def log_exception(log_file):
    """Log the current exception stack tracce to the screen, and to the log file.

    :param log_file: An open file handle to write log content to
    """
    traceback.print_exc()
    if log_file:
        traceback.print_exc(file=log_file)
