#!/bin/sh

export PYTHONPATH=..

cd `pwd`/`dirname $0`

for i in `ls test_*.py ulp/test_*.py`; do
    python $i
done
