<!-- ai-generated: 100% - drafted with ChatGPT from REQUIREMENTS.md, API.md and CHECKS.md and reviewed by the student -->

# svcdesk Lab 1 Specification

## 1. Purpose

The `svcdesk` service provides an HTTP/JSON service-desk API on port 8080. It manages tickets, computes their priorities, tracks their state, calculates SLA deadlines, reports SLA breaches and supports deterministic time during automated tests.

This specification implements requirements R-01 through R-25 while explicitly resolving the three contradictory requirement pairs described by the course material.

## 2. Conflict resolutions

### C1 — SLA clock for P1: `wallclock`

P1 acknowledgement and resolution targets use wall-clock time.

This resolves the conflict between R-13 and R-14 by keeping the business-hours rule for P2, P3 and P4 while applying the explicit around-the-clock requirement of R-14 to P1.

Therefore:

* P1 acknowledgement is due 15 minutes after creation.
* P1 resolution is due 4 hours after creation.
* P1 SLA time never pauses outside business hours.
* P2, P3 and P4 continue to use the business-hours clock.

### C2 — Closed tickets and reopening: `immutable`

A resolved ticket may be reopened within seven days of its resolution, but a closed ticket is immutable and may not be reopened.

This resolves the conflict between R-09 and R-10 by retaining the reopening rule for resolved tickets while retaining R-09 for tickets that have already reached the `closed` state.

Further work concerning a closed ticket must use a new ticket, optionally referencing the original ticket through `related_to`.

### C3 — VIP reporters and priority: `matrix`

Priority is determined only from impact and urgency according to the priority matrix.

The `reporter.vip` field is stored, but it does not alter the computed priority.

This resolves the conflict between R-05 and R-06 in favour of R-05. A VIP ticket with impact 3 and urgency 3 therefore remains P4. A VIP ticket whose matrix priority is P1 or P2 remains P1 or P2 respectively.

## 3. HTTP interface

All request and response bodies use JSON.

The service provides:

* `GET /health`
* `POST /tickets`
* `GET /tickets`
* `GET /tickets/{id}`
* `GET /tickets/{id}/sla`
* `POST /tickets/{id}/ack`
* `POST /tickets/{id}/start`
* `POST /tickets/{id}/resolve`
* `POST /tickets/{id}/close`
* `POST /tickets/{id}/reopen`

`GET /health` returns HTTP 200 and at least:

```json
{"status": "ok", "service": "svcdesk"}
```

Unknown paths return HTTP 404 with a JSON response.

## 4. Ticket data

Each ticket contains:

* a unique, opaque, non-empty server-generated `id`;
* `title`, containing 1 to 200 characters;
* optional `description`, defaulting to an empty string, with a maximum of 4000 characters;
* a reporter with a required `name`, optional `email`, and optional `vip` flag defaulting to false;
* integer `impact` in the range 1 through 3;
* integer `urgency` in the range 1 through 3;
* server-computed `priority`;
* server-managed `state`;
* `created_at`;
* optional `acknowledged_at`, `resolved_at` and `closed_at`;
* optional `related_to`;
* an `sla` object containing `ack_due_at` and `resolve_due_at`.

Client-supplied server-owned fields such as `id`, `priority`, `state`, timestamps and `sla` are ignored. Unknown request fields are also ignored.

All timestamps returned by the service are RFC 3339 instants. The implementation will return UTC timestamps using the `Z` suffix.

## 5. Priority calculation

The priority matrix is:

| Impact | Urgency 1 | Urgency 2 | Urgency 3 |
| ------ | --------- | --------- | --------- |
| 1      | P1        | P2        | P3        |
| 2      | P2        | P3        | P4        |
| 3      | P3        | P4        | P4        |

Under decision C3=`matrix`, `reporter.vip` never modifies this result.

A priority supplied by the client is ignored.

## 6. Validation

Creating a ticket requires:

* a valid title;
* a reporter containing a valid name;
* integer impact from 1 to 3;
* integer urgency from 1 to 3.

Invalid input returns HTTP 400 or 422 with a JSON body containing a top-level `error` object.

A missing title, a title longer than 200 characters, an invalid impact, an invalid urgency or a malformed test clock must therefore be rejected.

Unknown ticket identifiers return HTTP 404 with a JSON body containing a top-level `error` object.

## 7. Ticket state machine

A new ticket starts in state `new`.

The valid forward transitions are:

`new -> acknowledged -> in_progress -> resolved -> closed`

The actions behave as follows:

* `ack` changes `new` to `acknowledged` and stores `acknowledged_at`.
* `start` changes `acknowledged` to `in_progress`.
* `resolve` changes `in_progress` to `resolved` and stores `resolved_at`.
* `close` changes `resolved` to `closed` and stores `closed_at`.

Any unsupported transition returns HTTP 409.

Examples include acknowledging a ticket twice, starting a new ticket, resolving a new or merely acknowledged ticket, or closing a new ticket.

## 8. Reopening

A ticket in state `resolved` may be reopened while:

`now <= resolved_at + 7 days`

Successful reopening changes the ticket to `in_progress`.

A reopen occurring later than seven days after `resolved_at` returns HTTP 409.

Under C2=`immutable`, tickets in state `closed` always return HTTP 409 when `/reopen` is requested, regardless of how recently they were closed.

Reopening does not change the original SLA resolution deadline.

When a resolved ticket is reopened, it is considered unresolved again for SLA breach calculations.

## 9. SLA targets

The SLA targets are:

| Priority | Acknowledge | Resolve  |
| -------- | ----------- | -------- |
| P1       | 15 minutes  | 4 hours  |
| P2       | 1 hour      | 8 hours  |
| P3       | 4 hours     | 24 hours |
| P4       | 8 hours     | 72 hours |

Under C1=`wallclock`, both P1 targets use elapsed wall-clock time from `created_at`.

P2, P3 and P4 use business hours in `Europe/Warsaw`.

Business hours are Monday through Friday from 08:00 inclusive to 16:00 exclusive. Public holidays are not excluded.

When a business-hours calculation begins outside the business window, counting starts at the next business opening.

A target that finishes exactly at 16:00 is due at 16:00 that day rather than at the next business opening.

The implementation must use timezone-aware calculations so that Europe/Warsaw daylight-saving-time changes are handled correctly.

## 10. SLA status

`GET /tickets/{id}/sla` returns:

* `priority`;
* `ack_due_at`;
* `resolve_due_at`;
* `ack_breached`;
* `resolve_breached`;
* `paused`.

Acknowledgement is breached if acknowledgement has not occurred and the current instant is later than `ack_due_at`, or if `acknowledged_at` is later than `ack_due_at`.

Resolution is breached if resolution has not occurred and the current instant is later than `resolve_due_at`, or if `resolved_at` is later than `resolve_due_at`.

Equality with a due instant is not a breach.

For a reopened ticket, resolution is considered outstanding again and the original `resolve_due_at` is retained.

`paused` is true only when the ticket is still open, its resolution SLA uses business hours and the current instant is outside business hours.

P1 uses wall-clock SLA under C1=`wallclock`, so its SLA is never paused.

## 11. Test clock

When `SVCDESK_TEST_CLOCK` is set to `1` or `true`, a request may include the `X-Test-Clock` header.

A valid RFC 3339 value in this header becomes `now` for that request only.

It controls timestamps created by that request and all time-dependent decisions, including:

* ticket creation;
* acknowledgement;
* resolution;
* closing;
* reopening;
* SLA breach calculation;
* SLA pause calculation.

The clock is independent for every request. The service does not require test clocks to increase monotonically.

A malformed clock returns HTTP 400 or 422.

Without the header, the service uses real UTC time.

## 12. Ticket listing

`GET /tickets` returns all tickets in a single JSON array.

It accepts optional exact-match filters:

* `state`
* `priority`

No pagination is required.

## 13. Persistence

Tickets must survive restart of the `svcdesk` container.

The implementation may use SQLite stored in a Docker named volume.

## 14. Docker deployment

The project is deployed with Docker Compose.

The Compose configuration must:

* define a service named exactly `svcdesk`;
* build the service from this repository using a `build:` key;
* make the application listen on container port 8080;
* set `SVCDESK_TEST_CLOCK` to `"1"`;
* use no host-path bind mounts;
* require no network access after the image has been built;
* allow `GET /health` to return HTTP 200 within 120 seconds of startup.

Dependencies must therefore be installed during image build rather than downloaded when the container starts.

## 15. Conformance objective

The implementation must satisfy the published Lab 1 checker while exhibiting exactly these decision values:

```yaml
C1: wallclock
C2: immutable
C3: matrix
```

`DECISIONS.md` will declare the same values and explain why each conflicting alternative was rejected.

