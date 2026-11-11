---
lab4_comms:
  awareness: 2026-10-12T05:06:56Z
  detection: 2026-10-12T05:06:19Z
  classification: 2026-10-12T05:07:30Z
  nis2:
    early_warning_due: 2026-10-13T05:06:56Z
    notification_due: 2026-10-15T05:06:56Z
    notification_sent: 2026-10-12T06:00:00Z
    final_report_due: 2026-11-12T06:00:00Z
  ksc:
    early_warning_due: 2026-10-13T05:06:19Z
    notification_due: 2026-10-15T05:06:19Z
    notification_sent: 2026-10-12T06:00:00Z
    final_report_due: 2026-11-12T06:00:00Z
  dora:
    initial_due: 2026-10-12T09:07:30Z
    initial_sent: 2026-10-12T06:30:00Z
    intermediate_due: 2026-10-15T06:30:00Z
    intermediate_sent: 2026-10-14T06:30:00Z
    final_due: 2026-11-14T06:30:00Z
  log:
    - {at: 2026-10-12T06:00:00Z, to: "NIS2 competent authority", what: "Incident notification describing the significant checkout degradation and the known service impact."}
    - {at: 2026-10-12T06:00:00Z, to: "Polish KSC authority", what: "Incident notification after detection of the significant incident affecting checkout."}
    - {at: 2026-10-12T06:30:00Z, to: "DORA competent authority", what: "Initial notification of the ICT-related incident classified as major."}
    - {at: 2026-10-14T06:30:00Z, to: "DORA competent authority", what: "Intermediate report updating the authority on the incident, recovery and investigation."}
---
<!-- ai-generated: 100% - drafted with ChatGPT from the Lab 4 I-30 rules, incident timestamps and deadline arithmetic, then reviewed by the student -->

# Communications log: the regulators' clocks

## The three instants defended

For NIS2, I use `2026-10-12T05:06:56Z` as the awareness instant. This is the ticket acknowledgement time. By that point the detecting alert had already fired, the incident had been accepted by the on-call process, and the user-visible checkout impact was known. I therefore treat this as the point at which the organisation had become aware of a significant incident.

For the Polish KSC clock, I use `2026-10-12T05:06:19Z` as detection. This is the exact start of the firing run of `ShopCheckoutSlow`, which is also the detection instant recomputed from the Prometheus snapshot. The KSC wording uses the moment of detection rather than the later organisational-awareness instant.

For DORA, I use `2026-10-12T05:07:30Z` as classification as a major ICT-related incident. This is shortly after acknowledgement, once the severe checkout latency and the multi-service nature of the incident could reasonably have been assessed. It is deliberately later than both technical detection and organisational awareness because classification is an additional decision rather than the same event.

## The log

At 06:00 UTC I would send the NIS2 incident notification and the Polish KSC notification. Both are well before their respective 72-hour notification deadlines. Their final reports are therefore due one calendar month after that submission instant, at 06:00 UTC on 12 November 2026.

At 06:30 UTC I would submit the DORA initial notification. The incident was classified at 05:07:30 UTC, so the four-hour limit gives a deadline of 09:07:30 UTC. That is earlier than the alternative awareness-plus-24-hours cap, so 09:07:30 UTC is the applicable deadline.

The DORA intermediate report would be sent at 06:30 UTC on 14 October 2026. Because the initial notification was sent at 06:30 UTC on 12 October, the intermediate deadline is 72 elapsed hours later, at 06:30 UTC on 15 October. The final DORA report is then due one calendar month after the intermediate report was sent, at 06:30 UTC on 14 November 2026.
