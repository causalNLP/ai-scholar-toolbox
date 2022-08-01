import setuptools

with open('README.md', 'r') as fh:
    README = fh.read()

VERSION = '0.0.1'

setuptools.setup(
    name='ai_scholar_toolbox',
    version=VERSION,
    author='',
    description='Find Google Scholar Profiles',
    long_description=README,
    long_description_content_type='text/markdown',
    install_requires=[
        'bs4', 
        'selenium',
        'gdown',
        'requests',
        'pandas',
        'numpy'
    ],
    url='https://github.com/causalNLP/ai-scholar-toolbox',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
)
