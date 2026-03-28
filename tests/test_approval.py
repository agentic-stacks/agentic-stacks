import pytest
from agentic_stacks.approval import ApprovalGate, ApprovalResult, ApprovalTier


def test_auto_tier_approves_immediately():
    gate = ApprovalGate(tier=ApprovalTier.AUTO)
    result = gate.request(action="deploy", environment="dev", description="Deploy to dev")
    assert result.approved is True
    assert result.tier == ApprovalTier.AUTO


def test_auto_notify_approves_with_notification():
    notifications = []
    gate = ApprovalGate(tier=ApprovalTier.AUTO_NOTIFY, notify_fn=lambda msg: notifications.append(msg))
    result = gate.request(action="deploy", environment="staging", description="Deploy to staging")
    assert result.approved is True
    assert result.tier == ApprovalTier.AUTO_NOTIFY
    assert len(notifications) == 1
    assert "staging" in notifications[0]


def test_human_approve_uses_prompt():
    gate = ApprovalGate(tier=ApprovalTier.HUMAN_APPROVE, prompt_fn=lambda msg: True)
    result = gate.request(action="deploy", environment="prod", description="Deploy to prod")
    assert result.approved is True
    assert result.tier == ApprovalTier.HUMAN_APPROVE


def test_human_approve_rejection():
    gate = ApprovalGate(tier=ApprovalTier.HUMAN_APPROVE, prompt_fn=lambda msg: False)
    result = gate.request(action="deploy", environment="prod", description="Deploy to prod")
    assert result.approved is False


def test_human_approve_no_prompt_fn_raises():
    gate = ApprovalGate(tier=ApprovalTier.HUMAN_APPROVE)
    with pytest.raises(RuntimeError, match="prompt_fn"):
        gate.request(action="deploy", environment="prod", description="Deploy")


def test_from_string():
    assert ApprovalTier.from_string("auto") == ApprovalTier.AUTO
    assert ApprovalTier.from_string("auto-notify") == ApprovalTier.AUTO_NOTIFY
    assert ApprovalTier.from_string("human-approve") == ApprovalTier.HUMAN_APPROVE


def test_from_string_invalid():
    with pytest.raises(ValueError, match="Unknown"):
        ApprovalTier.from_string("invalid")
