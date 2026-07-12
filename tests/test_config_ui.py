import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PKG_NAME = "_config_ui_under_test"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"{_PKG_NAME}.{name}", _REPO_ROOT / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"{_PKG_NAME}.{name}"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def config_ui_mod():
    pkg = types.ModuleType(_PKG_NAME)
    pkg.__path__ = [str(_REPO_ROOT)]
    sys.modules[_PKG_NAME] = pkg

    original_qt = sys.modules.get("aqt.qt")
    sys.modules["aqt.qt"] = MagicMock()

    _load("server")
    _load("client_setup")
    mod = _load("config_ui")
    yield mod

    for name in (
        f"{_PKG_NAME}.server",
        f"{_PKG_NAME}.client_setup",
        f"{_PKG_NAME}.config_ui",
        _PKG_NAME,
    ):
        sys.modules.pop(name, None)
    if original_qt is not None:
        sys.modules["aqt.qt"] = original_qt


def _make_mw(port=8766):
    mw = MagicMock()
    mw.addonManager.getConfig.return_value = {"port": port}
    return mw


def _connected_callback(mod, call_index):
    save_btn = mod.QPushButton.return_value
    return save_btn.clicked.connect.call_args_list[call_index].args[0]


class TestOpenConfigDialog:
    def test_shows_running_status_with_current_port(self, config_ui_mod):
        mod = config_ui_mod
        mod.server.is_running = lambda: True

        mod.open_config_dialog(_make_mw(8766), "anki_mcp", MagicMock())

        label = mod.QLabel.return_value
        texts = [c.args[0] for c in label.setText.call_args_list]
        assert any("running on port 8766" in t for t in texts)

    def test_shows_not_running_status_when_server_is_down(self, config_ui_mod):
        mod = config_ui_mod
        mod.server.is_running = lambda: False

        mod.open_config_dialog(_make_mw(8766), "anki_mcp", MagicMock())

        label = mod.QLabel.return_value
        texts = [c.args[0] for c in label.setText.call_args_list]
        assert any("NOT running" in t for t in texts)

    def test_save_writes_config_and_restarts_with_spinbox_value(self, config_ui_mod):
        mod = config_ui_mod
        mod.server.is_running = lambda: True
        mod.QSpinBox.return_value.value.return_value = 9999
        restart = MagicMock(return_value=True)

        mod.open_config_dialog(_make_mw(8766), "anki_mcp", restart)
        _connected_callback(mod, 0)()  # simulate clicking "Save and restart"

        restart.assert_called_once_with(9999)

    def test_save_reports_failure_status_when_restart_fails(self, config_ui_mod):
        mod = config_ui_mod
        mod.server.is_running = lambda: True
        mod.QSpinBox.return_value.value.return_value = 80
        restart = MagicMock(return_value=False)
        mw = _make_mw(8766)

        mod.open_config_dialog(mw, "anki_mcp", restart)
        _connected_callback(mod, 0)()

        mw.addonManager.writeConfig.assert_called_once_with("anki_mcp", {"port": 80})
        label = mod.QLabel.return_value
        texts = [c.args[0] for c in label.setText.call_args_list]
        assert any("NOT running" in t for t in texts)

    def test_save_shows_confirmation_popup_on_success(self, config_ui_mod):
        mod = config_ui_mod
        mod.server.is_running = lambda: True
        mod.QSpinBox.return_value.value.return_value = 9999
        restart = MagicMock(return_value=True)

        mod.open_config_dialog(_make_mw(8766), "anki_mcp", restart)
        _connected_callback(mod, 0)()

        assert mod.QMessageBox.information.called
        assert not mod.QMessageBox.warning.called

    def test_save_shows_warning_popup_on_failure(self, config_ui_mod):
        mod = config_ui_mod
        mod.server.is_running = lambda: True
        mod.QSpinBox.return_value.value.return_value = 9999
        restart = MagicMock(return_value=False)

        mod.open_config_dialog(_make_mw(8766), "anki_mcp", restart)
        _connected_callback(mod, 0)()

        assert mod.QMessageBox.warning.called
        assert not mod.QMessageBox.information.called

    def test_restore_default_resets_port_spinbox(self, config_ui_mod):
        mod = config_ui_mod
        mod.server.is_running = lambda: True

        mod.open_config_dialog(_make_mw(9999), "anki_mcp", MagicMock())
        _connected_callback(mod, 6)()  # "Restore default"

        mod.QSpinBox.return_value.setValue.assert_called_with(8766)


class TestClientSetupTab:
    def test_copy_claude_code_command_uses_spinbox_port(self, config_ui_mod):
        mod = config_ui_mod
        mod.server.is_running = lambda: True
        mod.QSpinBox.return_value.value.return_value = 9999

        mod.open_config_dialog(_make_mw(8766), "anki_mcp", MagicMock())
        _connected_callback(mod, 2)()  # "Copy command" (Claude Code)

        mod.QApplication.clipboard.return_value.setText.assert_called_with(
            "claude mcp add anki --transport sse http://127.0.0.1:9999/sse"
        )

    def test_copy_manual_config_uses_spinbox_port(self, config_ui_mod):
        mod = config_ui_mod
        mod.server.is_running = lambda: True
        mod.QSpinBox.return_value.value.return_value = 9999

        mod.open_config_dialog(_make_mw(8766), "anki_mcp", MagicMock())
        _connected_callback(mod, 4)()  # "Copy config" (manual Claude Desktop)

        copied = mod.QApplication.clipboard.return_value.setText.call_args.args[0]
        assert "mcp-remote" in copied
        assert "http://127.0.0.1:9999/sse" in copied

    def test_copy_sse_url_uses_spinbox_port(self, config_ui_mod):
        mod = config_ui_mod
        mod.server.is_running = lambda: True
        mod.QSpinBox.return_value.value.return_value = 9999

        mod.open_config_dialog(_make_mw(8766), "anki_mcp", MagicMock())
        _connected_callback(mod, 5)()  # "Copy URL" (other MCP clients)

        mod.QApplication.clipboard.return_value.setText.assert_called_with(
            "http://127.0.0.1:9999/sse"
        )

    def test_export_button_saves_bundled_mcpb_to_chosen_path(self, config_ui_mod, tmp_path):
        mod = config_ui_mod
        mod.server.is_running = lambda: True
        dest = str(tmp_path / "anki-mcp.mcpb")
        mod.QFileDialog.getSaveFileName.return_value = (dest, "")
        mod.client_setup.export_mcpb = MagicMock()

        mod.open_config_dialog(_make_mw(8766), "anki_mcp", MagicMock())
        _connected_callback(mod, 3)()  # "Export Extension..."

        mod.client_setup.export_mcpb.assert_called_once_with(dest)

    def test_export_button_does_nothing_when_dialog_cancelled(self, config_ui_mod):
        mod = config_ui_mod
        mod.server.is_running = lambda: True
        mod.QFileDialog.getSaveFileName.return_value = ("", "")
        mod.client_setup.export_mcpb = MagicMock()

        mod.open_config_dialog(_make_mw(8766), "anki_mcp", MagicMock())
        _connected_callback(mod, 3)()

        mod.client_setup.export_mcpb.assert_not_called()

    def test_export_button_shows_warning_on_failure(self, config_ui_mod, tmp_path):
        mod = config_ui_mod
        mod.server.is_running = lambda: True
        dest = str(tmp_path / "anki-mcp.mcpb")
        mod.QFileDialog.getSaveFileName.return_value = (dest, "")
        mod.client_setup.export_mcpb = MagicMock(side_effect=OSError("disk full"))

        mod.open_config_dialog(_make_mw(8766), "anki_mcp", MagicMock())
        _connected_callback(mod, 3)()

        assert mod.QMessageBox.warning.called
