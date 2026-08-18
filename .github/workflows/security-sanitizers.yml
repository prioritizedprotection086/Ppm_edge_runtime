name: Security Tests

on:
  push:
  pull_request:

jobs:
  python-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytest
          pip install -e .

      - name: Run tests
        run: |
          PYTHONPATH=src pytest -q

  c-sanitizers:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Install build tools
        run: |
          sudo apt-get update
          sudo apt-get install -y cmake build-essential

      - name: Configure
        run: |
          cmake -S . -B build \
            -DCMAKE_BUILD_TYPE=Debug \
            -DCMAKE_C_FLAGS="-Wall -Wextra -fsanitize=address,undefined -fno-omit-frame-pointer"

      - name: Build
        run: cmake --build build --parallel

      - name: Run C tests
        run: ctest --test-dir build --output-on-failure
