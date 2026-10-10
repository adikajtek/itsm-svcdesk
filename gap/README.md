<!-- ai-generated: 100% - drafted with ChatGPT from my measured Toxiproxy client/server latency gap and reviewed by the student -->

# Client-server latency gap

I placed Toxiproxy in front of `svcdesk` and configured a downstream latency toxic with 100 ms latency and 10 ms jitter. During the measurement through the proxy, the client's p99 was 0.2298 seconds, while the p99 calculated from the server-side `http_server_request_duration_seconds` histogram was 0.1209 seconds. The measured gap was therefore 0.1089 seconds.

The difference exists because the two measurements have different boundaries. The client latency includes the extra delay introduced by Toxiproxy on the downstream path between the service and the client. The server histogram measures the time spent handling the HTTP request inside `svcdesk`; it does not include the additional delay that the proxy applies after the response leaves the application. This demonstrates why a server-side request-duration histogram cannot, by itself, represent all latency experienced by a client. Network components and proxies can add delay outside the service's own measured request lifetime.
