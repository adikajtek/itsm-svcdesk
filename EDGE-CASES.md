---
lab2_edge_cases:
  E1: {rule: R-08, count: 3}
  E2: {rule: R-06, count: 2}
  E3: {rule: R-09, count: 4}
  E4: {rule: R-10, count: 4}
  E5: {rule: R-12, count: 1}
  E6: {rule: R-13, count: 11}
---
<!-- ai-generated: 100% - drafted with ChatGPT from METRIC-SPEC.md and the service's verified practice-fixture observations, then reviewed by the student -->

# Edge cases in the practice event log

## E1 - clock skew produces a negative lead time

- What the log contains: The practice log contains three deployment-to-commit lead-time pairs in which the commit timestamp is later than the successful deployment that carried it, producing a negative raw duration because of clock skew.

- What a default definition would have done: A naive implementation could discard those pairs as invalid or keep the negative durations, which would either hide delivered work or artificially reduce the reported lead-time median seen by the dashboard reader.

- Why the rule is defensible: R-08 keeps the observations but clamps negative lead times to zero and records them as anomalies. This preserves evidence that the change was delivered without allowing inconsistent clocks to create impossible negative delivery times.

## E2 - a revert of a revert

- What the log contains: The practice log contains two revert commits, including a revert chain where a commit reverts another commit that is itself a revert of an earlier change.

- What a default definition would have done: A simple implementation could count each revert commit as a separate change, which would inflate the number of changes and distort both throughput and change-level lead-time measurements for someone reading the dashboard.

- Why the rule is defensible: R-06 resolves reverts transitively to the original change identifier. A revert of a revert therefore remains part of the same underlying change instead of manufacturing additional units of work.

## E3 - a hotfix that never touched `main`

- What the log contains: The practice log contains four distinct commit shas carried by production deployments whose branch value is not `main`, representing work such as hotfixes delivered directly from another branch.

- What a default definition would have done: A definition that filters commits by `branch == "main"` would omit these real production changes, making delivery appear slower or smaller than it actually was and misleading the person relying on the dashboard.

- Why the rule is defensible: R-09 deliberately ignores branch names for delivery metrics. If a commit actually reached production, its branch label should not erase that fact from the measurements.

## E4 - a deployment with zero linked commits

- What the log contains: The practice fixture contains four production deployments whose `commits` arrays are empty, so they have no commit from which a change-lead-time pair can be constructed.

- What a default definition would have done: A naive implementation might discard these deployments entirely because no lead-time value can be calculated, which would incorrectly reduce deployment frequency and alter the denominators of failure and rework rates.

- Why the rule is defensible: R-10 gives an empty deployment no lead-time pair but still treats it as a real production deployment for the other metrics. The dashboard therefore reflects deployment activity without inventing commit information that the log does not contain.

## E5 - a deployment that failed and never recovered

- What the log contains: The practice fixture has one failed production deployment for which no usable recovery instant exists because its covering incident is unresolved or no resolved covering incident is available.

- What a default definition would have done: A simplistic definition might pretend that recovery happened at the end of the observation window or omit the failed deployment altogether, producing an invented recovery duration or hiding an unresolved operational problem.

- Why the rule is defensible: R-12 excludes an open failure from the recovery-time median but counts it explicitly in `counts.open_failures` and still includes the deployment in change fail rate. The dashboard therefore distinguishes unknown recovery time from successful recovery.

## E6 - overlapping incidents

- What the log contains: The practice event log contains eleven unordered pairs of incident intervals that overlap in time according to the interval rule defined in R-13.

- What a default definition would have done: A naive implementation could merge overlapping incidents into one interval or sum their wall-clock durations, which would change recovery measurements and obscure which failed deployment was actually covered by which recovery event.

- Why the rule is defensible: R-13 measures recovery per failed deployment and does not merge overlapping incidents. Counting overlaps separately as anomalies preserves the event relationships while preventing shared wall-clock time from being counted as invented recovery duration.

## Gaming demonstration

I improved `deployment_frequency_per_day` by exploiting R-11, which counts every production deployment in the observation window regardless of whether that deployment carries any commits. I delayed the original deployments until after the measurement window and added successful production deployments with empty commit lists. The reported deployment frequency therefore increased even though those extra deployments delivered no additional customer work.

This demonstrates how a target based on deployment frequency can create a harmful incentive. If a team is rewarded for increasing the number of production deployments, it can generate operationally valid but low-value or empty deployments while delaying the real changes that users are waiting for. The metric improves while the underlying delivery system becomes worse.

A team, engineering manager, or delivery organisation evaluated primarily on deployment frequency could be rewarded for this behaviour because the dashboard reports a higher deployment rate. The customer would experience the opposite outcome: the original changes are delivered later or not delivered inside the measurement window. R-21 exposes that discrepancy by evaluating the ground truth of the base work rather than trusting the improved dashboard metric.
