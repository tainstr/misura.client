#!/bin/bash

T=`readlink -m "${BASH_SOURCE[0]}"`
CLIENTROOT="$( cd "$( dirname "${T}" )"/../.. && pwd )"
CLIENTDIR=$CLIENTROOT/misura/client
export PYTHONPATH=$CLIENTROOT:$PYTHONPATH

####
# Client startup functions
####
function mgui {
	oldir=`pwd`
	cd $CLIENTDIR/bin
	python "$@"
	cd "$oldir"
}
function maq {
	mgui acquisition.py "$@"
}
function mcf {
	mgui conf.py "$@"
}
function mgr {
	mgui graphics.py "$@"
}

function mbr {
	mgui browser.py "$@"
}

function mar {
	mbr
}

####
# Interactive prompt
####
function msc {
	oldir=`pwd`
	cd $CLIENTDIR
	python -i -c "import numpy as np; \
from cPickle import loads; \
from misura.client import from_argv; \
from time import sleep; \
m=from_argv()" $@
	cd "$oldir"
}
