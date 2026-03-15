from setuptools import setup, find_packages

setup(
    name="finance-rule-engine",
    version="2.0.0",
    description="AI-powered rule engine for financial/insurance systems",
    author="Rule Engine Team",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "antlr4-python3-runtime>=4.13.0",
        "pydantic>=2.5.0",
        "PyYAML>=6.0.0",
        "numpy>=1.26.0",
        "pandas>=2.1.0",
        "fastapi>=0.109.0",
        "uvicorn>=0.27.0",
        "sqlalchemy>=2.0.0",
        "structlog>=24.0.0",
        "tenacity>=8.2.0",
        "cachetools>=5.3.0",
    ],
    extras_require={
        "ml": ["onnxruntime>=1.16.0"],
        "redis": ["redis>=5.0.0"],
        "dev": ["pytest>=8.0.0", "pytest-asyncio>=0.23.0", "hypothesis>=6.92.0"],
    },
    entry_points={
        "console_scripts": [
            "rule-engine=api.server:main",
        ],
    },
)
