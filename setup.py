from setuptools import setup, find_packages

setup(
    name = 'pylse',
    version = '0.1.0',
    packages = find_packages(),
    description = 'Pulse-Transfer Level eDSL for the design, simulation, and verification of superconductor electronics',
    author = 'UCSBarchlab',
    author_email = 'mchristensen@ucsb.edu, gtzimpragos@ucsb.edu',
    # url = '',
    # download_url = '',
    tests_require = ['tox', 'nose'],
    classifiers = [
        'Development Status :: 1 - Planning',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.8',
        'Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)',
        'Topic :: System :: Hardware'
        ],
)
