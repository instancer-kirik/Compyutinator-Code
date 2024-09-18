from setuptools import setup, find_packages

setup(
    name="llama_ide_assistant_setup_and_downloader",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "ctransformers>=0.2.24",
        "requests",
        "tqdm",
        "PyQt6",
    ],
    author="Kirik",
    author_email="kirik@instance.select",
    description="An IDE assistant using Llama model",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/llama_ide_assistant",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)