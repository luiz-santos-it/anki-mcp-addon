from aqt.qt import (
    QApplication,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import client_setup, server


def open_config_dialog(mw, module: str, restart_server) -> None:
    """restart_server(port) -> bool; returns whether the server ended up running."""
    cfg = mw.addonManager.getConfig(module) or {}
    current_port = cfg.get("port", 8766)

    dialog = QDialog(mw)
    dialog.setWindowTitle("anki-mcp Settings")

    status_label = QLabel()

    def _refresh_status(running: bool, port: int) -> None:
        if running:
            status_label.setText(f"Server running on port {port}.")
        else:
            status_label.setText(f"Server NOT running — port {port} may already be in use.")

    _refresh_status(server.is_running(), current_port)

    port_spin = QSpinBox()
    port_spin.setRange(1, 65535)
    port_spin.setValue(current_port)

    def _on_save():
        port = port_spin.value()
        mw.addonManager.writeConfig(module, {"port": port})
        ok = restart_server(port)
        _refresh_status(ok, port)

    save_btn = QPushButton("Save and restart")
    save_btn.clicked.connect(_on_save)

    close_btn = QPushButton("Close")
    close_btn.clicked.connect(dialog.accept)

    server_layout = QVBoxLayout()
    server_layout.addWidget(QLabel("MCP server port:"))
    server_layout.addWidget(port_spin)
    server_layout.addWidget(status_label)

    btn_row = QHBoxLayout()
    btn_row.addWidget(save_btn)
    btn_row.addWidget(close_btn)
    server_layout.addLayout(btn_row)

    server_tab = QWidget()
    server_tab.setLayout(server_layout)

    client_setup_tab, refresh_client_setup = _build_client_setup_tab(dialog, port_spin)
    port_spin.valueChanged.connect(refresh_client_setup)

    tabs = QTabWidget()
    tabs.addTab(server_tab, "Server")
    tabs.addTab(client_setup_tab, "Client Setup")

    outer = QVBoxLayout()
    outer.addWidget(tabs)
    dialog.setLayout(outer)
    dialog.exec()


def _build_client_setup_tab(dialog, port_spin):
    layout = QVBoxLayout()

    current = {"cc": "", "manual": "", "url": ""}

    cc_group = QGroupBox("Claude Code")
    cc_field = QLineEdit()
    cc_field.setReadOnly(True)
    cc_copy_btn = QPushButton("Copy command")
    cc_copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(current["cc"]))
    cc_layout = QVBoxLayout()
    cc_layout.addWidget(cc_field)
    cc_layout.addWidget(cc_copy_btn)
    cc_group.setLayout(cc_layout)

    mcpb_group = QGroupBox("Claude Desktop (Extension)")
    mcpb_layout = QVBoxLayout()
    mcpb_layout.addWidget(QLabel("Export the bundled extension, then install it via Settings → Extensions."))
    mcpb_export_btn = QPushButton("Export Extension...")

    def _on_export():
        dest, _ = QFileDialog.getSaveFileName(
            dialog, "Export Claude Desktop Extension", "anki-mcp.mcpb", "Claude Desktop Extension (*.mcpb)"
        )
        if not dest:
            return
        try:
            client_setup.export_mcpb(dest)
        except OSError as exc:
            QMessageBox.warning(dialog, "Export failed", f"Could not export extension: {exc}")
        else:
            QMessageBox.information(dialog, "Exported", f"Saved to {dest}")

    mcpb_export_btn.clicked.connect(_on_export)
    mcpb_layout.addWidget(mcpb_export_btn)
    mcpb_group.setLayout(mcpb_layout)

    manual_group = QGroupBox("Claude Desktop (manual config, older versions)")
    manual_field = QTextEdit()
    manual_field.setReadOnly(True)
    manual_copy_btn = QPushButton("Copy config")
    manual_copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(current["manual"]))
    manual_layout = QVBoxLayout()
    manual_layout.addWidget(manual_field)
    manual_layout.addWidget(manual_copy_btn)
    manual_group.setLayout(manual_layout)

    other_group = QGroupBox("Other MCP clients")
    url_field = QLineEdit()
    url_field.setReadOnly(True)
    url_copy_btn = QPushButton("Copy URL")
    url_copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(current["url"]))
    other_layout = QVBoxLayout()
    other_layout.addWidget(url_field)
    other_layout.addWidget(url_copy_btn)
    other_group.setLayout(other_layout)

    layout.addWidget(cc_group)
    layout.addWidget(mcpb_group)
    layout.addWidget(manual_group)
    layout.addWidget(other_group)

    tab = QWidget()
    tab.setLayout(layout)

    def _refresh(*_args) -> None:
        port = port_spin.value()
        current["cc"] = client_setup.claude_code_command(port)
        current["manual"] = client_setup.claude_desktop_manual_config(port)
        current["url"] = client_setup.sse_url(port)
        cc_field.setText(current["cc"])
        manual_field.setPlainText(current["manual"])
        url_field.setText(current["url"])

    _refresh()
    return tab, _refresh
