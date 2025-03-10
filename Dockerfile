FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
RUN opentelemetry-bootstrap -a install

COPY . /app

EXPOSE 5005

CMD ["opentelemetry-instrument", "--traces_exporter", "console,otlp", "--metrics_exporter", "console", "--service_name", "python-telemetry-api", "--exporter_otlp_endpoint", "http://192.168.1.21:4317", "python3", "app.py"]
