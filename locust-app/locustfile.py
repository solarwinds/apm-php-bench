from os import environ
from locust import HttpUser, task, between, events
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader


api_token = environ.get("API_TOKEN")
endpoint = environ.get("OTEL_COLLECTOR")
service_name = environ.get("SERVICE_NAME")
exporter = OTLPMetricExporter(
    endpoint=f"{endpoint}/v1/metrics",
    headers={
        "authorization": f"Bearer {api_token}"
    }
)
reader = PeriodicExportingMetricReader(
    exporter,
    export_interval_millis=5000, # 5 seconds
)
resource = Resource.create(
    attributes={
        "service.name": service_name,
        "sw.data.module": "apm",
        "sw.apm.version": "0.0.0",
    }
)
meter_provider = MeterProvider(
    resource=resource,
    metric_readers=[reader],
)
metrics.set_meter_provider(meter_provider)

otel_meter = meter_provider.get_meter("apm-php-bench")
http_response_time = otel_meter.create_histogram(
    name="apm.php.benchmark.response.time",
    description="measures the duration of the inbound HTTP request",
    unit="ms",
)

requests_tracker = {
    "uninstrumented": {"request_count" : 0, "request_time" : 0 },
    "9.0.0-alpha.1": {"request_count" : 0, "request_time" : 0 },
    "8.13.0": {"request_count" : 0, "request_time" : 0 },
}


class FlaskSwarmUser(HttpUser):
    wait_time = between(0.25, 0.5)  # 0.25-0.5 seconds
    @task
    def request_uninstrumented(self):
        self.client.get(
            "http://nginx-uninstrumented/complex",
            name="uninstrumented",
        )
    @task
    def request_apm_php_9_alpha(self):
        self.client.get(
            "http://nginx-apm-php-9-alpha/complex",
            name="9.0.0-alpha.1",
        )
    @task
    def request_apm_8(self):
        self.client.get(
            "http://nginx-apm-8/complex",
            name="8.13.0",
        )


@events.request.add_listener
def report_response_time(response_time, **kw):
    app_kind = kw["name"]
    requests_tracker[app_kind]["request_count"] += 1
    requests_tracker[app_kind]["request_time"] += int(response_time)
    current_avg = int(
        requests_tracker[app_kind]["request_time"] / requests_tracker[app_kind]["request_count"]
    )
    http_response_time.record(
        current_avg,
        attributes={
            "benchmark.app.kind": app_kind
        }
    )
