"""Prompt-visibility regressions for the `grd-check-proof` agent surface."""

from __future__ import annotations

from pathlib import Path

from grd.adapters.install_utils import expand_at_includes

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = REPO_ROOT / "src" / "grd" / "agents"
SPEC_ROOT = REPO_ROOT / "src" / "grd" / "specs"


def _read() -> str:
    return (AGENTS_DIR / "grd-check-proof.md").read_text(encoding="utf-8")


def _expanded() -> str:
    return expand_at_includes(_read(), SPEC_ROOT, "/runtime/")


def test_grd_check_proof_prompts_surface_direct_proof_contract_references() -> None:
    source = _read()

    assert "{GRD_INSTALL_DIR}/templates/proof-redteam-schema.md" in source
    assert "{GRD_INSTALL_DIR}/references/verification/core/proof-redteam-protocol.md" in source
    assert "@{GRD_INSTALL_DIR}/references/publication/peer-review-panel.md" not in source


def test_grd_check_proof_prompt_no_longer_inlines_the_publication_panel() -> None:
    expanded = _expanded()

    assert "Peer Review Panel Protocol" not in expanded
    assert "Six-Agent Panel" not in expanded
    assert "Stage 3. Mathematical Soundness" not in expanded
