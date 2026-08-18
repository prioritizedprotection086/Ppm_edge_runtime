"""Build script for the minimal CPython C-extension boundary benchmark.

Compiles benchmark/cext/ppm_edge_ext.c together with the unmodified
Src/Ppm_edge.c kernel source. Does not modify Src/Ppm_edge.c or
Src/Ppm_edge.h -- includes and links them as-is.
"""
from pathlib import Path
from setuptools import setup, Extension

REPO = Path(__file__).resolve().parents[2]

ext = Extension(
    "ppm_edge_ext",
    sources=[
        str(Path(__file__).parent / "ppm_edge_ext.c"),
        str(REPO / "Src" / "Ppm_edge.c"),
    ],
    include_dirs=[str(REPO / "Src")],
    extra_compile_args=["-O2"],
)

setup(
    name="ppm_edge_ext",
    version="0.1.0",
    ext_modules=[ext],
)
