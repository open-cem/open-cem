# OpenCEM

OpenCEM is the _Open Source Customer Energy Manager_.

It is based on the `sgr-commhandler` Library.

Find documentation in folder [Documentation](./OpenCEM/Documentation).

## Installation

First, you must have **Python 3.12** installed.
At the moment the SGr commhandler library is not compatible with newer versions.

Create a virtual environment under `.venv`:

```bash
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Linux Shell
source ./.venv/bin/activate
```

Install the dependencies from PyPi:

```bash
pip install -U -r requirements.txt
```

## Run

Provided that you performed the installation steps and activated the virtual environment:

```bash
python openCEM_main_GUI.py
```
