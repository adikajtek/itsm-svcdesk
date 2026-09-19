<!-- ai-generated: 100% - drafted with ChatGPT from the Lab 1 implementation plan and published checks -->

# Tasks

## Phase 1 - Application foundation

* [ ] Create the Python application under `src/`.
* [ ] Add the required AI-disclosure headers to source files.
* [ ] Add FastAPI and runtime dependencies.
* [ ] Implement `GET /health`.
* [ ] Configure JSON error responses.

## Phase 2 - Ticket creation and retrieval

* [ ] Define request validation for title, description, reporter, impact and urgency.
* [ ] Ignore server-owned and unknown request fields.
* [ ] Generate unique opaque ticket ids.
* [ ] Implement the R-04 priority matrix.
* [ ] Implement C3=`matrix` so VIP does not alter priority.
* [ ] Implement `POST /tickets`.
* [ ] Implement `GET /tickets/{id}`.
* [ ] Implement `GET /tickets`.
* [ ] Add exact-match state and priority filters.
* [ ] Return JSON 404 errors for unknown ticket ids.

## Phase 3 - Test clock

* [ ] Read `SVCDESK_TEST_CLOCK`.
* [ ] Parse RFC 3339 `X-Test-Clock`.
* [ ] Reject malformed clocks with 400 or 422.
* [ ] Use test time independently for each request.
* [ ] Use real UTC time when no usable test clock is supplied.

## Phase 4 - Ticket state machine

* [ ] Implement acknowledge from `new`.
* [ ] Store `acknowledged_at`.
* [ ] Implement start from `acknowledged`.
* [ ] Implement resolve from `in_progress`.
* [ ] Store `resolved_at`.
* [ ] Implement close from `resolved`.
* [ ] Store `closed_at`.
* [ ] Return 409 for all invalid transitions.

## Phase 5 - Reopening

* [ ] Permit reopening a resolved ticket within seven days.
* [ ] Reject reopening after seven days.
* [ ] Implement C2=`immutable`.
* [ ] Always reject reopening closed tickets.
* [ ] Clear resolution state appropriately when a resolved ticket is reopened.
* [ ] Keep the original resolution SLA deadline.

## Phase 6 - SLA deadlines

* [ ] Define acknowledgement and resolution durations for P1-P4.
* [ ] Implement P1 wall-clock deadlines for C1=`wallclock`.
* [ ] Implement Europe/Warsaw business-hours calculation.
* [ ] Skip weekends and non-business hours.
* [ ] Handle the exact-16:00 tie rule.
* [ ] Handle DST correctly.
* [ ] Verify SLA calculations against the published test vectors.

## Phase 7 - SLA status

* [ ] Implement `GET /tickets/{id}/sla`.
* [ ] Implement `ack_breached`.
* [ ] Implement `resolve_breached`.
* [ ] Treat equality with due time as not breached.
* [ ] Treat reopened tickets as unresolved.
* [ ] Implement business-hours `paused`.
* [ ] Ensure P1 is never paused under C1=`wallclock`.

## Phase 8 - Persistence

* [ ] Add SQLite storage.
* [ ] Persist all ticket state and timestamps.
* [ ] Configure a Docker named volume.
* [ ] Ensure no host-path bind mount is present.

## Phase 9 - Container

* [ ] Create the Dockerfile.
* [ ] Install dependencies at image-build time.
* [ ] Run the service on port 8080.
* [ ] Configure `docker-compose.yml`.
* [ ] Ensure service name is exactly `svcdesk`.
* [ ] Ensure Compose contains a `build:` key.
* [ ] Set `SVCDESK_TEST_CLOCK: "1"`.

## Phase 10 - Verification

* [ ] Run `./itsmlab.sh verify 1`.
* [ ] Fix every failing L1-CORE-1 check.
* [ ] Fix every failing L1-CORE-2 check.
* [ ] Confirm L1-CORE-3 passes.
* [ ] Confirm observed C1/C2/C3 values match `DECISIONS.md`.
* [ ] Confirm L1-CORE-5 is `skip` locally.
* [ ] Commit and push the finished implementation.
* [ ] Verify again with a clean working tree.
* [ ] Create and push annotated tag `lab1/v1`.
* [ ] Obtain the submission receipt.

