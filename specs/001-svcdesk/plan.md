<!-- ai-generated: 100% - drafted with ChatGPT from the Lab 1 specification, API contract and published checks -->

# Implementation Plan

## 1. Technology

The service will be implemented in Python 3.13 using FastAPI.

The application will run inside Docker and listen on port 8080.

Ticket persistence will use SQLite stored in a Docker named volume so that tickets survive service-container restarts.

## 2. Application structure

The implementation will be placed under `src/`.

Planned responsibilities:

* application startup and FastAPI routing;
* request validation and error handling;
* ticket persistence;
* priority calculation;
* ticket state transitions;
* test-clock handling;
* business-hours SLA calculations;
* SLA breach and pause calculations.

The service will expose exactly the HTTP behaviour defined by `API.md`.

## 3. Decisions to implement

The running implementation must exhibit:

* C1 = `wallclock`
* C2 = `immutable`
* C3 = `matrix`

These values must remain consistent with `DECISIONS.md`.

### C1

P1 acknowledgement and resolution targets use wall-clock time.

P2, P3 and P4 targets use business hours in `Europe/Warsaw`.

### C2

Resolved tickets may be reopened within seven days.

Closed tickets may never be reopened.

### C3

Priority is calculated only from impact and urgency.

The VIP flag is stored but does not modify priority.

## 4. HTTP endpoints

Implement:

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

All responses are JSON.

## 5. Validation

Validate the client-controlled fields required by R-03 and R-20.

Reject invalid input with HTTP 400 or 422 and a top-level `error` object.

Ignore unknown request fields and server-owned fields such as:

* id
* priority
* state
* timestamps
* sla

## 6. Priority

Implement the R-04 matrix directly.

Under C3=`matrix`, no VIP promotion is applied after the matrix result.

## 7. State machine

Implement only the permitted transitions:

`new -> acknowledged -> in_progress -> resolved -> closed`

Additionally:

`resolved -> in_progress`

is allowed through `/reopen` while within the seven-day reopening window.

Under C2=`immutable`, `closed -> in_progress` is never allowed.

All invalid transitions return 409.

## 8. Test clock

When `SVCDESK_TEST_CLOCK` is enabled, parse `X-Test-Clock` independently for each request.

A valid value becomes the current time for that request.

A malformed value returns 400 or 422.

The implementation must not require request clocks to be monotonic.

## 9. SLA calculation

Implement both clock types:

### Wall-clock

Used for both P1 targets under C1=`wallclock`.

Due time equals `created_at + target`.

### Business-hours

Used for P2, P3 and P4.

Business hours are Monday-Friday, 08:00-16:00, in `Europe/Warsaw`.

The implementation must:

* skip nights and weekends;
* start counting at the next opening if creation is outside business hours;
* handle Europe/Warsaw DST correctly;
* preserve the rule that a target ending exactly at 16:00 is due at 16:00 that day.

The published API vectors will be used as the reference values.

## 10. SLA status

Implement:

* `ack_breached`
* `resolve_breached`
* `paused`

Equality with a deadline is not a breach.

A reopened ticket becomes unresolved again without receiving a new resolution deadline.

P1 is never paused under C1=`wallclock`.

## 11. Persistence

Use SQLite for ticket data.

Store the database file in a Docker named volume.

No host-path bind mounts will be used.

## 12. Docker

Create a Dockerfile based on Python 3.13.

Dependencies are installed during the image build.

The runtime container must need no external network access.

The Compose service must:

* be named `svcdesk`;
* contain a `build:` key;
* expose application port 8080;
* set `SVCDESK_TEST_CLOCK: "1"`;
* use a named volume for persistence;
* contain no bind mounts.

## 13. Verification

Run:

`./itsmlab.sh verify 1`

Fix failures by check identifier.

The implementation is ready for submission when all locally checked Core specifications pass and L1-CORE-5 is the expected local `skip`.

