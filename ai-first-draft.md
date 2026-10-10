---
lab3_first_draft:
  source: ai
  tool: "ChatGPT GPT-5.6 Sol, ChatGPT, 10 October 2026"
  ladder: [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.125, 0.15, 0.175, 0.2, 0.225, 0.25, 0.3, 0.4, 0.5, 0.75, 1.0, 1.5, 2.5]
  verdict: TODO
  evidence: {p99_seconds: TODO, bucket: [TODO, TODO], relative_width: TODO}
lab3_flawed_ladder:
  verdict: refuted
  evidence: {p99_seconds: TODO, bucket: [TODO, TODO], relative_width: TODO}
---
<!-- ai-generated: 100% - the first draft was produced by ChatGPT before measurement and will be evaluated against the measured profile -->

# The assistant's first draft, and two verdicts

## Prompt

Without seeing any measurements for my FastAPI service, propose Prometheus histogram bucket boundaries in seconds for GET /kb/search and one multi-window burn-rate alert rule. The route calls an upstream knowledge-base service on every request. I want a practical first draft only; do not assume a measured p99.

## Answer

For a first draft, I would use this histogram ladder in seconds:

[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.125, 0.15, 0.175, 0.2, 0.225, 0.25, 0.3, 0.4, 0.5, 0.75, 1.0, 1.5, 2.5]

It gives relatively fine resolution between 100 ms and 300 ms while retaining coverage for both very fast responses and a multi-second tail. Because I have not seen measurements, I would treat this only as a starting point and redesign the ladder after measuring the real distribution.

For an availability SLO with objective 0.99, a first multi-window fast-burn alert could use burn rate 14.4 with a 1h long window and a 5m short window. The alert should require both windows to exceed 14.4 * (1 - 0.99), filter specifically on http_route="/kb/search", and calculate bad requests from 5xx responses divided by all valid /kb/search requests. I would give it a short for-duration such as 2m and severity P1. The exact SLO objective, windows and final alert should still be validated against the measured service behaviour and the laboratory specification.

## Verdict on the draft ladder

TODO after measurement.

## The draft alert rule

TODO after the SLO and final alert design.

## Verdict on the instructor's flawed ladder

TODO after measurement.
