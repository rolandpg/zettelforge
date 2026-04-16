"""
Governance Spec Drift Detection

Validates that CI governance steps match the governance controls manifest.
Catches phantom controls (in CI but not in spec) and orphan controls
(in spec but not enforced).

This test is the guardrail against AI agents or developers inserting
undocumented governance checks into CI.
"""

import re
from pathlib import Path

import yaml


GOVERNANCE_MANIFEST = Path(__file__).parent.parent / "governance" / "controls.yaml"
CI_WORKFLOW = Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"


def _load_manifest():
    """Load the governance controls manifest."""
    assert GOVERNANCE_MANIFEST.exists(), (
        f"Governance manifest not found: {GOVERNANCE_MANIFEST}"
    )
    with open(GOVERNANCE_MANIFEST) as f:
        return yaml.safe_load(f)


def _extract_gov_labels_from_ci():
    """Extract all GOV-XXX labels from CI workflow step names."""
    assert CI_WORKFLOW.exists(), f"CI workflow not found: {CI_WORKFLOW}"
    ci_text = CI_WORKFLOW.read_text()
    # Match step names like "GOV-003 — ..." or "GOV-012 — ..."
    return set(re.findall(r"GOV-\d{3}", ci_text))


class TestGovernanceSpecDrift:
    """Ensure CI governance checks are spec-driven."""

    def test_manifest_exists_and_parses(self):
        """The governance manifest must exist and be valid YAML."""
        manifest = _load_manifest()
        assert "controls" in manifest, "Manifest must have a 'controls' key"
        assert len(manifest["controls"]) > 0, "Manifest must declare at least one control"

    def test_all_controls_have_required_fields(self):
        """Every control must have name, category, enforcement, and rules."""
        manifest = _load_manifest()
        for control_id, control in manifest["controls"].items():
            assert re.match(r"GOV-\d{3}", control_id), (
                f"Control ID must match GOV-NNN format: {control_id}"
            )
            for field in ("name", "category", "enforcement", "rules"):
                assert field in control, (
                    f"{control_id} missing required field: {field}"
                )
            assert control["enforcement"] in ("ci", "runtime", "both"), (
                f"{control_id} enforcement must be ci, runtime, or both"
            )
            assert len(control["rules"]) > 0, (
                f"{control_id} must have at least one rule"
            )

    def test_no_phantom_controls_in_ci(self):
        """Every GOV-XXX label in CI must exist in the manifest."""
        manifest = _load_manifest()
        declared_ids = set(manifest["controls"].keys())
        ci_labels = _extract_gov_labels_from_ci()

        phantoms = ci_labels - declared_ids
        assert phantoms == set(), (
            f"Phantom governance controls in CI (not in manifest): {phantoms}. "
            f"Either add them to governance/controls.yaml or remove from ci.yml."
        )

    def test_ci_controls_have_enforcement(self):
        """Every CI-enforced control must reference a ci_step in its rules."""
        manifest = _load_manifest()
        for control_id, control in manifest["controls"].items():
            if control["enforcement"] in ("ci", "both"):
                ci_rules = [
                    r for r in control["rules"]
                    if "ci_step" in r
                ]
                assert len(ci_rules) > 0, (
                    f"{control_id} is CI-enforced but no rule has a ci_step reference"
                )

    def test_runtime_controls_have_enforcement(self):
        """Every runtime-enforced control must reference a runtime_method or test."""
        manifest = _load_manifest()
        for control_id, control in manifest["controls"].items():
            if control["enforcement"] in ("runtime", "both"):
                runtime_rules = [
                    r for r in control["rules"]
                    if "runtime_method" in r or "test" in r
                ]
                assert len(runtime_rules) > 0, (
                    f"{control_id} is runtime-enforced but no rule has "
                    f"a runtime_method or test reference"
                )

    def test_ci_step_references_exist_in_workflow(self):
        """Every ci_step referenced in the manifest must exist in ci.yml."""
        manifest = _load_manifest()
        ci_text = CI_WORKFLOW.read_text()

        missing = []
        for control_id, control in manifest["controls"].items():
            for rule in control["rules"]:
                ci_step = rule.get("ci_step")
                if ci_step and ci_step not in ci_text:
                    missing.append(f"{control_id}/{rule['id']}: ci_step '{ci_step}' not found in ci.yml")

        assert missing == [], (
            f"Manifest references CI steps that don't exist:\n" +
            "\n".join(f"  - {m}" for m in missing)
        )

    def test_test_references_exist(self):
        """Every test file referenced in the manifest must exist."""
        manifest = _load_manifest()
        repo_root = Path(__file__).parent.parent

        missing = []
        for control_id, control in manifest["controls"].items():
            for rule in control["rules"]:
                test_path = rule.get("test")
                if test_path and not (repo_root / test_path).exists():
                    missing.append(f"{control_id}/{rule['id']}: test '{test_path}' not found")

        assert missing == [], (
            f"Manifest references test files that don't exist:\n" +
            "\n".join(f"  - {m}" for m in missing)
        )
