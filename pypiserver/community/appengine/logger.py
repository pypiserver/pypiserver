import logging


class CustomLogger:
    """Utility wrapper class around the logging mechanism"""

    @staticmethod
    def configure_logging(verbose=False):
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        return logger

    def __init__(self, verbose_logger=True):
        self._logger = self.configure_logging(verbose=verbose_logger)

    def info(self, msg=''):
        self._logger.info(msg)

    def debug(self, msg=''):
        self._logger.debug(msg)

    def warning(self, msg=''):
        self._logger.warning(msg)

    def error(self, msg=''):
        self._logger.error(msg, exc_info=True)
