from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_node_validation(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", "-e", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_bootstrap_runtime_catalog_validator_treats_launch_wrapper_special_values_as_catalog_driven() -> None:
    result = _run_node_validation(
        r"""
const assert = require("node:assert/strict");
const { validateRuntimeCatalog } = require("./bin/install.js");
const catalog = require("./src/gpd/adapters/runtime_catalog.json");

const dynamicCatalog = JSON.parse(JSON.stringify(catalog));
const launchWrapperRuntime = dynamicCatalog.find(
  (runtime) => runtime.capabilities.permissions_surface === "launch-wrapper"
);
launchWrapperRuntime.capabilities.permission_surface_kind = "future.json:launchWrapper";
assert.equal(
  validateRuntimeCatalog(dynamicCatalog).find(
    (runtime) => runtime.runtime_name === launchWrapperRuntime.runtime_name
  ).capabilities.permission_surface_kind,
  "future.json:launchWrapper"
);

const invalidCatalog = JSON.parse(JSON.stringify(dynamicCatalog));
invalidCatalog[0].capabilities.permission_surface_kind = "future.json:launchWrapper";
assert.throws(
  () => validateRuntimeCatalog(invalidCatalog),
  /runtime catalog entry 0\.capabilities\.permission_surface_kind must be a config surface label when permissions_surface=config-file/
);
"""
    )

    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
