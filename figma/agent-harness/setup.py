from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-figma",
    version="1.0.0",
    description="CLI harness for Figma — design file inspection, export, and collaboration via REST API",
    python_requires=">=3.10",
    packages=find_namespace_packages(where=".", include=["cli_anything.*"]),
    package_dir={"": "."},
    install_requires=[
        "click>=8.0.0",
        "prompt-toolkit>=3.0.0",
        "requests>=2.31.0",
        "websockets>=11.0",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
            "responses",
        ]
    },
    entry_points={
        "console_scripts": [
            "cli-anything-figma=cli_anything.figma.figma_cli:main",
        ]
    },
    package_data={
        "cli_anything.figma": ["skills/SKILL.md"],
    },
)
