from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="reactive-python",
    version="0.1.0",
    author="Justin Spahr-Summers",
    author_email="justin@jspahrsummers.com",
    description="Reactive programming abstractions for asyncio and the Python standard library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    url="https://github.com/jspahrsummers/reactive-python",
    packages=find_packages(),
    package_data={"reactive": ["py.typed"]},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Other Environment",
        "Framework :: AsyncIO",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    install_requires=[],
    keywords="asyncio reactive reactive-programming frp",
)
