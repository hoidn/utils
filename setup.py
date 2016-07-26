from setuptools import setup, find_packages

setup(name = 'utils',
    packages = find_packages('.'),
    package_dir = {'utils': 'utils'},
    install_requires = ['plotly', 'meta'],
    zip_safe = False)
