import logging


def get_logger(name="root", loglevel="INFO"):
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger
    else:
        loglevel = getattr(logging, loglevel.upper(), logging.INFO)
        logger.setLevel(loglevel)
        fmt = "%(asctime)s %(filename)-18s %(levelname)-8s: %(message)s"
        fmt_date = "[%T] [%d.%m.%Y] [%Z]"
        formatter = logging.Formatter(fmt, fmt_date)
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
