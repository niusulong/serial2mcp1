"""
Serial-Agent-MCP 项目安装配置文件
基于 MCP (Model Context Protocol) 的智能串口交互工具
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="serial2mcp",
    version="0.1.0",
    author="Niusulong",
    author_email="niusulong@example.com",
    description="基于 MCP 协议的智能串口交互工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/niusulong/serial2mcp",
    packages=find_packages(where="src", include=["serial2mcp", "serial2mcp.*"]),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "serial2mcp=serial2mcp.main:main",
        ],
    },
)