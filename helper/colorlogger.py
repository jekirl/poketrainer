import logging

import colorlog

# disable logging for root level, otherwise propagated logs would show twice
# we will later add a filehandler to the root level, if configured
colorlog.getLogger().addHandler(logging.NullHandler())


def create_logger(name, color='reset', log_level=logging.INFO, log_colors=None):
    if log_colors is None:
        log_colors = {
            'DEBUG': 'white',
            'INFO': 'white',
            'WARNING': 'red',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter('%(log_color)s%(asctime)s %(' + color + ')s[%(module)10s] %(log_color)s[%(levelname)5s] %(' + color + ')s%(message)s',
                                                   log_colors=log_colors))
    log = colorlog.getLogger(name)
    log.propagate = True
    log.addHandler(handler)
    log.setLevel(log_level)
    return log
