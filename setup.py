from setuptools import setup, find_packages

setup(
    name="morning",
    version="0.1",
    packages=find_packages(),
    install_requires=[line.strip() for line in open("requirements.txt")
                     if not line.startswith("#") and line.strip()],
)
