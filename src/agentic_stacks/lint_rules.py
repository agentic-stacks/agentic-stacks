"""Skill linting engine — validates skill content against authoring standards.

Rules can be built-in (derived from the authoring guide) or loaded from a
.lint-rules.yaml file shipped in a common repo for centralized control.
"""

import pathlib
import re
from dataclasses import dataclass, field

import yaml


@dataclass
class LintMessage:
    """A single lint finding."""
    level: str  # "error" or "warning"
    rule: str
    path: str
    message: str

    def __str__(self):
        return f"[{self.level.upper()}] {self.rule}: {self.path} — {self.message}"


@dataclass
class LintRules:
    """Configurable lint rule thresholds."""
    # Skill content rules
    require_skill_readme: bool = True
    max_skill_lines: int = 500
    min_skill_lines: int = 5
    forbid_placeholders: bool = True
    placeholder_patterns: list[str] = field(
        default_factory=lambda: [r"\bTBD\b", r"\bTODO\b", r"\bFIXME\b", r"\bplaceholder\b"]
    )
    require_imperative_headings: bool = True
    # Heading words that suggest non-imperative style
    non_imperative_prefixes: list[str] = field(
        default_factory=lambda: ["About", "Regarding", "Overview of", "Introduction to"]
    )

    # CLAUDE.md rules
    require_claude_md: bool = True
    require_routing_table: bool = True
    require_critical_rules: bool = True
    min_critical_rules: int = 3
    max_critical_rules: int = 15

    # Manifest rules
    require_skill_descriptions: bool = True
    require_target_software: bool = True

    # Custom disabled rules
    disabled_rules: list[str] = field(default_factory=list)


def load_rules_from_yaml(path: pathlib.Path) -> LintRules:
    """Load lint rules from a .lint-rules.yaml file, merging with defaults."""
    rules = LintRules()
    if not path.exists():
        return rules

    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        return rules

    for key, value in data.items():
        if hasattr(rules, key):
            setattr(rules, key, value)

    return rules


def load_project_rules(project_dir: pathlib.Path) -> LintRules:
    """Load lint rules for a project, checking common-skills first.

    Resolution order:
    1. .stacks/common-skills/.lint-rules.yaml  (centralized control)
    2. .lint-rules.yaml in the stack being linted   (stack-level override)
    3. Built-in defaults

    The common-skills file provides the base, the stack file can override.
    """
    rules = LintRules()

    # Load from common-skills if present (centralized rules)
    common_rules_path = project_dir / ".stacks" / "common-skills" / ".lint-rules.yaml"
    if common_rules_path.exists():
        rules = load_rules_from_yaml(common_rules_path)

    return rules


def merge_stack_rules(base: LintRules, stack_dir: pathlib.Path) -> LintRules:
    """Merge stack-level .lint-rules.yaml on top of base rules."""
    stack_rules_path = stack_dir / ".lint-rules.yaml"
    if not stack_rules_path.exists():
        return base

    data = yaml.safe_load(stack_rules_path.read_text())
    if not isinstance(data, dict):
        return base

    # Create a copy with overrides
    merged = LintRules()
    # Start from base
    for attr in vars(base):
        setattr(merged, attr, getattr(base, attr))
    # Apply stack overrides
    for key, value in data.items():
        if hasattr(merged, key):
            setattr(merged, key, value)

    return merged


def lint_stack(stack_dir: pathlib.Path, rules: LintRules | None = None) -> list[LintMessage]:
    """Lint a stack directory against the authoring standards.

    Args:
        stack_dir: Path to the stack root (containing stack.yaml).
        rules: Lint rules to apply. If None, uses built-in defaults.

    Returns:
        List of LintMessage findings.
    """
    if rules is None:
        rules = LintRules()

    messages: list[LintMessage] = []

    manifest_path = stack_dir / "stack.yaml"
    if not manifest_path.exists():
        messages.append(LintMessage("error", "manifest", str(stack_dir), "No stack.yaml found"))
        return messages

    manifest = yaml.safe_load(manifest_path.read_text())
    if not isinstance(manifest, dict):
        messages.append(LintMessage("error", "manifest", str(manifest_path), "stack.yaml is not a valid mapping"))
        return messages

    _lint_manifest(manifest, manifest_path, rules, messages)
    _lint_claude_md(stack_dir, manifest, rules, messages)
    _lint_skills(stack_dir, manifest, rules, messages)

    # Filter out disabled rules
    if rules.disabled_rules:
        messages = [m for m in messages if m.rule not in rules.disabled_rules]

    return messages


def _lint_manifest(manifest: dict, path: pathlib.Path, rules: LintRules, msgs: list[LintMessage]):
    """Check manifest-level quality."""
    if rules.require_skill_descriptions:
        for skill in manifest.get("skills", []):
            if not skill.get("description", "").strip():
                msgs.append(LintMessage(
                    "warning", "skill-description",
                    str(path), f"Skill '{skill.get('name', '?')}' has no description"))

    if rules.require_target_software:
        target = manifest.get("target", {})
        if not target.get("software", "").strip():
            msgs.append(LintMessage(
                "warning", "target-software",
                str(path), "No target.software specified"))


def _lint_claude_md(stack_dir: pathlib.Path, manifest: dict, rules: LintRules, msgs: list[LintMessage]):
    """Check CLAUDE.md structure against authoring standards."""
    claude_path = stack_dir / "CLAUDE.md"

    if rules.require_claude_md:
        if not claude_path.exists():
            msgs.append(LintMessage("error", "claude-md", str(claude_path), "Missing CLAUDE.md"))
            return
    elif not claude_path.exists():
        return

    content = claude_path.read_text()

    if rules.require_routing_table:
        # Look for a markdown table after a "routing" heading
        has_routing = bool(re.search(r"(?i)##\s*routing\s*table", content))
        if not has_routing:
            msgs.append(LintMessage(
                "warning", "routing-table",
                str(claude_path), "Missing '## Routing Table' section"))

        # Check that every manifest skill appears in routing table
        if has_routing:
            for skill in manifest.get("skills", []):
                entry = skill.get("entry", "")
                if entry and entry not in content:
                    msgs.append(LintMessage(
                        "warning", "routing-completeness",
                        str(claude_path),
                        f"Skill '{skill['name']}' (entry: {entry}) not found in routing table"))

    if rules.require_critical_rules:
        critical_match = re.search(r"(?i)##\s*critical\s*rules", content)
        if not critical_match:
            msgs.append(LintMessage(
                "warning", "critical-rules",
                str(claude_path), "Missing '## Critical Rules' section"))
        else:
            # Count numbered rules after the heading
            after_heading = content[critical_match.end():]
            # Stop at the next ## heading
            next_heading = re.search(r"\n##\s", after_heading)
            if next_heading:
                after_heading = after_heading[:next_heading.start()]
            numbered_rules = re.findall(r"^\s*\d+\.", after_heading, re.MULTILINE)
            count = len(numbered_rules)
            if count < rules.min_critical_rules:
                msgs.append(LintMessage(
                    "warning", "critical-rules-count",
                    str(claude_path),
                    f"Only {count} critical rules (minimum {rules.min_critical_rules})"))
            elif count > rules.max_critical_rules:
                msgs.append(LintMessage(
                    "warning", "critical-rules-count",
                    str(claude_path),
                    f"{count} critical rules (maximum {rules.max_critical_rules}) — too many dilutes their impact"))


def _lint_skills(stack_dir: pathlib.Path, manifest: dict, rules: LintRules, msgs: list[LintMessage]):
    """Check individual skill directories and content."""
    for skill in manifest.get("skills", []):
        entry = skill.get("entry", "")
        skill_name = skill.get("name", "?")
        skill_path = stack_dir / entry

        if not skill_path.exists():
            msgs.append(LintMessage("error", "skill-missing", str(skill_path),
                                    f"Skill '{skill_name}' entry path does not exist"))
            continue

        if not skill_path.is_dir():
            msgs.append(LintMessage("warning", "skill-not-dir", str(skill_path),
                                    f"Skill '{skill_name}' entry should be a directory"))
            continue

        # Check for README.md
        readme = skill_path / "README.md"
        if rules.require_skill_readme and not readme.exists():
            msgs.append(LintMessage(
                "warning", "skill-readme",
                str(skill_path), f"Skill '{skill_name}' missing README.md"))

        # Lint all markdown files in the skill directory
        for md_file in skill_path.rglob("*.md"):
            _lint_markdown_file(md_file, skill_name, rules, msgs)


def _lint_markdown_file(path: pathlib.Path, skill_name: str, rules: LintRules, msgs: list[LintMessage]):
    """Lint a single markdown file for content quality."""
    content = path.read_text()
    lines = content.splitlines()

    # Check file length
    if len(lines) > rules.max_skill_lines:
        msgs.append(LintMessage(
            "warning", "skill-length",
            str(path),
            f"Skill file has {len(lines)} lines (max {rules.max_skill_lines}) — consider splitting"))

    if len(lines) < rules.min_skill_lines:
        msgs.append(LintMessage(
            "warning", "skill-length",
            str(path),
            f"Skill file has only {len(lines)} lines (min {rules.min_skill_lines}) — too sparse"))

    # Check for placeholders
    if rules.forbid_placeholders:
        for pattern in rules.placeholder_patterns:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    msgs.append(LintMessage(
                        "warning", "placeholder",
                        str(path),
                        f"Line {i}: placeholder text found matching '{pattern}'"))
                    break  # One finding per pattern per file

    # Check heading style (imperative vs descriptive)
    if rules.require_imperative_headings:
        for i, line in enumerate(lines, 1):
            heading_match = re.match(r"^#{1,3}\s+(.+)", line)
            if heading_match:
                heading_text = heading_match.group(1).strip()
                for prefix in rules.non_imperative_prefixes:
                    if heading_text.startswith(prefix):
                        msgs.append(LintMessage(
                            "warning", "imperative-heading",
                            str(path),
                            f"Line {i}: heading '{heading_text}' — prefer imperative style "
                            f"(e.g., 'Install X' not 'About X')"))
                        break
