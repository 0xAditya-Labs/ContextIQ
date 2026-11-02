"""
Unit tests for ticket_parser.py
================================
Tests the pure-function parser that converts the raw .txt knowledge base
into structured dictionaries. Using tempfile so tests are self-contained
and don't depend on the actual dummy_it_tickets.txt file.

Run from the backend/ directory:
    python -m pytest tests/ -v
"""

import os
import tempfile

import pytest

from app.core.ticket_parser import parse_tickets


# ── Fixtures ───────────────────────────────────────────────────────────────────

VALID_SAMPLE = """\
Ticket ID: TKT-001
Category: VPN
Issue: VPN fails after password change
Resolution: Reset credentials in VPN portal and re-authenticate

Ticket ID: TKT-002
Category: Password Reset
Issue: Account locked out after 5 failed login attempts
Resolution: Contact IT helpdesk with employee ID to unlock

Ticket ID: TKT-003
Category: Printer
Issue: Office printer shows offline after Windows update
Resolution: Uninstall and reinstall the printer driver
"""

WINDOWS_LINE_ENDINGS = VALID_SAMPLE.replace("\n", "\r\n")


def _write_temp(content: str) -> str:
    """Write content to a temp file and return its path."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        return f.name


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestParseTickets:

    def test_parses_correct_number_of_tickets(self):
        path = _write_temp(VALID_SAMPLE)
        try:
            tickets = parse_tickets(path)
            assert len(tickets) == 3
        finally:
            os.unlink(path)

    def test_ticket_id_extracted_correctly(self):
        path = _write_temp(VALID_SAMPLE)
        try:
            tickets = parse_tickets(path)
            assert tickets[0]["ticket_id"] == "TKT-001"
            assert tickets[1]["ticket_id"] == "TKT-002"
            assert tickets[2]["ticket_id"] == "TKT-003"
        finally:
            os.unlink(path)

    def test_category_extracted_correctly(self):
        path = _write_temp(VALID_SAMPLE)
        try:
            tickets = parse_tickets(path)
            assert tickets[0]["category"] == "VPN"
            assert tickets[1]["category"] == "Password Reset"
            assert tickets[2]["category"] == "Printer"
        finally:
            os.unlink(path)

    def test_issue_extracted_correctly(self):
        path = _write_temp(VALID_SAMPLE)
        try:
            tickets = parse_tickets(path)
            assert "password change" in tickets[0]["issue"].lower()
        finally:
            os.unlink(path)

    def test_resolution_extracted_correctly(self):
        path = _write_temp(VALID_SAMPLE)
        try:
            tickets = parse_tickets(path)
            assert "vpn portal" in tickets[0]["resolution"].lower()
        finally:
            os.unlink(path)

    def test_full_text_preserved(self):
        """full_text should contain the raw block, not just extracted fields."""
        path = _write_temp(VALID_SAMPLE)
        try:
            tickets = parse_tickets(path)
            assert "TKT-001" in tickets[0]["full_text"]
            assert "VPN fails" in tickets[0]["full_text"]
        finally:
            os.unlink(path)

    def test_windows_line_endings_handled(self):
        """Parser should normalise \\r\\n to \\n before splitting."""
        path = _write_temp(WINDOWS_LINE_ENDINGS)
        try:
            tickets = parse_tickets(path)
            assert len(tickets) == 3
            # No stray \\r should appear in parsed fields
            assert "\r" not in tickets[0]["ticket_id"]
            assert "\r" not in tickets[0]["category"]
        finally:
            os.unlink(path)

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            parse_tickets("/nonexistent/path/that/does/not/exist.txt")

    def test_empty_file_returns_empty_list(self):
        path = _write_temp("")
        try:
            tickets = parse_tickets(path)
            assert tickets == []
        finally:
            os.unlink(path)

    def test_tickets_without_id_are_skipped(self):
        """Malformed blocks without a Ticket ID line should be filtered out."""
        content = """\
Category: VPN
Issue: Some issue without a Ticket ID
Resolution: Some resolution

Ticket ID: TKT-010
Category: Email
Issue: Cannot access email
Resolution: Reset email password
"""
        path = _write_temp(content)
        try:
            tickets = parse_tickets(path)
            # Only TKT-010 is valid
            assert len(tickets) == 1
            assert tickets[0]["ticket_id"] == "TKT-010"
        finally:
            os.unlink(path)

