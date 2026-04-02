"""Approval gate engine -- auto, auto-notify, or human-approve."""

from dataclasses import dataclass
from enum import Enum
from typing import Callable


class ApprovalTier(Enum):
    AUTO = "auto"
    AUTO_NOTIFY = "auto-notify"
    HUMAN_APPROVE = "human-approve"

    @classmethod
    def from_string(cls, value: str) -> "ApprovalTier":
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(f"Unknown approval tier: {value!r}. Valid tiers: {', '.join(m.value for m in cls)}")


@dataclass(frozen=True)
class ApprovalResult:
    approved: bool
    tier: ApprovalTier
    action: str
    environment: str
    description: str


class ApprovalGate:
    def __init__(self, tier: ApprovalTier, notify_fn: Callable[[str], None] | None = None, prompt_fn: Callable[[str], bool] | None = None):
        self._tier = tier
        self._notify_fn = notify_fn
        self._prompt_fn = prompt_fn

    def request(self, action: str, environment: str, description: str) -> ApprovalResult:
        message = f"[{self._tier.value}] {action} on {environment}: {description}"
        if self._tier == ApprovalTier.AUTO:
            approved = True
        elif self._tier == ApprovalTier.AUTO_NOTIFY:
            approved = True
            if self._notify_fn:
                self._notify_fn(message)
        elif self._tier == ApprovalTier.HUMAN_APPROVE:
            if self._prompt_fn is None:
                raise RuntimeError("prompt_fn is required for human-approve tier")
            approved = self._prompt_fn(message)
        else:
            approved = False
        return ApprovalResult(approved=approved, tier=self._tier, action=action, environment=environment, description=description)
