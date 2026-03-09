<?php

use OpenTelemetry\API\Trace\TracerInterface;
use OpenTelemetry\SDK\Metrics\MeterProviderInterface;
use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;
use Slim\Factory\AppFactory;
use GuzzleHttp\Client;
use Monolog\Level;
use Monolog\Logger;
use Monolog\Handler\ErrorLogHandler;
use OpenTelemetry\API\Globals;
use OpenTelemetry\Contrib\Logs\Monolog\Handler;

require __DIR__ . '/vendor/autoload.php';

$handler = new Handler(
    OpenTelemetry\API\Globals::loggerProvider(),
    Level::Info,
    true,
);

$logger = new Logger('app');
$logger->pushHandler($handler);

$tracer = Globals::tracerProvider()->getTracer('app');
$global_meter_provider = Globals::meterProvider();
$my_meter = $global_meter_provider->getMeter('jerry-test-meter', '123');
$test_counter_a = $my_meter->createCounter(
    'trace.service.jerry-test-counter-a',
    'SDK-defined counter by user\'s service');
$test_counter_b = $my_meter->createCounter(
    'trace.service.jerry-test-counter-b',
    'SDK-defined counter by user\'s service');
$test_counter_c = $my_meter->createCounter(
    'trace.service.jerry-test-counter-c',
    'SDK-defined counter by user\'s service');
$test_histogram = $my_meter->createHistogram(
    'trace.service.jerry-test-histogram',
    'ms',
    'SDK-defined histogram by user\'s service');

$app = AppFactory::create();

$app->get('/healthcheck', function (Request $request, Response $response) {
    $response->getBody()->write('Yay healthy');
    return $response;
});

$app->get('/request', function (Request $request, Response $response) use ($logger) {
    $logger->info('Sending request to example.com');
    $client = new Client();
    $resp = $client->request('GET', 'http://example.com');
    $logger->info('Received response from example.com');
    $response->getBody()->write($resp->getBody()->getContents());
    return $response;
});

$app->get('/metrics', function (Request $request, Response $response) use ($logger, $test_counter_a, $test_counter_b, $test_counter_c, $test_histogram, $global_meter_provider) {
    # here for predictable response_time metrics
    sleep(1);
    $logger->info('Incrementing counter, recording histogram');
    $test_counter_a->add(1);
    $test_counter_b->add(1);
    $test_counter_c->add(1);
    $test_histogram->record(
        500,
        [
            'sw.transaction' => 'jerry-test'
        ]
    );
    if ($global_meter_provider instanceof MeterProviderInterface) {
        $global_meter_provider->forceFlush();
    }
    $response->getBody()->write('Finished adding and recording');
    return $response;
});

$app->get('/logs', function (Request $request, Response $response) use ($logger) {
    $logger->error('An error log by app-side app logger');
    $logger->warning('A warning log by app-side app logger');
    $logger->info('An info log by app-side app logger');
    $response->getBody()->write('Done');
    return $response;
});

$app->get('/sdk', function (Request $request, Response $response) use ($logger, $tracer) {
    $main = $tracer->spanBuilder('my_sdk_manual_span')->startSpan();
    $mainScope = $main->activate();
    $client = new Client();
    $resp = $client->request('GET', 'http://example.com');
    $logger->debug('Made manual span then request to example.com');
    $response->getBody()->write('Done');
    $mainScope->detach();
    $main->end();
    return $response;
});

function make_ten_spans(TracerInterface $tracer)
{
    $manual_01 = $tracer->spanBuilder('manual_01')->startSpan();
    $manual_01Scope = $manual_01->activate();
    $manual_02 = $tracer->spanBuilder('manual_02')->startSpan();
    $manual_02Scope = $manual_02->activate();
    $manual_03 = $tracer->spanBuilder('manual_03')->startSpan();
    $manual_03Scope = $manual_03->activate();
    $manual_04 = $tracer->spanBuilder('manual_04')->startSpan();
    $manual_04Scope = $manual_04->activate();
    $manual_05 = $tracer->spanBuilder('manual_05')->startSpan();
    $manual_05Scope = $manual_05->activate();
    $manual_06 = $tracer->spanBuilder('manual_06')->startSpan();
    $manual_06Scope = $manual_06->activate();
    $manual_07 = $tracer->spanBuilder('manual_07')->startSpan();
    $manual_07Scope = $manual_07->activate();
    $manual_08 = $tracer->spanBuilder('manual_08')->startSpan();
    $manual_08Scope = $manual_08->activate();
    $manual_09 = $tracer->spanBuilder('manual_09')->startSpan();
    $manual_09Scope = $manual_09->activate();
    $manual_10 = $tracer->spanBuilder('manual_10')->startSpan();
    $manual_10Scope = $manual_10->activate();
    print('Made 10 Otel spans');
    $manual_10Scope->detach();
    $manual_10->end();
    $manual_09Scope->detach();
    $manual_09->end();
    $manual_08Scope->detach();
    $manual_08->end();
    $manual_07Scope->detach();
    $manual_07->end();
    $manual_06Scope->detach();
    $manual_06->end();
    $manual_05Scope->detach();
    $manual_05->end();
    $manual_04Scope->detach();
    $manual_04->end();
    $manual_03Scope->detach();
    $manual_03->end();
    $manual_02Scope->detach();
    $manual_02->end();
    $manual_01Scope->detach();
    $manual_01->end();
}

$app->get('/complex', function (Request $request, Response $response) use ($logger, $test_counter_a, $test_counter_b, $test_counter_c, $test_histogram, $global_meter_provider, $tracer) {
    if (class_exists('\Solarwinds\ApmPhp\API\TransactionName')) {
        \Solarwinds\ApmPhp\API\TransactionName::set('complex_trace');
    }
    for ($i = 0; $i < 10; $i++) {
         make_ten_spans($tracer);
    }
    $logger->info('Incrementing counter, recording histogram');
    $test_counter_a->add(1);
    $test_counter_b->add(1);
    $test_counter_c->add(1);
    $test_histogram->record(
        500,
        [
            'sw.transaction' => 'jerry-test'
        ]
    );

    $response->getBody()->write('Done');
    return $response;
});

$app->run();
