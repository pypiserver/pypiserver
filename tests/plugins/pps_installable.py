import logging
import tempfile

import os.path as osp


def init_plugin():
    fpath = osp.join(tempfile.gettempdir(), 'installable.txt')
    open(fpath, 'w').close()
    logging.getLogger(__name__).info('Plugin wrote: %s', fpath)
