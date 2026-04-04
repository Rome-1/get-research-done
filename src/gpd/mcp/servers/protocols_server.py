"""GPD Protocols MCP server — exposes physics computation protocols via MCP tools.

Loads protocol files from specs/references/protocols/, parses YAML frontmatter
and markdown body, and serves them via FastMCP tools.

Entry point: python -m gpd.mcp.servers.protocols_server
Console script: gpd-mcp-protocols
"""

import json
import re
import threading
from functools import lru_cache
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from gpd.core.observability import gpd_span
from gpd.mcp.servers import (
    configure_mcp_logging,
    parse_frontmatter_with_error,
    run_mcp_server,
    stable_mcp_error,
    stable_mcp_response,
    tighten_registered_tool_contracts,
)
from gpd.specs import SPECS_DIR

logger = configure_mcp_logging("gpd-protocols")

PROTOCOLS_DIR = SPECS_DIR / "references" / "protocols"
PROTOCOL_DOMAINS_MANIFEST = PROTOCOLS_DIR / "protocol-domains.json"

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)


def _extract_sections(body: str) -> list[dict[str, str | int]]:
    """Extract H2/H3 sections from markdown body."""
    sections: list[dict[str, str | int]] = []
    matches = list(_HEADING_RE.finditer(body))
    for i, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        content = body[start:end].strip()
        sections.append({"level": level, "title": title, "content": content})
    return sections


def _extract_steps_and_checkpoints(body: str) -> tuple[list[str], list[str]]:
    """Extract procedural steps and verification checkpoints from the body.

    Parses sections once and extracts both in a single pass (avoids
    duplicate ``_extract_sections`` calls).
    """
    steps: list[str] = []
    checkpoints: list[str] = []
    for section in _extract_sections(body):
        title_lower = section["title"].lower()
        if any(kw in title_lower for kw in ("step", "procedure", "method", "organization", "approach")):
            for line in section["content"].split("\n"):
                stripped = line.strip()
                if re.match(r"^(\d+\.|[-*])\s+", stripped):
                    steps.append(re.sub(r"^(\d+\.|[-*])\s+", "", stripped).strip())
        elif any(kw in title_lower for kw in ("verification", "checkpoint", "check", "common pitfall", "common error")):
            for line in section["content"].split("\n"):
                stripped = line.strip()
                if re.match(r"^(\d+\.|[-*])\s+", stripped):
                    checkpoints.append(re.sub(r"^(\d+\.|[-*])\s+", "", stripped).strip())
    return steps, checkpoints


def _load_authoritative_protocol_parts(path: Path) -> tuple[dict[str, object], str]:
    """Read one authoritative protocol document or fail closed."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise OSError(f"Failed to read {path}: {exc}") from exc

    meta, body, parse_error = parse_frontmatter_with_error(text)
    if parse_error is not None:
        raise ValueError(f"Malformed frontmatter in {path}: {parse_error}")
    return meta, body


@lru_cache(maxsize=1)
def _load_protocol_domain_manifest() -> dict[str, str]:
    """Load the authoritative protocol-domain manifest."""
    try:
        raw = json.loads(PROTOCOL_DOMAINS_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Failed to read protocol domain manifest {PROTOCOL_DOMAINS_MANIFEST}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError("Protocol domain manifest must be a JSON object")

    allowed_keys = {"schema_version", "protocol_domains"}
    extra_keys = sorted(str(key) for key in raw if str(key) not in allowed_keys)
    if extra_keys:
        raise ValueError(f"Protocol domain manifest has unexpected keys: {', '.join(extra_keys)}")

    schema_version = raw.get("schema_version")
    if not isinstance(schema_version, int) or isinstance(schema_version, bool) or schema_version != 1:
        raise ValueError(f"Unsupported protocol domain manifest schema_version: {raw.get('schema_version')!r}")

    protocol_domains = raw.get("protocol_domains")
    if not isinstance(protocol_domains, dict) or not protocol_domains:
        raise ValueError("Protocol domain manifest must include a non-empty protocol_domains object")

    domains: dict[str, str] = {}
    for protocol_name, domain in protocol_domains.items():
        if not isinstance(protocol_name, str) or not protocol_name.strip():
            raise ValueError("Protocol domain manifest contains a blank protocol name")
        if not isinstance(domain, str) or not domain.strip():
            raise ValueError(f"Protocol domain manifest for {protocol_name!r} must be a non-empty string")
        normalized_name = protocol_name.strip()
        normalized_domain = domain.strip()
        if normalized_name in domains:
            raise ValueError(f"Protocol domain manifest contains duplicate protocol {normalized_name!r}")
        domains[normalized_name] = normalized_domain
    return domains


def _protocol_domain(name: str) -> str:
    """Return the authoritative domain for one protocol name."""
    domains = _load_protocol_domain_manifest()
    try:
        return domains[name]
    except KeyError as exc:
        raise ValueError(f"Protocol {name!r} is missing domain metadata in {PROTOCOL_DOMAINS_MANIFEST.name}") from exc


def _normalize_protocol_tier(raw: object, *, protocol_name: str) -> int:
    """Return an integer tier for protocol sorting and ranking."""
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ValueError(f"Protocol {protocol_name!r} has invalid frontmatter: tier must be an integer, got {raw!r}")
    return raw


def _normalize_protocol_load_when(raw: object, *, protocol_name: str) -> list[str]:
    """Return a validated ``load_when`` keyword list for protocol routing."""
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(
            f"Protocol {protocol_name!r} has invalid frontmatter: load_when must be a list of non-empty strings"
        )

    cleaned: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            raise ValueError(
                "Protocol "
                f"{protocol_name!r} has invalid frontmatter: load_when contains non-string entry {item!r}"
            )
        stripped = item.strip()
        if not stripped:
            raise ValueError(
                f"Protocol {protocol_name!r} has invalid frontmatter: load_when entries must be non-empty strings"
            )
        cleaned.append(stripped)
    return cleaned


def _normalize_protocol_context_cost(raw: object, *, protocol_name: str) -> str:
    """Return a validated string ``context_cost`` label for protocol metadata."""
    if not isinstance(raw, str):
        raise ValueError(
            f"Protocol {protocol_name!r} has invalid frontmatter: context_cost must be a non-empty string, got {raw!r}"
        )
    stripped = raw.strip()
    if not stripped:
        raise ValueError(
            f"Protocol {protocol_name!r} has invalid frontmatter: context_cost must be a non-empty string"
        )
    return stripped


# ---------------------------------------------------------------------------
# Protocol Store
# ---------------------------------------------------------------------------


class ProtocolStore:
    """In-memory store of parsed protocol files."""

    def __init__(self, protocols_dir: Path) -> None:
        self._protocols: dict[str, dict[str, object]] = {}
        self._load_all(protocols_dir)

    def _load_all(self, protocols_dir: Path) -> None:
        with gpd_span("protocols.load_all", protocols_dir=str(protocols_dir)):
            self._do_load(protocols_dir)

    def _do_load(self, protocols_dir: Path) -> None:
        if not protocols_dir.is_dir():
            raise OSError(f"Protocols directory not found: {protocols_dir}")
        domain_manifest = _load_protocol_domain_manifest()
        protocol_files = sorted(protocols_dir.glob("*.md"))
        if not protocol_files:
            raise ValueError(f"No protocol files found in {protocols_dir}")
        protocol_names = {path.stem for path in protocol_files}
        for path in protocol_files:
            name = path.stem
            meta, body = _load_authoritative_protocol_parts(path)
            load_when = _normalize_protocol_load_when(meta.get("load_when", []), protocol_name=name)
            tier = _normalize_protocol_tier(meta.get("tier", 2), protocol_name=name)
            context_cost = _normalize_protocol_context_cost(meta.get("context_cost", "medium"), protocol_name=name)

            domain = _protocol_domain(name)
            steps, checkpoints = _extract_steps_and_checkpoints(body)

            # Extract title from first H1
            title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else name.replace("-", " ").title()

            self._protocols[name] = {
                "name": name,
                "title": title,
                "domain": domain,
                "tier": tier,
                "context_cost": context_cost,
                "load_when": load_when,
                "steps": steps,
                "checkpoints": checkpoints,
                "body": body,
            }

        unused_manifest_entries = sorted(name for name in domain_manifest if name not in protocol_names)
        if unused_manifest_entries:
            raise ValueError(
                "Protocol domain manifest has entries without protocol files: " + ", ".join(unused_manifest_entries)
            )

        logger.info("Loaded %d protocols from %s", len(self._protocols), protocols_dir)

    def get(self, name: str) -> dict[str, object] | None:
        """Get a protocol by name (stem of the .md file)."""
        return self._protocols.get(name)

    def list_all(self, domain: str | None = None) -> list[dict[str, object]]:
        """List protocols, optionally filtered by domain."""
        if domain is not None and domain not in self.domains:
            raise ValueError(f"Unknown protocol domain: {domain}")
        result = []
        for p in self._protocols.values():
            if domain and p["domain"] != domain:
                continue
            result.append(
                {
                    "name": p["name"],
                    "title": p["title"],
                    "domain": p["domain"],
                    "tier": p["tier"],
                    "context_cost": p["context_cost"],
                    "load_when": p["load_when"],
                }
            )
        return sorted(result, key=lambda x: (x["tier"], str(x["name"])))

    def route(self, computation_type: str) -> list[dict[str, object]]:
        """Find protocols matching a computation type description.

        Matches against load_when keywords using case-insensitive substring matching.
        """
        query = computation_type.lower()
        scored: list[tuple[int, dict[str, object]]] = []

        for p in self._protocols.values():
            score = 0
            # Check load_when keywords
            for keyword in p["load_when"]:
                if isinstance(keyword, str) and keyword.lower() in query:
                    score += 10
                elif isinstance(keyword, str) and any(w in query for w in keyword.lower().split()):
                    score += 3

            # Check protocol name
            name_words = str(p["name"]).replace("-", " ").split()
            for w in name_words:
                if w.lower() in query:
                    score += 5

            # Tier 1 protocols get a bonus
            if p["tier"] == 1:
                score += 2

            if score > 0:
                scored.append(
                    (
                        score,
                        {
                            "name": p["name"],
                            "title": p["title"],
                            "domain": p["domain"],
                            "tier": p["tier"],
                            "context_cost": p["context_cost"],
                            "relevance_score": score,
                        },
                    )
                )

        scored.sort(key=lambda x: -x[0])
        return [item for _, item in scored]

    @property
    def domains(self) -> list[str]:
        """List all unique domains."""
        return sorted({str(p["domain"]) for p in self._protocols.values()})


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

_store: ProtocolStore | None = None
_store_lock = threading.Lock()


def _get_store() -> ProtocolStore:
    """Return the lazily-initialised protocol store (thread-safe)."""
    global _store  # noqa: PLW0603
    if _store is not None:
        return _store
    with _store_lock:
        if _store is None:
            _store = ProtocolStore(PROTOCOLS_DIR)
        return _store


mcp = FastMCP("gpd-protocols")


@mcp.tool()
def get_protocol(name: str) -> dict[str, object]:
    """Get a physics computation protocol by name.

    Returns the full protocol content including steps, checkpoints,
    and the raw markdown body.

    Args:
        name: Protocol name (e.g., "perturbation-theory", "renormalization-group").
              Use the stem of the .md filename without extension.
    """
    with gpd_span("mcp.protocols.get", protocol_name=name):
        try:
            store = _get_store()
            protocol = store.get(name)
            if protocol is None:
                available = [str(p["name"]) for p in store.list_all()]
                return stable_mcp_response({"available": available}, error=f"Protocol '{name}' not found")
            return stable_mcp_response(
                {
                    "name": protocol["name"],
                    "title": protocol["title"],
                    "domain": protocol["domain"],
                    "tier": protocol["tier"],
                    "context_cost": protocol["context_cost"],
                    "load_when": protocol["load_when"],
                    "steps": protocol["steps"],
                    "checkpoints": protocol["checkpoints"],
                    "content": protocol["body"],
                }
            )
        except Exception as exc:  # pragma: no cover - defensive envelope
            return stable_mcp_error(exc)


@mcp.tool()
def list_protocols(domain: str | None = None) -> dict[str, object]:
    """List available physics computation protocols.

    Args:
        domain: Optional domain filter. Use one of the values returned in
                ``available_domains`` such as:
                "core_derivation", "computational_methods", "mathematical_methods",
                "numerical_translation", "gr_cosmology", "fluid_plasma",
                "quantum_info", "condensed_matter", "nuclear_particle",
                "general".
    """
    with gpd_span("mcp.protocols.list", domain=domain or "all"):
        try:
            store = _get_store()
            protocols = store.list_all(domain)
            return stable_mcp_response(
                {
                    "count": len(protocols),
                    "protocols": protocols,
                    "available_domains": store.domains,
                }
            )
        except Exception as exc:  # pragma: no cover - defensive envelope
            return stable_mcp_error(exc)


@mcp.tool()
def route_protocol(computation_type: str) -> dict[str, object]:
    """Auto-select the best protocols for a computation type.

    Given a description of the computation being performed, finds the most
    relevant protocols by matching against load_when keywords and protocol names.

    Args:
        computation_type: Description of the computation (e.g., "perturbative QCD
                         calculation of vacuum polarization at one loop").
    """
    with gpd_span("mcp.protocols.route"):
        try:
            store = _get_store()
            matches = store.route(computation_type)
            return stable_mcp_response(
                {
                    "query": computation_type,
                    "match_count": len(matches),
                    "protocols": matches[:10],  # Top 10 matches
                }
            )
        except Exception as exc:  # pragma: no cover - defensive envelope
            return stable_mcp_error(exc)


@mcp.tool()
def get_protocol_checkpoints(name: str) -> dict[str, object]:
    """Get verification checkpoints for a specific protocol.

    Returns the list of checkpoint/verification steps that should be performed
    during or after applying this protocol.

    Args:
        name: Protocol name (e.g., "perturbation-theory").
    """
    with gpd_span("mcp.protocols.checkpoints", protocol_name=name):
        try:
            store = _get_store()
            protocol = store.get(name)
            if protocol is None:
                available = [str(p["name"]) for p in store.list_all()]
                return stable_mcp_response({"available": available}, error=f"Protocol '{name}' not found")
            return stable_mcp_response(
                {
                    "name": protocol["name"],
                    "title": protocol["title"],
                    "checkpoints": protocol["checkpoints"],
                    "checkpoint_count": len(protocol["checkpoints"]),
                }
            )
        except Exception as exc:  # pragma: no cover - defensive envelope
            return stable_mcp_error(exc)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the gpd-protocols MCP server."""
    run_mcp_server(mcp, "GPD Protocols MCP Server")


tighten_registered_tool_contracts(mcp)


if __name__ == "__main__":
    main()
