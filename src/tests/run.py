# ai-generated: 100% - drafted with ChatGPT from the Lab 1 API contract and reviewed by the student

import json
import os
import sys
import time
import unittest
import urllib.error
import urllib.request
import uuid


BASE_URL = os.getenv("SVCDESK_URL", "http://svcdesk:8080").rstrip("/")


def request(method, path, body=None, clock=None):
    data = None
    headers = {}

    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif method == "POST":
        data = b""

    if clock is not None:
        headers["X-Test-Clock"] = clock

    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw
        return exc.code, payload


def ticket_payload(impact=1, urgency=1, vip=False):
    return {
        "title": f"Own test {uuid.uuid4()}",
        "description": "Ticket created by the Lab 1 own-tests suite",
        "reporter": {
            "name": "Test Reporter",
            "email": "test@example.com",
            "vip": vip,
        },
        "impact": impact,
        "urgency": urgency,
    }


def create_ticket(impact=1, urgency=1, vip=False, clock="2026-10-14T10:00:00Z"):
    status, ticket = request(
        "POST",
        "/tickets",
        ticket_payload(impact, urgency, vip),
        clock,
    )
    if status != 201:
        raise AssertionError(f"ticket creation failed: {status} {ticket}")
    return ticket


class SvcdeskTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        last_error = None

        for _ in range(30):
            try:
                status, body = request("GET", "/health")
                if status == 200:
                    return
            except Exception as exc:
                last_error = exc

            time.sleep(0.5)

        raise RuntimeError(f"svcdesk did not become ready: {last_error}")

    def test_01_health(self):
        status, body = request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["service"], "svcdesk")

    def test_02_create_ticket(self):
        ticket = create_ticket()
        self.assertTrue(ticket["id"])
        self.assertEqual(ticket["state"], "new")

    def test_03_priority_matrix_p1(self):
        ticket = create_ticket(impact=1, urgency=1)
        self.assertEqual(ticket["priority"], "P1")

    def test_04_vip_does_not_override_matrix(self):
        ticket = create_ticket(impact=3, urgency=3, vip=True)
        self.assertEqual(ticket["priority"], "P4")
        self.assertTrue(ticket["reporter"]["vip"])

    def test_05_get_ticket(self):
        created = create_ticket()
        status, fetched = request("GET", f"/tickets/{created['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(fetched["id"], created["id"])

    def test_06_list_priority_filter(self):
        created = create_ticket(impact=1, urgency=1)
        status, tickets = request("GET", "/tickets?priority=P1")
        self.assertEqual(status, 200)
        self.assertTrue(any(t["id"] == created["id"] for t in tickets))

    def test_07_acknowledge(self):
        ticket = create_ticket()
        status, updated = request(
            "POST",
            f"/tickets/{ticket['id']}/ack",
            clock="2026-10-14T10:05:00Z",
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["state"], "acknowledged")
        self.assertEqual(updated["acknowledged_at"], "2026-10-14T10:05:00Z")

    def test_08_full_state_machine(self):
        ticket = create_ticket()

        status, ticket = request(
            "POST",
            f"/tickets/{ticket['id']}/ack",
            clock="2026-10-14T10:05:00Z",
        )
        self.assertEqual(status, 200)

        status, ticket = request(
            "POST",
            f"/tickets/{ticket['id']}/start",
            clock="2026-10-14T10:06:00Z",
        )
        self.assertEqual(status, 200)
        self.assertEqual(ticket["state"], "in_progress")

        status, ticket = request(
            "POST",
            f"/tickets/{ticket['id']}/resolve",
            clock="2026-10-14T11:00:00Z",
        )
        self.assertEqual(status, 200)
        self.assertEqual(ticket["state"], "resolved")

        status, ticket = request(
            "POST",
            f"/tickets/{ticket['id']}/close",
            clock="2026-10-14T11:01:00Z",
        )
        self.assertEqual(status, 200)
        self.assertEqual(ticket["state"], "closed")

    def test_09_invalid_transition_returns_409(self):
        ticket = create_ticket()
        status, body = request(
            "POST",
            f"/tickets/{ticket['id']}/start",
            clock="2026-10-14T10:05:00Z",
        )
        self.assertEqual(status, 409)
        self.assertIn("error", body)

    def test_10_p1_wallclock_sla(self):
        ticket = create_ticket(
            impact=1,
            urgency=1,
            clock="2026-10-14T10:00:00Z",
        )
        self.assertEqual(
            ticket["sla"]["ack_due_at"],
            "2026-10-14T10:15:00Z",
        )
        self.assertEqual(
            ticket["sla"]["resolve_due_at"],
            "2026-10-14T14:00:00Z",
        )

    def test_11_unknown_ticket_returns_404(self):
        status, body = request("GET", "/tickets/does-not-exist")
        self.assertEqual(status, 404)
        self.assertIn("error", body)

    def test_12_malformed_test_clock_is_rejected(self):
        status, body = request(
            "POST",
            "/tickets",
            ticket_payload(),
            clock="not-a-date",
        )
        self.assertIn(status, (400, 422))
        self.assertIn("error", body)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SvcdeskTests)

    result = unittest.TextTestRunner(
        stream=sys.stdout,
        verbosity=1,
    ).run(suite)

    failed = len(result.failures) + len(result.errors)
    passed = result.testsRun - failed - len(result.skipped)

    print(f"ITSMLAB-TESTS: passed={passed} failed={failed}")

    if failed != 0 or passed < 10:
        sys.exit(1)
