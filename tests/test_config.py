"""Tests for freshservice_mcp.config module."""
import os
from unittest.mock import patch

from freshservice_mcp.config import (
    TicketSource,
    TicketStatus,
    TicketPriority,
    ChangeStatus,
    ChangePriority,
    ChangeImpact,
    ChangeType,
    ChangeRisk,
    UnassignedForOptions,
    AVAILABLE_SCOPES,
)


class TestEnums:
    def test_ticket_source_values(self):
        assert TicketSource.EMAIL == 1
        assert TicketSource.PORTAL == 2
        assert TicketSource.PHONE == 3
        assert TicketSource.MS_TEAMS == 15

    def test_ticket_status_values(self):
        assert TicketStatus.OPEN == 2
        assert TicketStatus.PENDING == 3
        assert TicketStatus.RESOLVED == 4
        assert TicketStatus.CLOSED == 5

    def test_ticket_priority_values(self):
        assert TicketPriority.LOW == 1
        assert TicketPriority.URGENT == 4

    def test_change_status_values(self):
        assert ChangeStatus.OPEN == 1
        assert ChangeStatus.CLOSED == 6

    def test_change_priority_values(self):
        assert ChangePriority.LOW == 1
        assert ChangePriority.URGENT == 4

    def test_change_impact_values(self):
        assert ChangeImpact.LOW == 1
        assert ChangeImpact.HIGH == 3

    def test_change_type_values(self):
        assert ChangeType.MINOR == 1
        assert ChangeType.EMERGENCY == 4

    def test_change_risk_values(self):
        assert ChangeRisk.LOW == 1
        assert ChangeRisk.VERY_HIGH == 4

    def test_unassigned_for_options(self):
        assert UnassignedForOptions.THIRTY_MIN == "30m"
        assert UnassignedForOptions.ONE_DAY == "1d"


class TestAvailableScopes:
    def test_contains_expected_scopes(self):
        assert "tickets" in AVAILABLE_SCOPES
        assert "changes" in AVAILABLE_SCOPES
        assert "assets" in AVAILABLE_SCOPES
        assert "agents" in AVAILABLE_SCOPES
        assert "solutions" in AVAILABLE_SCOPES

    def test_scope_count(self):
        assert len(AVAILABLE_SCOPES) >= 10
