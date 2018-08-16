from setuptools import find_packages, setup

setup(
    name='torrent_bot',
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': ['torrent_bot=torrent_bot.torrent_bot:main'],
    },
)
