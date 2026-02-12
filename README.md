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

## Docker

You can run OpenCEM as Docker container.

### Build

You can build your own Docker image. Start the build from the repository's root directory:

```bash
docker build --rm ghcr.io/open-cem/open-cem:latest .
```

### Image

An official image is provided on Github:

```bash
docker pull ghcr.io/open-cem/open-cem:latest 
```

### Environment Variables

You can customize the OpenCEM Docker image at runtime using environment variables:

* `HTTP_HOST`: The web GUI listener address, defaults to `0.0.0.0`
* `HTTP_PORT`: The web GUI TCP port, defaults to `8000`
* `MQTT_HOST`: The MQTT broker host, defaults to `localhost`
* `MQTT_PORT`: The MQTT broker port, defaults to `1883`
* `INFLUX_HOST`: The InfluxDB host, defaults to `localhost`
* `INFLUX_PORT`: The InfluxDB port, defaults to `8086`
* `INFLUX_USER`: The (optional) InfluxDB user name
* `INFLUX_PASSWORD`: The (optional) InfluxDB password
