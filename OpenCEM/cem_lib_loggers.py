# Generative AI was used for some Code

import logging
import os
from logging.handlers import TimedRotatingFileHandler


def create_debug_logger():
    """
    This logger will log every Level. Is only ment for debugging, because files will get big quickly.
    """
    logger = logging.getLogger()  # gives back the root logger
    logger.setLevel(logging.DEBUG)


    path = os.path.join(os.getcwd(), "_logFiles", "Debug.log")
    print(path)
    file_handler = TimedRotatingFileHandler(path, when='midnight', interval=1, backupCount=0)

    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s // File"%(pathname)s", function %(funcName)s, line %(lineno)d')  # Add path, function and line, to always know what did the log

    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)


def create_event_logger():
    """
    Will log all events with the tag INFO or higher and write a Logfile
    """
    logger = logging.getLogger()

    if logger.level != logging.DEBUG:
        logger.setLevel(logging.INFO)

    print(os.getcwd())

    path = os.path.join(os.getcwd(), "_logFiles", "Event.log")
    print(path)
    file_handler = TimedRotatingFileHandler(path, when='midnight', interval=1, backupCount=0)
    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s // File"%(pathname)s", function %(funcName)s, line %(lineno)d')  # Add path, function and line, to always know what did the log

    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)


def show_logger_in_console(Log_level: int):
    """
    Will enable the event and debug-log in the console. The statistics logger will not be showing in the console, because it would cluster the console too much.
    param: level: CRITICAL = 50, ERROR = 40, WARNING = 30,INFO = 20, DEBUG = 10
    """
    logger = logging.getLogger()

    streaming_handler = logging.StreamHandler()
    streaming_handler.setLevel(Log_level)
    streaming_handler.setFormatter(CustomFormatter())

    logger.addHandler(streaming_handler)


class CustomFormatter(logging.Formatter):
    """
    creates the format for a colored console log
    Source: https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output
    """

    white = "\u001b[37m"
    yellow = "\u001b[33m"
    red = "\u001b[31m"
    bold_red = "\u001b[31;1m"
    reset = "\u001b[0m"
    format = '%(asctime)s %(levelname)s: %(message)s // File"%(pathname)s", function %(funcName)s, line %(lineno)d'

    FORMATS = {
        logging.DEBUG: white + format + reset,
        logging.INFO: white + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

class MyTimedRotatingFileHandler(TimedRotatingFileHandler):
    """
    This is a custom TimeRotatingFileHandler.
    It works like a normal TimeRotatingFileHandler, but this custom one can add a header at the top of a file.
    source: https://stackoverflow.com/questions/27840094/write-a-header-at-every-logfile-that-is-created-with-a-time-rotating-logger
    """

    def __init__(self, filename, when='h', interval=1, backupCount=0, encoding=None, delay=False, utc=False, atTime=None, header=''):
        self.header = header
        super().__init__(filename, when, interval, backupCount, encoding, delay, utc, atTime)
    def _open(self):
        stream = super()._open()
        if self.header and stream.tell() == 0:
            stream.write(self.header + self.terminator)
            stream.flush()
        return stream

def create_device_logger() -> logging.Logger:
    """
    This methode creates the device logger to log the data from the devices.

    """

    device_logger = logging.getLogger("device_logger")
    device_logger.setLevel(logging.INFO)
    device_logger.propagate = False  # stats won't be showing in root logger

    path = os.path.join(os.getcwd(), "_logFiles", "DeviceLog.log")
    device_values_header = "timestamp;name;type;info;state;value;unit;error_code"

    # rollback once a day
    file_handler = MyTimedRotatingFileHandler(path, when='midnight', interval=1, backupCount=0, header=device_values_header)
    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s;%(message)s', datefmt="%d.%m.%y %H:%M:%S")
    file_handler.setFormatter(formatter)

    device_logger.addHandler(file_handler)

    return device_logger













