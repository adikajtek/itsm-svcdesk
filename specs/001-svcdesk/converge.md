<!-- ai-generated: 100% - drafted with ChatGPT by comparing the Lab 1 requirements, decisions and implemented service -->

# Convergence Report

This report compares the written specification and decisions with the service that was actually implemented and verified by the Lab 1 checker.

The implementation follows the required ticket creation, validation, state transition and SLA behaviour. The final service passed the complete Core conformance suite, including the published priority, state-machine, test-clock and SLA checks.

For the priority conflict, R-05 defines priority from the impact and urgency matrix, while R-06 introduces special handling for VIP reporters. The implementation resolves this conflict with C3=`matrix`. The `reporter.vip` value is preserved on the ticket, but it does not alter the priority calculated from impact and urgency. This matches the decision recorded in `DECISIONS.md` and the behaviour observed by the checker.

For ticket reopening, R-09 treats closed tickets as immutable, while R-10 permits reopening in circumstances that overlap with the closed state. The implemented C2=`immutable` policy permits a resolved ticket to be reopened during the seven-day window but rejects reopening once the ticket has been closed. This keeps closed ticket history stable while preserving the supported reopen workflow for resolved tickets.

For SLA calculation, R-13 describes business-hour SLA accounting, while R-14 requires P1 incidents to operate around the clock. The implementation resolves this as C1=`wallclock`: P1 acknowledgement and resolution deadlines use continuous wall-clock time, while lower priorities use the Europe/Warsaw business-hours calendar.

The deployed service and `DECISIONS.md` therefore converge on the same three conflict resolutions: C1=`wallclock`, C2=`immutable`, and C3=`matrix`. The grader observations for the submitted implementation matched all three declared values.

