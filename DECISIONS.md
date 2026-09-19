---
svcdesk_decisions:
  C1: wallclock
  C2: immutable
  C3: matrix
---
<!-- ai-generated: 90% - drafted with ChatGPT from the course requirements and reviewed by the student -->

# Decisions

## C1 - SLA clock for P1

**Decision:** P1 acknowledgement and resolution targets use wall-clock time continuously, including evenings, nights and weekends.

**Rejected alternative:** I rejected applying the business-hours clock to P1 tickets, which would pause their SLA outside the working-day window.

**Reason:** R-13 says SLA clocks pause outside business hours, while R-14 explicitly requires P1 tickets to be handled around the clock. I treat R-14 as the specific exception to the general business-hours rule in R-13. P2, P3 and P4 still use business hours, while P1 uses wall-clock time.

**Service owner:** The Service Desk product owner should approve this decision because that role owns the SLA policy and is accountable for how urgent incidents are prioritised and reported.

**Customer outcome:** Reporters affected by the most critical P1 incidents receive an SLA that continues running outside office hours, so serious outages are not effectively postponed until the next business day.

## C2 - Closed tickets and reopening

**Decision:** Closed tickets are immutable. Resolved tickets may be reopened within seven days, but a ticket that has reached the closed state cannot be reopened.

**Rejected alternative:** I rejected allowing closed tickets to be reopened within seven days of closure, even though R-10 describes reopening for both resolved and closed tickets.

**Reason:** R-09 explicitly defines a closed ticket as immutable and requires further work to be represented by a new ticket using `related_to`. I therefore retain reopening for resolved tickets but treat closure as the final state, preserving the historical integrity of completed tickets.

**Service owner:** The Service Desk product owner should approve this decision because that role owns the ticket lifecycle, reporting rules and the meaning of the closed state.

**Customer outcome:** Customers retain an auditable history of completed work. If a problem returns after closure, a new related ticket records the new work without changing the history of the original closed ticket.

## C3 - VIP reporters and the priority matrix

**Decision:** Ticket priority is determined only by the impact and urgency matrix. The VIP flag is stored but does not change the calculated priority.

**Rejected alternative:** I rejected automatically raising low-priority VIP tickets to P2 solely because the reporter has `reporter.vip` set to true.

**Reason:** R-05 states that priority is derived from impact and urgency and from nothing else, while R-06 would override that result for VIP reporters. I retain the matrix as the single objective priority rule so that operational severity is determined consistently from business impact and urgency.

**Service owner:** The Service Desk product owner should approve this decision because that role owns the prioritisation policy and is responsible for ensuring that the priority model reflects operational impact consistently.

**Customer outcome:** All reporters receive priorities based on the same impact and urgency criteria. VIP status remains visible to agents but does not displace tickets whose operational impact is genuinely more severe.

