from setuptools import setup, find_packages

setup(
    name='pyair_utils',
    version='3.0.0',
    packages=find_packages(exclude=['docs', 'tests*']),
    url='https://github.com/LionelR/pyair_utils',
    license='BSD',
    author='Lionel Roubeyrie',
    author_email='lroubeyrie@limair.asso.fr',
    description='Utilities for the pyair package. Requires the windrose package to work.',
    long_description="""
    - geo : computing geo-statistics for sites against a central site (typically an industrial site), like windroses
    and time against wind from the central point. Also provides function for exporting results as KML files.
    - plot : Plotting facilities for windroses based reports.
    - utils : various independant functions
    """,
    keywords="air quality windrose statistics",
    install_requires=['matplotlib', 'pandas', 'windrose', 'pyair'],

)
