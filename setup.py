import setuptools

with open('README.md', 'r') as fh:
    README = fh.read()

VERSION = '0.0.1'

setuptools.setup(
    name='ai_scholar_toolbox',
    version=VERSION,
    author='',
    license="MIT",
    description='Find Google Scholar Profiles',
    long_description=README,
    long_description_content_type='text/markdown',
    install_requires=[
        'gdown',
        'bs4', 
        'selenium',
        'pandas',
        'requests',
        'numpy'
    ],
    url='https://github.com/causalNLP/ai-scholar-toolbox',
    packages=setuptools.find_packages(),
    classifiers=[        
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
)
