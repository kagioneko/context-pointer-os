import builtins
import os
import subprocess
import sys
from pathlib import Path

from cpos.context_store import ContextStore
from cpos.ait import AITInstruction
from cpos.kernel import CPOS
from cpos.gateway import SourceGateway
from cpos.registry import ContextRegistry
from cpos.registry import ContextObject
from cpos.scheduler import Scheduler
from cpos.shell import CognitiveShell


def test_scheduler_journal_uses_generated_registry_key():
    registry = ContextRegistry()
    scheduler = Scheduler(ContextStore(registry))

    assert registry.kernel_key is not None
    assert scheduler.journal_guard.secret_key == registry.kernel_key.encode()
    assert scheduler.journal_guard.secret_key != b"default_secret"


def test_cpos_exposes_same_key_used_by_journal(tmp_path):
    kernel = CPOS(str(tmp_path / "workspace"))

    assert kernel.kernel_key == kernel.registry.kernel_key
    assert kernel.scheduler.journal_guard.secret_key == kernel.kernel_key.encode()


def test_shell_exits_cleanly_on_eof(monkeypatch, capsys):
    class KernelStub:
        def monitor(self):
            pass

    monkeypatch.setattr(builtins, "input", lambda _prompt: (_ for _ in ()).throw(EOFError()))
    CognitiveShell(KernelStub()).start()

    assert "Input closed." in capsys.readouterr().out


def test_direct_shell_entrypoint_preserves_existing_workspace(tmp_path):
    workspace = tmp_path / "existing"
    workspace.mkdir()
    sentinel = workspace / "keep.txt"
    sentinel.write_text("keep me", encoding="utf-8")
    project_root = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        [
            sys.executable,
            str(project_root / "src" / "cpos" / "shell.py"),
            "--workspace",
            str(workspace),
        ],
        input="exit\n",
        text=True,
        capture_output=True,
        timeout=10,
        cwd=project_root,
    )

    assert result.returncode == 0, result.stderr
    assert sentinel.read_text(encoding="utf-8") == "keep me"


def _run_rewrite(kernel, source, data="updated"):
    obj = ContextObject(
        id="code",
        type="system_code",
        title="Code",
        summary="Code",
        source=source,
        data=data,
        trust_score=1.0,
    )
    kernel.registry.register(obj)
    kernel.scheduler.retrieval_policy.self_modification_enabled = True
    return kernel.scheduler.execute(
        AITInstruction("security", "code", "rewrite", 5),
        bypass_approval=True,
    )


def test_rewrite_is_confined_to_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    kernel = CPOS(str(workspace))

    result = _run_rewrite(kernel, "filesystem:../escaped.py")

    assert result["status"] == "error"
    assert "escapes workspace" in result["result"]
    assert not (tmp_path / "escaped.py").exists()


def test_rewrite_rejects_absolute_path(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    kernel = CPOS(str(workspace))
    destination = tmp_path / "escaped.py"

    result = _run_rewrite(kernel, f"filesystem:{destination}")

    assert result["status"] == "error"
    assert "workspace-relative" in result["result"]
    assert not destination.exists()


def test_rewrite_allows_existing_file_inside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    destination = workspace / "module.py"
    destination.write_text("old", encoding="utf-8")
    kernel = CPOS(str(workspace))

    result = _run_rewrite(kernel, "filesystem:module.py")

    assert result["status"] == "ok"
    assert destination.read_text(encoding="utf-8") == "updated"


def test_rewrite_rejects_symlink_escape(tmp_path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    (workspace / "link").symlink_to(outside, target_is_directory=True)
    kernel = CPOS(str(workspace))

    result = _run_rewrite(kernel, "filesystem:link/escaped.py")

    assert result["status"] == "error"
    assert "escapes workspace" in result["result"]
    assert not (outside / "escaped.py").exists()


def test_source_gateway_rejects_paths_outside_project(tmp_path):
    outside = tmp_path / "outside.py"
    outside.write_text("SECRET = 'not readable'", encoding="utf-8")
    project_root = Path(__file__).resolve().parents[1]
    traversal = Path(os.path.relpath(outside, project_root))

    gateway = SourceGateway()

    assert gateway.fetch_object(str(outside)) is None
    assert gateway.fetch_object(str(traversal)) is None


def test_source_gateway_reads_python_inside_project():
    obj = SourceGateway().fetch_object("src/cpos/ait.py")

    assert obj is not None
    assert obj.source == "filesystem:src/cpos/ait.py"
    assert "class AITInstruction" in obj.data


def test_cpos_step_preserves_scheduler_response_shape(tmp_path):
    kernel = CPOS(str(tmp_path / "workspace"))

    result = kernel.step("m1l9")

    assert isinstance(result, dict)
    assert set(("status", "result")).issubset(result)
