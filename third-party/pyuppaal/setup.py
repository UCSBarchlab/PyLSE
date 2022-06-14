from distutils.core import setup

setup(name='pyuppaal',
    version='0.1',
    description='Python library for manipulating UPPAAL xml files. Can currently import, export and layout models.',
    url='https://github.com/bencaldwell/pyuppaal',
    author='Ben Caldwell',
    author_email='benny.caldwell@gmail.com',
    license='GPL-3',
    packages=['pyuppaal'],
    requires=['pygraphviz']
    )
