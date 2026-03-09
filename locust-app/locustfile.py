from os import environ
import random

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

otel_meter = meter_provider.get_meter("apm-php-benchmark")
http_response_time = otel_meter.create_histogram(
    name="apm.php.benchmark.response.time",
    description="measures the duration of the inbound HTTP request",
    unit="ms",
)

requests_tracker = {
    "uninstrumented": {"request_count" : 0, "request_time" : 0 },
    "oboe": {"request_count" : 0, "request_time" : 0 },
    "otel": {"request_count" : 0, "request_time" : 0 },
    "alpha": {"request_count" : 0, "request_time" : 0 },
    "dev": {"request_count" : 0, "request_time" : 0 }
}


class FlaskSwarmUser(HttpUser):
    wait_time = between(0.25, 0.5)  # 0.25-0.5 seconds

    # @task
    # def request_uninstrumented(self):
    #     self.client.get(
    #         "http://nginx-uninstrumented/complex",
    #         name="uninstrumented",
    #     )
    # @task
    # def request_oboe(self):
    #     self.client.get(
    #         "http://nginx-oboe/complex",
    #         name="oboe",
    #     )
    @task
    def request_otel(self):
        self.client.get(
            "http://nginx-otel/complex",
            name="otel",
        )
    @task
    def request_alpha(self):
        self.client.get(
            "http://nginx-alpha/complex",
            name="alpha",
        )
    # @task
    # def request_dev(self):
    #     self.client.get(
    #         "http://nginx-dev/complex",
    #         name="dev",
    #     )
    # @task
    # def request_metrics_endpoints(self):
    #     # Headers to execute more custom sampling logic if APM-instrumented
    #     # with new otel context for each request
    #     trace_id = "".join(random.choices("0123456789abcdef", k=32))
    #     span_id = "".join(random.choices("0123456789abcdef", k=16))
    #     tracestate_span_id = "".join(random.choices("0123456789abcdef", k=16))
    #     trace_flags = "01"
    #     traceparent = "00-{}-{}-{}".format(trace_id, span_id, trace_flags)
    #     tracestate = "sw={}-{}".format(tracestate_span_id, trace_flags)
    #     http_headers = {
    #         "traceparent": traceparent,
    #         "tracestate": tracestate,
    #         "x-trace-options": (
    #             "trigger-trace;custom-from=frank;foo=bar;"
    #             "sw-keys=custom-sw-from:herbert,baz:qux;ts={}".format(1234567890)
    #         ),
    #     }
    #     # self.client.get(
    #     #     "http://nginx-uninstrumented/complex",
    #     #     name="uninstrumented",
    #     #     headers=http_headers,
    #     # )
    #     # self.client.get(
    #     #     "http://nginx-oboe/complex",
    #     #     name="oboe",
    #     #     headers=http_headers,
    #     # )
    #     self.client.get(
    #         "http://nginx-otel/complex",
    #         name="otel",
    #         headers=http_headers,
    #     )
    #     self.client.get(
    #         "http://nginx-alpha/complex",
    #         name="alpha",
    #         headers=http_headers,
    #     )
    #     self.client.get(
    #         "http://nginx-dev/complex",
    #         name="dev",
    #         headers=http_headers,
    #     )


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
