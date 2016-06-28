#!/bin/bash
#-*- coding: utf-8 -*-
#
## Checks that README has no RsT-syntactic errors.
# Since it is used by `setup.py`'s `description` if it has any errors,
# PyPi would fail parsing them, ending up with an ugly landing page,
# when uploaded.

>&2 echo "+++ Checking README for PyPy...."
set +x ## Enable for debug

my_dir=`dirname "$0"`
cd $my_dir/..

py=""
rst="rst2html"
if [ ! -x "`which $rst 2>/dev/null`" ]; then
    ## In WinPython, only a python-script exist in PATH,
    #   so execute it with python-interpreter.
    #
    exe="`which rst2html.py 2> /dev/null`"
    if [ $? -eq 0 ]; then
        py=python
        rst="$exe"
    else
        echo -e "Cannot find 'rst2html'! \n Sphinx installed? `pip show sphinx`" &&
        exit 1
    fi

    if [ -x "`which cygpath`" ]; then
        rst="`cygpath -w $rst`"
    fi
fi

export PYTHONPATH='$my_dir/..'
#python setup.py --long-description > t.rst ## Uncomment to inspect it.
python setup.py --long-description | $py "$rst"  --halt=warning > /dev/null && echo OK
