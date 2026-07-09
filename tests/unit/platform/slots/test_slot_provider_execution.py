from __future__ import annotations

import base64
import importlib.util
import json
import sys
import types
import uuid
from dataclasses import fields
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from doge.bootstrap.runtime_factories.slots import (
    build_builtin_slot_kernel,
    build_slot_aware_eval_suites,
    build_slot_status_rows,
)
from doge.config.settings import AuthConfig, DBConfig, FeatureConfig, Settings, SlotConfig
from doge.infrastructure.database.slot_signing_repository import SQLiteSlotSigningRepository
from doge.platform.slots import (
    SlotConfigurationError,
    SlotContext,
    SlotInstallPolicy,
    SlotInstaller,
    SlotType,
    sign_slot_manifest,
)


def test_provider_execution_default_off_keeps_installed_slot_manifest_only(
    tmp_path, monkeypatch
) -> None:
    installed = _installed_provider(tmp_path, monkeypatch)
    settings = _settings(tmp_path, installed, provider_execution=False)

    rows = build_slot_status_rows(settings)

    row = _row(rows, installed.slot_id)
    assert row["execution_eligible"] is False
    assert "manifest-only slot" in row["execution_blockers"]
    assert "slot_provider_execution disabled" in row["execution_blockers"]
    assert not installed.import_marker.exists()


def test_provider_execution_status_reports_eligible_without_importing_provider(
    tmp_path, monkeypatch
) -> None:
    installed = _installed_provider(tmp_path, monkeypatch)
    settings = _settings(tmp_path, installed, provider_execution=True)

    rows = build_slot_status_rows(settings)

    row = _row(rows, installed.slot_id)
    assert row["execution_eligible"] is True
    assert row["execution"]["signature"]["status"] == "verified"
    assert row["execution"]["signature"]["revocation_checked"] is True
    assert not installed.import_marker.exists()


def test_provider_execution_imports_and_resolves_only_after_all_gates_pass(
    tmp_path, monkeypatch
) -> None:
    installed = _installed_provider(tmp_path, monkeypatch)
    settings = _settings(tmp_path, installed, provider_execution=True)
    kernel = build_builtin_slot_kernel(settings=settings)
    context = SlotContext(settings=settings, feature_flags=_feature_flags(settings))

    contributions = kernel.resolve_contributions(context, slot_type=SlotType.WORKFLOW)

    contribution = next(item for item in contributions if item.slot_id == installed.slot_id)
    assert contribution.workflows[0].slug == "third-party-workflow"
    assert installed.import_marker.read_text(encoding="utf-8") == "imported"


def test_provider_execution_allows_eval_suite_facets_after_p10_gate(
    tmp_path, monkeypatch
) -> None:
    cases_path = tmp_path / "provider-cases.json"
    cases_path.write_text("[]", encoding="utf-8")
    installed = _installed_provider(
        tmp_path,
        monkeypatch,
        slot_type="eval",
        eval_cases_path=cases_path,
    )
    settings = _settings(tmp_path, installed, provider_execution=True)

    registry = build_slot_aware_eval_suites(settings=settings)

    assert registry is not None
    assert installed.slot_id in registry.suite_ids
    suite = registry.suite_for(installed.slot_id)
    assert suite.gold_set_path == cases_path.resolve()
    assert suite.execution_profile == "local_alpha_provider"
    assert suite.eval_policy == ("offline", "deterministic", "provider_signed")
    assert installed.import_marker.read_text(encoding="utf-8") == "imported"


def test_provider_execution_lifecycle_runs_inside_slot_permission_context(
    tmp_path, monkeypatch
) -> None:
    installed = _installed_provider(tmp_path, monkeypatch)
    settings = _settings(tmp_path, installed, provider_execution=True)
    kernel = build_builtin_slot_kernel(settings=settings)
    context = SlotContext(settings=settings, feature_flags=_feature_flags(settings))

    kernel.start(context, slot_type=SlotType.WORKFLOW)

    assert installed.lifecycle_marker.read_text(encoding="utf-8") == (
        f"start:{installed.slot_id}:True"
    )

    kernel.stop(context)

    assert installed.lifecycle_marker.read_text(encoding="utf-8") == (
        f"stop:{installed.slot_id}:True"
    )


def test_provider_execution_resolves_package_installed_by_slot_installer(
    tmp_path, monkeypatch
) -> None:
    installed = _installed_provider(tmp_path, monkeypatch, installed_by_installer=True)
    settings = _settings(tmp_path, installed, provider_execution=True)
    kernel = build_builtin_slot_kernel(settings=settings)
    context = SlotContext(settings=settings, feature_flags=_feature_flags(settings))

    contributions = kernel.resolve_contributions(context, slot_type=SlotType.WORKFLOW)

    contribution = next(item for item in contributions if item.slot_id == installed.slot_id)
    assert contribution.workflows[0].slug == "third-party-workflow"
    assert installed.import_marker.read_text(encoding="utf-8") == "imported"


def test_provider_execution_rejects_sys_path_package_root_collision(
    tmp_path, monkeypatch
) -> None:
    installed = _installed_provider(tmp_path, monkeypatch, typosquat=True)
    settings = _settings(tmp_path, installed, provider_execution=True)
    kernel = build_builtin_slot_kernel(settings=settings)
    context = SlotContext(settings=settings, feature_flags=_feature_flags(settings))

    with pytest.raises(SlotConfigurationError, match="importable host module"):
        kernel.resolve_contributions(context, slot_type=SlotType.WORKFLOW)

    assert not installed.import_marker.exists()


def test_provider_execution_ignores_preloaded_package_prefix_modules(
    tmp_path, monkeypatch
) -> None:
    installed = _installed_provider(tmp_path, monkeypatch)
    fake_helper = types.ModuleType(f"{installed.package_name}.helper")
    fake_helper.MARKER_TEXT = "preloaded"
    fake_helper.__file__ = str(tmp_path / "preloaded-helper.py")
    sys.modules[f"{installed.package_name}.helper"] = fake_helper
    settings = _settings(tmp_path, installed, provider_execution=True)
    kernel = build_builtin_slot_kernel(settings=settings)
    context = SlotContext(settings=settings, feature_flags=_feature_flags(settings))

    kernel.resolve_contributions(context, slot_type=SlotType.WORKFLOW)

    assert installed.import_marker.read_text(encoding="utf-8") == "imported"
    helper_module = sys.modules[f"{installed.package_name}.helper"]
    assert Path(helper_module.__file__).resolve().is_relative_to(
        installed.install_dir
        / installed.slot_id.replace(".", "_")
        / "package"
        / installed.package_name
    )


def test_provider_execution_rejects_loaded_host_module_root_collision(
    tmp_path, monkeypatch
) -> None:
    installed = _installed_provider(tmp_path, monkeypatch, package_name="json")
    settings = _settings(tmp_path, installed, provider_execution=True)
    kernel = build_builtin_slot_kernel(settings=settings)
    context = SlotContext(settings=settings, feature_flags=_feature_flags(settings))

    with pytest.raises(SlotConfigurationError, match="already loaded host module"):
        kernel.resolve_contributions(context, slot_type=SlotType.WORKFLOW)

    assert not installed.import_marker.exists()
    assert hasattr(json, "loads")


def test_provider_execution_rejects_unloaded_importable_host_module_root_collision(
    tmp_path, monkeypatch
) -> None:
    package_name = _unloaded_importable_host_root()
    installed = _installed_provider(tmp_path, monkeypatch, package_name=package_name)
    settings = _settings(tmp_path, installed, provider_execution=True)
    kernel = build_builtin_slot_kernel(settings=settings)
    context = SlotContext(settings=settings, feature_flags=_feature_flags(settings))

    with pytest.raises(SlotConfigurationError, match="importable host module"):
        kernel.resolve_contributions(context, slot_type=SlotType.WORKFLOW)

    assert not installed.import_marker.exists()
    assert package_name not in sys.modules


def test_provider_execution_rejects_revoked_key_and_accepts_trusted_successor(
    tmp_path, monkeypatch
) -> None:
    revoked = _installed_provider(tmp_path, monkeypatch, key_id="ops@v1")
    successor = _installed_provider(tmp_path, monkeypatch, key_id="ops@v2")
    trusted_keys = {
        "ops@v1": revoked.public_key,
        "ops@v2": successor.public_key,
    }
    settings = _settings(
        tmp_path,
        successor,
        provider_execution=True,
        trusted_publisher_keys=trusted_keys,
    )
    SQLiteSlotSigningRepository(settings.db.agent_db).revoke(
        "ops@v1",
        reason="rotated",
        actor_hash="test",
        successor_key_id="ops@v2",
    )

    rows = build_slot_status_rows(settings)
    revoked_row = _row(rows, revoked.slot_id)
    successor_row = _row(rows, successor.slot_id)

    assert revoked_row["execution_eligible"] is False
    assert "signature revoked: key_id is revoked" in revoked_row["execution_blockers"]
    assert successor_row["execution_eligible"] is True
    kernel = build_builtin_slot_kernel(settings=settings)
    context = SlotContext(settings=settings, feature_flags=_feature_flags(settings))
    contributions = kernel.resolve_contributions(context, slot_type=SlotType.WORKFLOW)
    assert any(item.slot_id == successor.slot_id for item in contributions)
    assert not revoked.import_marker.exists()
    assert successor.import_marker.read_text(encoding="utf-8") == "imported"


def test_provider_execution_rejects_manifest_only_v2_signature(
    tmp_path, monkeypatch
) -> None:
    installed = _installed_provider(tmp_path, monkeypatch, package_signed=False)
    settings = _settings(tmp_path, installed, provider_execution=True)

    row = _row(build_slot_status_rows(settings), installed.slot_id)

    assert row["execution_eligible"] is False
    assert "signature is manifest-only; package signature required" in row["execution_blockers"]
    assert not installed.import_marker.exists()


def test_provider_execution_rejects_tampered_signed_package(
    tmp_path, monkeypatch
) -> None:
    installed = _installed_provider(tmp_path, monkeypatch)
    provider_path = (
        installed.install_dir
        / installed.slot_id.replace(".", "_")
        / "package"
        / installed.package_name
        / "provider.py"
    )
    provider_path.write_text("tampered = True\n", encoding="utf-8")
    settings = _settings(tmp_path, installed, provider_execution=True)

    row = _row(build_slot_status_rows(settings), installed.slot_id)

    assert row["execution_eligible"] is False
    assert any("package digest mismatch" in blocker for blocker in row["execution_blockers"])
    assert not installed.import_marker.exists()


def test_provider_execution_requires_verified_signature(tmp_path, monkeypatch) -> None:
    installed = _installed_provider(tmp_path, monkeypatch, signed=False)
    settings = _settings(tmp_path, installed, provider_execution=True)

    row = _row(build_slot_status_rows(settings), installed.slot_id)

    assert row["execution_eligible"] is False
    assert "signature missing" in row["execution_blockers"]
    assert not installed.import_marker.exists()


def test_provider_execution_requires_non_revoked_signing_key(
    tmp_path, monkeypatch
) -> None:
    installed = _installed_provider(tmp_path, monkeypatch)
    settings = _settings(tmp_path, installed, provider_execution=True)
    SQLiteSlotSigningRepository(settings.db.agent_db).revoke(
        "ops-key",
        reason="compromised",
        actor_hash="test",
    )

    row = _row(build_slot_status_rows(settings), installed.slot_id)

    assert row["execution_eligible"] is False
    assert "signature revoked: key_id is revoked" in row["execution_blockers"]
    assert not installed.import_marker.exists()


def test_provider_execution_requires_enterprise_allowlist(tmp_path, monkeypatch) -> None:
    installed = _installed_provider(tmp_path, monkeypatch)
    settings = _settings(
        tmp_path,
        installed,
        provider_execution=True,
        enterprise=True,
        allowlist=(),
    )

    row = _row(build_slot_status_rows(settings), installed.slot_id)

    assert row["execution_eligible"] is False
    assert "slot is not enterprise allowlisted" in row["execution_blockers"]
    assert not installed.import_marker.exists()


def test_provider_execution_requires_runtime_interception(tmp_path, monkeypatch) -> None:
    installed = _installed_provider(tmp_path, monkeypatch)
    settings = _settings(
        tmp_path,
        installed,
        provider_execution=True,
        runtime_interception=False,
    )

    row = _row(build_slot_status_rows(settings), installed.slot_id)

    assert row["execution_eligible"] is False
    assert "slot_runtime_interception disabled" in row["execution_blockers"]
    assert not installed.import_marker.exists()


def test_provider_execution_keeps_route_facets_restricted_after_p10_eval(
    tmp_path, monkeypatch
) -> None:
    installed = _installed_provider(tmp_path, monkeypatch, restricted_facet=True)
    settings = _settings(tmp_path, installed, provider_execution=True)
    kernel = build_builtin_slot_kernel(settings=settings)
    context = SlotContext(settings=settings, feature_flags=_feature_flags(settings))

    with pytest.raises(SlotConfigurationError, match="restricted facet routes"):
        kernel.resolve_contributions(context, slot_type=SlotType.WORKFLOW)

    assert installed.import_marker.exists()


def test_manifest_dir_slots_remain_non_installed_manifest_only(
    tmp_path, monkeypatch
) -> None:
    installed = _installed_provider(tmp_path, monkeypatch)
    manifest_dir = tmp_path / "manifest-dir"
    manifest_dir.mkdir()
    manifest = _manifest(installed.slot_id, installed.entrypoint)
    (manifest_dir / "direct.json").write_text(json.dumps(manifest), encoding="utf-8")
    settings = _settings(
        tmp_path,
        installed,
        provider_execution=True,
        install_dir=tmp_path / "empty-install-dir",
        manifest_dirs=(manifest_dir,),
    )

    row = _row(build_slot_status_rows(settings), installed.slot_id)

    assert row["execution_eligible"] is False
    assert "not installed slot" in row["execution_blockers"]
    assert not installed.import_marker.exists()


class _InstalledFixture:
    def __init__(
        self,
        *,
        slot_id: str,
        entrypoint: str,
        install_dir: Path,
        public_key: str,
        import_marker: Path,
        lifecycle_marker: Path,
        package_name: str,
        key_id: str,
    ) -> None:
        self.slot_id = slot_id
        self.entrypoint = entrypoint
        self.install_dir = install_dir
        self.public_key = public_key
        self.import_marker = import_marker
        self.lifecycle_marker = lifecycle_marker
        self.package_name = package_name
        self.key_id = key_id


def _installed_provider(
    tmp_path,
    monkeypatch,
    *,
    signed: bool = True,
    package_signed: bool = True,
    restricted_facet: bool = False,
    typosquat: bool = False,
    installed_by_installer: bool = False,
    key_id: str = "ops-key",
    package_name: str | None = None,
    slot_type: str = "workflow",
    eval_cases_path: Path | None = None,
) -> _InstalledFixture:
    package_name = package_name or f"p7_provider_{uuid.uuid4().hex}"
    slot_id = f"vendor.p{uuid.uuid4().hex}"
    import_marker = tmp_path / f"{package_name}.imported"
    lifecycle_marker = tmp_path / f"{package_name}.lifecycle"
    monkeypatch.setenv("P5_PROVIDER_IMPORT_MARKER", str(import_marker))
    monkeypatch.setenv("P5_PROVIDER_LIFECYCLE_MARKER", str(lifecycle_marker))

    install_dir = tmp_path / "installed"
    slot_dir = (
        tmp_path / "source" / slot_id.replace(".", "_")
        if installed_by_installer
        else install_dir / slot_id.replace(".", "_")
    )
    slot_dir.mkdir(parents=True)
    package_dir = slot_dir / "package"
    provider_package = package_dir / package_name
    provider_package.mkdir(parents=True)
    (provider_package / "__init__.py").write_text("", encoding="utf-8")
    (provider_package / "helper.py").write_text("MARKER_TEXT = 'imported'\n", encoding="utf-8")
    (provider_package / "provider.py").write_text(
        _provider_module(
            slot_id,
            restricted_facet=restricted_facet,
            slot_type=slot_type,
            eval_cases_path=eval_cases_path,
        ),
        encoding="utf-8",
    )
    if typosquat:
        typosquat_package = tmp_path / package_name
        typosquat_package.mkdir()
        (typosquat_package / "__init__.py").write_text("", encoding="utf-8")
        (typosquat_package / "provider.py").write_text(
            "from pathlib import Path\n"
            "import os\n"
            "marker = os.environ.get('P5_PROVIDER_IMPORT_MARKER')\n"
            "Path(marker).write_text('typosquat', encoding='utf-8') if marker else None\n"
            "class ProviderSlot: pass\n",
            encoding="utf-8",
        )
        monkeypatch.syspath_prepend(str(tmp_path))
    if package_name.startswith("p7_provider_"):
        sys.modules.pop(package_name, None)
        sys.modules.pop(f"{package_name}.provider", None)

    entrypoint = f"{package_name}.provider.ProviderSlot"
    manifest_path = slot_dir / "slot.json"
    manifest_path.write_text(
        json.dumps(
            _manifest(
                slot_id,
                entrypoint,
                slot_type=slot_type,
                eval_cases_path=eval_cases_path,
            ),
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    private_key_path, public_key = _write_private_key(slot_dir)
    if signed:
        sign_slot_manifest(
            manifest_path,
            private_key_path=private_key_path,
            key_id=key_id,
            package_dir=package_dir if package_signed else None,
        )
    if installed_by_installer:
        SlotInstaller().install(
            slot_dir,
            install_dir=install_dir,
            policy=SlotInstallPolicy(
                trusted_publisher_keys={key_id: public_key},
                allow_unsigned_local=False,
            ),
        )
    return _InstalledFixture(
        slot_id=slot_id,
        entrypoint=entrypoint,
        install_dir=install_dir,
        public_key=public_key,
        import_marker=import_marker,
        lifecycle_marker=lifecycle_marker,
        package_name=package_name,
        key_id=key_id,
    )


def _settings(
    tmp_path,
    installed: _InstalledFixture,
    *,
    provider_execution: bool,
    runtime_interception: bool = True,
    enterprise: bool = False,
    allowlist: tuple[str, ...] | None = None,
    install_dir: Path | None = None,
    manifest_dirs: tuple[Path, ...] = (),
    trusted_publisher_keys: dict[str, str] | None = None,
) -> Settings:
    return Settings(
        db=DBConfig(dir=tmp_path / "db"),
        auth=AuthConfig(mode="enterprise" if enterprise else "local_demo"),
        features=FeatureConfig(
            slot_platform=True,
            slot_loader=True,
            slot_install=True,
            slot_runtime_interception=runtime_interception,
            slot_provider_execution=provider_execution,
        ),
        slots=SlotConfig(
            manifest_dirs=manifest_dirs,
            install_dir=install_dir or installed.install_dir,
            enterprise_allowlist=allowlist
            if allowlist is not None
            else ((installed.slot_id,) if enterprise else ()),
            trusted_publisher_keys=trusted_publisher_keys
            if trusted_publisher_keys is not None
            else {installed.key_id: installed.public_key},
            allow_unsigned_local=False,
        ),
    )


def _feature_flags(settings: Settings) -> dict[str, bool]:
    return {
        field.name: getattr(settings.features, field.name)
        for field in fields(settings.features)
        if isinstance(getattr(settings.features, field.name), bool)
    }


def _row(rows, slot_id: str) -> dict:
    return next(row for row in rows if row["id"] == slot_id)


def _unloaded_importable_host_root() -> str:
    for name in ("email", "fractions", "statistics", "mailbox", "smtplib", "zoneinfo"):
        if name in sys.modules:
            continue
        if importlib.util.find_spec(name) is not None:
            return name
    pytest.skip("no unloaded importable host module root available")


def _manifest(
    slot_id: str,
    entrypoint: str,
    *,
    slot_type: str = "workflow",
    eval_cases_path: Path | None = None,
) -> dict:
    if slot_type == "eval":
        if eval_cases_path is None:
            raise ValueError("eval provider fixture requires eval_cases_path")
        return {
            "schema_version": 1,
            "id": slot_id,
            "name": "Third-party Eval Suite",
            "version": "0.1.0",
            "type": "eval",
            "owner": "vendor",
            "maturity": "experimental",
            "description": "Trusted local eval suite provider execution fixture.",
            "entrypoint": entrypoint,
            "provides": {
                "capabilities": ["eval_suite", "provider_eval_suite"],
                "metadata": {
                    "suite_id": slot_id,
                    "gold_set_path": str(eval_cases_path),
                },
            },
            "permissions": {"filesystem": "read", "risk_level": "low"},
            "feature_flags": ["slot_platform"],
        }
    if slot_type != "workflow":
        raise ValueError(f"unsupported provider fixture slot_type: {slot_type}")
    return {
        "schema_version": 1,
        "id": slot_id,
        "name": "Third-party Workflow",
        "version": "0.1.0",
        "type": "workflow",
        "owner": "vendor",
        "maturity": "experimental",
        "description": "Trusted local provider execution fixture.",
        "entrypoint": entrypoint,
        "provides": {"capabilities": ["third_party_workflow"]},
        "permissions": {"risk_level": "low"},
        "feature_flags": ["slot_platform"],
    }


def _provider_module(
    slot_id: str,
    *,
    restricted_facet: bool,
    slot_type: str = "workflow",
    eval_cases_path: Path | None = None,
) -> str:
    restricted = (
        "routes=(GatewayRouteContribution("
        "router_id='bad-route', router_factory=lambda context: None, prefix='/bad'),)"
        if restricted_facet
        else ""
    )
    if slot_type == "eval":
        if eval_cases_path is None:
            raise ValueError("eval provider fixture requires eval_cases_path")
        return _eval_provider_module(slot_id, eval_cases_path)
    if slot_type != "workflow":
        raise ValueError(f"unsupported provider fixture slot_type: {slot_type}")
    return f"""
import os
from pathlib import Path

from .helper import MARKER_TEXT

from doge.platform.slots import (
    current_slot_permission_context,
    GatewayRouteContribution,
    ISlot,
    SlotContribution,
    SlotHealth,
    SlotManifest,
    SlotProvides,
    SlotType,
    WorkflowTemplateContribution,
)

marker = os.environ.get("P5_PROVIDER_IMPORT_MARKER")
if marker:
    Path(marker).write_text(MARKER_TEXT, encoding="utf-8")


class ProviderSlot(ISlot):
    def manifest(self):
        return SlotManifest(
            schema_version=1,
            id={slot_id!r},
            name="Third-party Workflow",
            version="0.1.0",
            type=SlotType.WORKFLOW,
            owner="vendor",
            maturity="experimental",
            description="Trusted local provider execution fixture.",
            entrypoint=__name__ + ".ProviderSlot",
            provides=SlotProvides(capabilities=("third_party_workflow",)),
            health=SlotHealth(status="experimental"),
            feature_flags=("slot_platform",),
        )

    def resolve(self, context):
        return SlotContribution(
            slot_id={slot_id!r},
            workflows=(
                WorkflowTemplateContribution(
                    slug="third-party-workflow",
                    template_factory=lambda context: {{"slug": "third-party-workflow"}},
                ),
            ),
            {restricted}
        )

    def start(self, context):
        self._write_lifecycle("start")

    def stop(self, context):
        self._write_lifecycle("stop")

    def _write_lifecycle(self, action):
        lifecycle_marker = os.environ.get("P5_PROVIDER_LIFECYCLE_MARKER")
        active = current_slot_permission_context()
        slot_id = active.slot_id if active is not None else "none"
        enforce = active.enforce if active is not None else "none"
        if lifecycle_marker:
            Path(lifecycle_marker).write_text(
                f"{{action}}:{{slot_id}}:{{enforce}}",
                encoding="utf-8",
            )
"""


def _eval_provider_module(slot_id: str, eval_cases_path: Path) -> str:
    return f"""
import os
from pathlib import Path

from .helper import MARKER_TEXT

from doge.platform.slots import (
    EvalSuiteContribution,
    ISlot,
    SlotContribution,
    SlotHealth,
    SlotManifest,
    SlotProvides,
    SlotType,
)

marker = os.environ.get("P5_PROVIDER_IMPORT_MARKER")
if marker:
    Path(marker).write_text(MARKER_TEXT, encoding="utf-8")


class ProviderSlot(ISlot):
    def manifest(self):
        return SlotManifest(
            schema_version=1,
            id={slot_id!r},
            name="Third-party Eval Suite",
            version="0.1.0",
            type=SlotType.EVAL,
            owner="vendor",
            maturity="experimental",
            description="Trusted local eval suite provider execution fixture.",
            entrypoint=__name__ + ".ProviderSlot",
            provides=SlotProvides(
                capabilities=("eval_suite", "provider_eval_suite"),
                metadata={{
                    "suite_id": {slot_id!r},
                    "gold_set_path": {str(eval_cases_path)!r},
                }},
            ),
            health=SlotHealth(status="experimental"),
            feature_flags=("slot_platform",),
        )

    def resolve(self, context):
        return SlotContribution(
            slot_id={slot_id!r},
            eval_suites=(
                EvalSuiteContribution(
                    suite_id={slot_id!r},
                    gold_set_path={str(eval_cases_path)!r},
                    execution_profile="local_alpha_provider",
                    eval_policy=("offline", "deterministic", "provider_signed"),
                ),
            ),
        )
"""


def _write_private_key(directory: Path) -> tuple[Path, str]:
    private_key = Ed25519PrivateKey.generate()
    private_key_path = directory / "ops-key.pem"
    private_key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return private_key_path, base64.b64encode(public_key).decode("ascii")
