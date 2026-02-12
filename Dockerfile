FROM python:3.12-slim-bookworm

ENV HTTP_HOST=0.0.0.0
ENV HTTP_PORT=8000
ENV MQTT_HOST=
ENV MQTT_PORT=1883
ENV INFLUX_HOST=
ENV INFLUX_PORT=8086
ENV INFLUX_USER=
ENV INFLUX_PASSWORD=
ENV CONFIG_PATH=/app/System_Settings
ENV XML_PATH=/app/xml_files

WORKDIR /app

COPY . .

# Install dependencies:
RUN pip install --no-cache-dir -U pip
RUN pip install --no-cache-dir -U -r requirements.txt

# Run the application:
CMD ["python", "OpenCEM_main_GUI.py"]
