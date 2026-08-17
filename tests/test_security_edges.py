name: Security Tests

on:
  push:
    branches:
      - main
      - master
      - security-edge-tests
  pull_request:

jobs:
  python-tests:
    name: Python Security Tests
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then
            pip install -r requirements.txt
          fi
          pip install pytest
          pip install -e .

      - name: Run security tests
        run: |
          pytest -q tests/test_security_edges.py

      - name: Run full test suite
        run: |
          pytest -q

  c-sanitizers:
    name: C Sanitizer Tests
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install build tools
        run: |
          sudo apt-get update
          sudo apt-get install -y cmake build-essential

      - name: Configure sanitizer build
        run: |
          cmake -S . -B build \
            -DCMAKE_BUILD_TYPE=Debug \
            -DCMAKE_C_FLAGS="-Wall -Wextra -Wconversion -Wsign-conversion -fsanitize=address,undefined -fno-omit-frame-pointer" \
            -DCMAKE_CXX_FLAGS="-Wall -Wextra -Wconversion -Wsign-conversion -fsanitize=address,undefined -fno-omit-frame-pointer"

      - name: Build
        run: |
          cmake --build build --parallel

      - name: Run C tests
        run: |
          ctest --test-dir build --output-on-failure
