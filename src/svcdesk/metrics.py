# ai-generated: 100% - drafted with ChatGPT from METRIC-SPEC.md and reviewed by the student

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


UTC = timezone.utc


class MetricError(ValueError):
    pass


def parse_instant(value: Any) -> datetime:
    if not isinstance(value, str):
        raise MetricError("timestamp must be a string")

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise MetricError("invalid RFC 3339 timestamp")

    if parsed.tzinfo is None:
        raise MetricError("timestamp must include an offset")

    return parsed.astimezone(UTC)


def format_instant(value: datetime) -> str:
    value = value.astimezone(UTC).replace(microsecond=0)
    return value.isoformat().replace("+00:00", "Z")


def decimal_seconds(delta) -> Decimal:
    return (
        Decimal(delta.days * 86400 + delta.seconds)
        + Decimal(delta.microseconds) / Decimal(1_000_000)
    )


def round_seconds(value: Decimal) -> int:
    return int(
        value.quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )


def round_six(value: Decimal) -> float:
    return float(
        value.quantize(
            Decimal("0.000001"),
            rounding=ROUND_HALF_UP,
        )
    )


def median_seconds(values: list[Decimal]) -> int | None:
    if not values:
        return None

    values = sorted(values)
    count = len(values)

    if count % 2:
        median = values[count // 2]
    else:
        median = (
            values[count // 2 - 1] + values[count // 2]
        ) / Decimal(2)

    return round_seconds(median)


def compute_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise MetricError("request body must be an object")

    window = payload.get("window")
    if not isinstance(window, dict):
        raise MetricError("window is required")

    window_from = parse_instant(window.get("from"))
    window_to = parse_instant(window.get("to"))

    if window_to <= window_from:
        raise MetricError("window.to must be after window.from")

    raw_events = payload.get("events")
    if not isinstance(raw_events, list):
        raise MetricError("events must be an array")

    events: list[dict[str, Any]] = []
    seen_event_ids: set[str] = set()

    # R-05: first event_id occurrence wins.
    for raw in raw_events:
        if not isinstance(raw, dict):
            raise MetricError("every event must be an object")

        event_id = raw.get("event_id")

        if (
            not isinstance(event_id, str)
            or not 1 <= len(event_id) <= 64
        ):
            raise MetricError("invalid event_id")

        if event_id in seen_event_ids:
            continue

        seen_event_ids.add(event_id)

        event_type = raw.get("type")
        if event_type not in {"commit", "deployment", "incident"}:
            raise MetricError("invalid event type")

        event = dict(raw)
        event["_at"] = parse_instant(event.get("at"))

        if event_type == "commit":
            sha = event.get("sha")
            branch = event.get("branch")
            change_id = event.get("change_id")
            reverts = event.get("reverts")

            if not isinstance(sha, str) or not sha:
                raise MetricError("invalid commit sha")

            if not isinstance(branch, str):
                raise MetricError("invalid commit branch")

            if reverts is not None and (
                not isinstance(reverts, str) or not reverts
            ):
                raise MetricError("invalid reverts value")

            if change_id is not None and (
                not isinstance(change_id, str) or not change_id
            ):
                raise MetricError("invalid change_id")

            # A normal commit has change_id and no reverts.
            # A revert has reverts and no change_id.
            if (reverts is None) != (change_id is not None):
                raise MetricError(
                    "commit change_id/reverts combination is invalid"
                )

        elif event_type == "deployment":
            deployment_id = event.get("deployment_id")
            environment = event.get("environment")
            outcome = event.get("outcome")
            commits = event.get("commits")
            unplanned = event.get("unplanned")
            caused_by = event.get("caused_by")

            if not isinstance(deployment_id, str) or not deployment_id:
                raise MetricError("invalid deployment_id")

            if not isinstance(environment, str):
                raise MetricError("invalid environment")

            if outcome not in {"success", "failure"}:
                raise MetricError("invalid deployment outcome")

            if not isinstance(commits, list) or any(
                not isinstance(sha, str) or not sha
                for sha in commits
            ):
                raise MetricError("invalid deployment commits")

            if type(unplanned) is not bool:
                raise MetricError("invalid unplanned value")

            if caused_by is not None and (
                not isinstance(caused_by, str) or not caused_by
            ):
                raise MetricError("invalid caused_by value")

        else:
            incident_id = event.get("incident_id")
            phase = event.get("phase")
            deployments = event.get("deployments")

            if not isinstance(incident_id, str) or not incident_id:
                raise MetricError("invalid incident_id")

            if phase not in {"opened", "resolved"}:
                raise MetricError("invalid incident phase")

            if not isinstance(deployments, list) or any(
                not isinstance(dep_id, str) or not dep_id
                for dep_id in deployments
            ):
                raise MetricError("invalid incident deployments")

        events.append(event)

    commits: dict[str, dict[str, Any]] = {}
    deployments: dict[str, dict[str, Any]] = {}
    incident_events: dict[tuple[str, str], dict[str, Any]] = {}

    for event in events:
        if event["type"] == "commit":
            sha = event["sha"]

            if sha in commits:
                raise MetricError("duplicate commit sha")

            commits[sha] = event

        elif event["type"] == "deployment":
            deployment_id = event["deployment_id"]

            if deployment_id in deployments:
                raise MetricError("duplicate deployment_id")

            deployments[deployment_id] = event

        else:
            key = (event["incident_id"], event["phase"])

            if key in incident_events:
                raise MetricError("duplicate incident phase")

            incident_events[key] = event

    incident_ids = {
        incident_id
        for incident_id, _ in incident_events
    }

    # Well-formedness reference checks.
    for commit in commits.values():
        reverts = commit["reverts"]

        if reverts is not None and reverts not in commits:
            raise MetricError("reverts references an unknown sha")

    for deployment in deployments.values():
        for sha in deployment["commits"]:
            if sha not in commits:
                raise MetricError(
                    "deployment references an unknown commit"
                )

        caused_by = deployment["caused_by"]

        if (
            caused_by is not None
            and caused_by not in incident_ids
        ):
            raise MetricError(
                "caused_by references an unknown incident"
            )

    for (incident_id, phase), event in incident_events.items():
        for deployment_id in event["deployments"]:
            if deployment_id not in deployments:
                raise MetricError(
                    "incident references an unknown deployment"
                )

        if (
            phase == "resolved"
            and (incident_id, "opened") not in incident_events
        ):
            raise MetricError(
                "resolved incident has no opened event"
            )

    # R-06: resolve revert chains transitively to the original change.
    change_by_sha: dict[str, str] = {}

    def resolve_change(
        sha: str,
        stack: set[str] | None = None,
    ) -> str:
        if sha in change_by_sha:
            return change_by_sha[sha]

        if stack is None:
            stack = set()

        if sha in stack:
            raise MetricError("revert cycle detected")

        stack.add(sha)
        commit = commits[sha]

        if commit["reverts"] is None:
            change_id = commit["change_id"]
        else:
            change_id = resolve_change(
                commit["reverts"],
                stack,
            )

        stack.remove(sha)
        change_by_sha[sha] = change_id
        return change_id

    for sha in commits:
        resolve_change(sha)

    all_changes = set(change_by_sha.values())

    # R-07: earliest commit instant for each resolved change.
    first_commit_by_change: dict[str, datetime] = {}

    for sha, commit in commits.items():
        change_id = change_by_sha[sha]
        current = first_commit_by_change.get(change_id)

        if current is None or commit["_at"] < current:
            first_commit_by_change[change_id] = commit["_at"]

    # R-01 and R-02.
    scoped_deployments = [
        deployment
        for deployment in deployments.values()
        if deployment["environment"] == "production"
        and window_from <= deployment["_at"] < window_to
    ]

    scoped_deployments.sort(
        key=lambda deployment: (
            deployment["_at"],
            deployment["deployment_id"],
            deployment["event_id"],
        )
    )

    successful = [
        deployment
        for deployment in scoped_deployments
        if deployment["outcome"] == "success"
    ]

    failed = [
        deployment
        for deployment in scoped_deployments
        if deployment["outcome"] == "failure"
    ]

    # R-08: first successful production deployment per commit.
    lead_times: list[Decimal] = []
    negative_lead_time_pairs = 0
    delivered_shas: set[str] = set()

    for deployment in successful:
        for sha in deployment["commits"]:
            if sha in delivered_shas:
                continue

            delivered_shas.add(sha)

            duration = decimal_seconds(
                deployment["_at"] - commits[sha]["_at"]
            )

            if duration < 0:
                negative_lead_time_pairs += 1
                duration = Decimal(0)

            lead_times.append(duration)

    # R-09.
    commits_never_on_main = {
        sha
        for deployment in scoped_deployments
        for sha in deployment["commits"]
        if commits[sha]["branch"] != "main"
    }

    # R-10.
    deployments_without_commits = sum(
        1
        for deployment in scoped_deployments
        if not deployment["commits"]
    )

    # Build incident intervals and coverage.
    incidents: dict[str, dict[str, Any]] = {}

    for incident_id in incident_ids:
        opened_event = incident_events.get(
            (incident_id, "opened")
        )
        resolved_event = incident_events.get(
            (incident_id, "resolved")
        )

        covered: set[str] = set()

        if opened_event is not None:
            covered.update(opened_event["deployments"])

        if resolved_event is not None:
            covered.update(resolved_event["deployments"])

        incidents[incident_id] = {
            "opened": (
                opened_event["_at"]
                if opened_event is not None
                else None
            ),
            "resolved": (
                resolved_event["_at"]
                if resolved_event is not None
                else None
            ),
            "deployments": covered,
        }

    # R-12: recovery per failed deployment.
    recovery_times: list[Decimal] = []
    open_failures = 0

    for deployment in failed:
        candidates = [
            (
                incident["opened"],
                incident_id,
                incident,
            )
            for incident_id, incident in incidents.items()
            if incident["opened"] is not None
            and deployment["deployment_id"]
            in incident["deployments"]
        ]

        if not candidates:
            open_failures += 1
            continue

        _, _, covering = min(
            candidates,
            key=lambda item: (
                item[0],
                item[1],
            ),
        )

        if covering["resolved"] is None:
            open_failures += 1
            continue

        duration = decimal_seconds(
            covering["resolved"] - deployment["_at"]
        )

        if duration < 0:
            duration = Decimal(0)

        recovery_times.append(duration)

    # R-13: overlapping incident pairs.
    intervals: list[tuple[str, datetime, datetime]] = []

    for incident_id, incident in incidents.items():
        if incident["opened"] is None:
            continue

        end = (
            incident["resolved"]
            if incident["resolved"] is not None
            else window_to
        )

        intervals.append(
            (
                incident_id,
                incident["opened"],
                end,
            )
        )

    overlapping_incident_pairs = 0

    for left_index in range(len(intervals)):
        for right_index in range(
            left_index + 1,
            len(intervals),
        ):
            _, left_start, left_end = intervals[left_index]
            _, right_start, right_end = intervals[right_index]

            if (
                left_start < right_end
                and right_start < left_end
            ):
                overlapping_incident_pairs += 1

    # R-16/R-17 ground truth: one value per change.
    first_success_by_change: dict[str, datetime] = {}

    for deployment in successful:
        for sha in deployment["commits"]:
            change_id = change_by_sha[sha]
            current = first_success_by_change.get(change_id)

            if (
                current is None
                or deployment["_at"] < current
            ):
                first_success_by_change[
                    change_id
                ] = deployment["_at"]

    true_change_lead_times: list[Decimal] = []

    for change_id, deployment_at in (
        first_success_by_change.items()
    ):
        duration = decimal_seconds(
            deployment_at
            - first_commit_by_change[change_id]
        )

        if duration < 0:
            duration = Decimal(0)

        true_change_lead_times.append(duration)

    deployment_count = len(scoped_deployments)

    window_days = (
        decimal_seconds(window_to - window_from)
        / Decimal(86400)
    )

    deployment_frequency = round_six(
        Decimal(deployment_count) / window_days
    )

    change_fail_rate = (
        round_six(
            Decimal(len(failed))
            / Decimal(deployment_count)
        )
        if deployment_count
        else None
    )

    rework_deployments = sum(
        1
        for deployment in scoped_deployments
        if deployment["unplanned"] is True
        and deployment["caused_by"] is not None
    )

    deployment_rework_rate = (
        round_six(
            Decimal(rework_deployments)
            / Decimal(deployment_count)
        )
        if deployment_count
        else None
    )

    return {
        "spec_version": "1.0.0",
        "window": {
            "from": format_instant(window_from),
            "to": format_instant(window_to),
        },
        "deployment_frequency_per_day": deployment_frequency,
        "change_lead_time_seconds_p50": median_seconds(
            lead_times
        ),
        "failed_deployment_recovery_time_seconds_p50":
            median_seconds(recovery_times),
        "change_fail_rate": change_fail_rate,
        "deployment_rework_rate": deployment_rework_rate,
        "counts": {
            "deployments": deployment_count,
            "successful_deployments": len(successful),
            "failed_deployments": len(failed),
            "recovered_failures": len(recovery_times),
            "open_failures": open_failures,
            "rework_deployments": rework_deployments,
            "lead_time_pairs": len(lead_times),
            "changes": len(all_changes),
        },
        "anomalies": {
            "negative_lead_time_pairs":
                negative_lead_time_pairs,
            "deployments_without_commits":
                deployments_without_commits,
            "commits_never_on_main":
                len(commits_never_on_main),
            "revert_chains_collapsed": sum(
                1
                for commit in commits.values()
                if commit["reverts"] is not None
            ),
            "overlapping_incident_pairs":
                overlapping_incident_pairs,
        },
        "ground_truth": {
            "changes_delivered":
                len(first_success_by_change),
            "true_change_lead_time_seconds_p50":
                median_seconds(true_change_lead_times),
        },
    }
