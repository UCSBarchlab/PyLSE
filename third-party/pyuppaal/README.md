# pyuppaal
Python library for manipulating UPPAAL xml files. Can currently import, export and layout models.

This project was created from the existing launchpad site https://launchpad.net/pyuppaal.

## Installation Instructions 

1) Install pygraphviz. On windows the requires steps are:

    1) Install mingw32

    2) Download pygraphviz sources

    3) Edit setup.py in pygraphviz folder to:

        * library_path=r"c:\Program Files (x86)\Graphviz 2.28\bin"

        * include_path=r"c:\Program Files (x86)\Graphviz 2.28\include"

    4) run python setup.py build -c mingw32

    5) run python setup.py install
  
2) Install pyuppaal using python setup.py install

## Running pyuppal scripts

To autolayout a model run bin/layout_uppaal, use option --help for arguments.

## Using pyuppal

To use pyuppal in your application or the python shell, use import pyuppaal. 
Remember to have pyuppaal in you PYTHONPATH.

## Running tests
To run tests invoke the test script test/run_tests.sh:

sh test/run_tests.sh

Remember to have verifyta in you path else the test case for UPPAAL integration
will fail. 
