#!/usr/bin/env bash
set -euo pipefail

python -m pip install -U pip

PY_MINOR="$(python -c 'import sys; print(sys.version_info.minor)')"
if [ "$PY_MINOR" -ge 13 ]; then
  python -m pip install -U -f https://www.open3d.org/docs/latest/dev_wheels.html open3d
else
  python -m pip install 'open3d>=0.19,<0.20'
fi

python -m pip install   'numpy>=1.24'   'pydantic>=2.6'   'pytest>=8'   'matplotlib>=3.8'   'pandas>=2.0'

python -m pip install -e . --no-deps

python - <<'PY'
import sys
import open3d as o3d
import scan2stage
import matplotlib
import pandas
print("Python:", sys.version)
print("Open3D:", o3d.__version__)
print("Scan2Stage:", scan2stage.__version__)
print("Matplotlib:", matplotlib.__version__)
print("Pandas:", pandas.__version__)
PY
