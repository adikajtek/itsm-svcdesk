---
lab4_postmortem:
  ticket: "3ba75e92-1b55-483b-a69e-6097c02b182c"
  detecting_alert: ShopCheckoutSlow
  onset: 2026-10-12T05:01:00Z
  detection: 2026-10-12T05:06:19Z
  acknowledgement: 2026-10-12T05:06:56Z
  recovery: 2026-10-12T05:08:19Z
  mttd_seconds: 319
  mtta_seconds: 37
  mttr_seconds: 439
  identified_flags: [adFailure, intlShippingSlowdown]
---
<!-- ai-generated: 80% - drafted with ChatGPT from the recorded Lab 4 incident, measured Prometheus evidence and checker recomputation, then reviewed by the student -->

# Postmortem: Checkout latency during shipping slowdown and concurrent advertisement failures

## Date

The incident occurred on 12 October 2026, and this postmortem was prepared after reviewing the recorded incident, its Prometheus snapshot, ticket and investigation evidence.

## Authors

This postmortem was prepared by the student acting as the on-call engineer for the recorded Laboratory 4 incident and reviewing the available operational evidence.

## Status

Complete for the incident investigation, with follow-up action items recorded below and the underlying problem record retained for further preventive work.

## Summary

At 05:01:00 UTC the recorded shop entered a seeded fault condition. Checkout became severely slower for users and the `ShopCheckoutSlow` alert began firing at 05:06:19 UTC. The incident was acknowledged at 05:06:56 UTC and the detecting alert recovered at 05:08:19 UTC.

The observable evidence supports two seeded conditions with high confidence: `intlShippingSlowdown`, which increased shipping and checkout latency, and `adFailure`, which caused concurrent advertisement request failures. The third resource-class flag is intentionally not identified because the available metrics reviewed here do not support a sufficiently defensible distinction between the remaining resource faults.

## Impact

Users experienced severely increased checkout latency. At 05:06:30 UTC, checkout server-span p99 latency was approximately 8800 ms and shipping server-span p99 latency was approximately 7700 ms.

The latency measurement was derived from:

`histogram_quantile(0.99, sum by(service_name,le) (rate(traces_span_metrics_duration_milliseconds_bucket{span_kind="SPAN_KIND_SERVER"}[5m])))`

evaluated during the incident. It returned approximately 8800 ms for `checkout` and 7700 ms for `shipping`.

Advertisement requests were also failing during the incident. The server-span error-ratio query:

`sum by(service_name) (rate(traces_span_metrics_calls_total{span_kind="SPAN_KIND_SERVER",status_code="STATUS_CODE_ERROR"}[5m])) / sum by(service_name) (rate(traces_span_metrics_calls_total{span_kind="SPAN_KIND_SERVER"}[5m]))`

returned approximately 0.0476 for `ad` at 05:06:30 UTC, meaning roughly 4.76% of the observed ad server spans in that window were errors.

The incident lasted 439 seconds from onset to recovery. Detection occurred after 319 seconds, and acknowledgement followed the detecting alert after another 37 seconds.

## Root Causes

The first identified seeded condition was `intlShippingSlowdown`. Shipping p99 latency rose to approximately 7.7 seconds during the incident, while checkout p99 reached approximately 8.8 seconds. This is consistent with a shipping slowdown propagating into the checkout path.

The second identified seeded condition was `adFailure`. The `ad` service showed an approximately 4.76% server-span error ratio during the incident, while the evidence reviewed did not show a comparable payment or product-catalog error signal.

The resource-class condition was not identified with sufficient confidence from the evidence reviewed, so it is not named as an identified flag rather than presenting an unsupported conclusion as ground truth.

## Trigger

The incident was triggered by the recorded fault injector at the recomputed onset time of 05:01:00 UTC. The injected conditions then affected multiple parts of the shop until the recorded operator mitigated the active fault conditions.

## Resolution

Service recovery was observed at 05:08:19 UTC, when the first firing run of the detecting alert ended. On the recorded path the Prometheus snapshot exposes the resulting service behaviour and aggregate fault activity but does not expose the individual flag-switch operations or their exact order.

The operational workaround was therefore the removal of the active seeded fault conditions. For the two conditions identified from telemetry, this corresponds to disabling the shipping slowdown and advertisement failure conditions. The exact order of the recorded operator's individual flag changes is not asserted because it cannot be reconstructed reliably from the reviewed metrics.

## Detection

The incident was detected by the `ShopCheckoutSlow` alert at 05:06:19 UTC, 319 seconds after the fault onset. The alert represents a user-visible symptom rather than an internal implementation cause.

The supporting latency query is:

`histogram_quantile(0.99, sum by(le) (rate(traces_span_metrics_duration_milliseconds_bucket{service_name="checkout",span_kind="SPAN_KIND_SERVER"}[5m]))) > 2000`

The recorded incident was acknowledged 37 seconds after detection. Without the symptom alert, the degradation would have depended on a user complaint or manual observation of checkout latency.

## Action Items

The following actions aim to shorten detection and recovery while reducing the probability that equivalent faults create the same user impact.

| Action Item | Type | Owner | Bug |
|---|---|---|---|
| Add a dedicated shipping-latency diagnostic panel and runbook query so an on-call engineer can distinguish downstream shipping latency from checkout-local latency immediately after a page. | mitigate | SRE team | ITSM-41 |
| Add automated tests for checkout behaviour when the shipping dependency becomes 5-10 seconds slower, including a defined timeout and graceful failure behaviour. | prevent | Checkout team | ITSM-42 |
| Document a standard incident investigation sequence that compares checkout latency with downstream service latency and recent error-rate changes before forming a root-cause conclusion. | process | SRE team | ITSM-43 |

## Lessons Learned

### What went well

The symptom-based `ShopCheckoutSlow` alert successfully detected a user-visible degradation and reached the incident workflow. The ticket was acknowledged only 37 seconds after the detecting alert fired.

The Prometheus snapshot retained enough data to distinguish the major shipping latency signal from unrelated traffic changes and to identify the concurrent advertisement error condition.

### What went wrong

Detection required 319 seconds after onset, so users experienced degraded checkout behaviour for several minutes before the alert fired. The available telemetry also made the resource-class fault harder to distinguish confidently than the shipping and advertisement conditions.

The recorded investigator concentrated heavily on checkout-local spans and did not reliably isolate the clearly elevated shipping latency visible in the service-level histogram evidence.

### Where we got lucky

The shipping slowdown produced a strong, measurable latency signal that could be separated from load because frontend request rates stayed close to their healthy baseline. The incident also recovered quickly after detection, limiting the overall recorded duration to 439 seconds.

## Timeline

- 04:56:00 UTC — Healthy-baseline traffic showed approximately 4.18 frontend server calls per second and 2.17 frontend-proxy calls per second; no evidence of the later x15 traffic pattern was present.
- 05:01:00 UTC — Fault onset recorded in the Prometheus snapshot.
- 05:06:19 UTC — `ShopCheckoutSlow` began its detecting firing run. MTTD was 319 seconds.
- 05:06:30 UTC — Investigation evidence showed checkout p99 at approximately 8.8 seconds and shipping p99 at approximately 7.7 seconds. Frontend request rate remained approximately 4.02 calls per second, ruling against a large homepage traffic flood.
- 05:06:30 UTC — The ad server-span error ratio was approximately 4.76%, supporting the concurrent `adFailure` identification.
- 05:06:56 UTC — The P1 incident ticket was acknowledged. MTTA was 37 seconds.
- 05:08:19 UTC — The detecting alert's first firing run ended and service was considered recovered. MTTR from onset was 439 seconds.

## Supporting information

The primary evidence is `incident/tsdb-snapshot.tar.gz`, `incident/ticket.json`, the recorded investigator transcript in `ai-rca/transcript.md`, and the recomputation produced by `./itsmlab.sh incident 4`.

The recomputation established onset `2026-10-12T05:01:00Z`, detection `2026-10-12T05:06:19Z`, acknowledgement `2026-10-12T05:06:56Z`, recovery `2026-10-12T05:08:19Z`, MTTD 319 seconds, MTTA 37 seconds and MTTR 439 seconds.

The incident investigation also compared frontend request rates before and during the incident. The baseline was approximately 4.18 calls per second for `frontend`, while the incident value was approximately 4.02 calls per second, providing evidence against `loadGeneratorFloodHomepage`.

## Problem record

- Incident record: P1 ticket `3ba75e92-1b55-483b-a69e-6097c02b182c` records the user-visible checkout degradation and acknowledgement of the incident.
- Root cause: Multiple seeded fault conditions affected the shop; telemetry strongly identifies `intlShippingSlowdown` and concurrent `adFailure`.
- Known error: Checkout latency can inherit multi-second latency from the shipping dependency, while concurrent failures in another service can complicate incident diagnosis.
- Workaround: Disable the active seeded fault conditions to restore normal service, while using downstream latency and error-rate comparisons to identify the affected dependencies.
