import colorlog


def create_logger(name, color, log_color='log_color'):
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter('%(asctime)s %(' + color + ')s[%(module)10s] %(' + log_color + ')s[%(levelname)5s] %(' + color + ')s%(message)s',
                                                   log_colors={
                                                       'DEBUG': 'white',
                                                       'INFO': 'white',
                                                       'WARNING': 'red',
                                                       'ERROR': 'red',
                                                       'CRITICAL': 'red,bg_white',
                                                   },))
    log = colorlog.getLogger(name)
    log.propagate = False
    log.addHandler(handler)
    return log
