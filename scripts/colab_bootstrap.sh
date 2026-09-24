#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python}"

"$PYTHON_BIN" -m pip install -U pip

PY_MINOR="$("$PYTHON_BIN" -c 'import sys; print(sys.version_info.minor)')"
if [ "$PY_MINOR" -ge 13 ]; then
  "$PYTHON_BIN" -m pip install -U -f https://www.open3d.org/docs/latest/dev_wheels.html open3d
else
  "$PYTHON_BIN" -m pip install 'open3d>=0.19,<0.20'
fi

"$PYTHON_BIN" -m pip install   'numpy>=1.24'   'pydantic>=2.6'   'pytest>=8'   'matplotlib>=3.8'   'pandas>=2.0'

"$PYTHON_BIN" -m pip install -e . --no-deps

"$PYTHON_BIN" - <<'PY'
import sys
import open3d as o3d
import scan2stage
import matplotlib
import pandas
print("Python executable:", sys.executable)
print("Python:", sys.version)
print("Open3D:", o3d.__version__)
print("Scan2Stage:", scan2stage.__version__)
print("Scan2Stage path:", scan2stage.__file__)
print("Matplotlib:", matplotlib.__version__)
print("Pandas:", pandas.__version__)
PY
