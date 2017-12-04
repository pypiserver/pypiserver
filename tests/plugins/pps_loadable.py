import logging
import tempfile

import os.path as osp


fpath = osp.join(tempfile.gettempdir(), 'loadable.txt')
open(fpath, 'w').close()
logging.getLogger(__name__).info('Plugin wrote: %s', fpath)
