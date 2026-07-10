from aqt.qt import QDialog, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout

from . import server


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

    layout = QVBoxLayout()
    layout.addWidget(QLabel("MCP server port:"))
    layout.addWidget(port_spin)
    layout.addWidget(status_label)

    btn_row = QHBoxLayout()
    btn_row.addWidget(save_btn)
    btn_row.addWidget(close_btn)
    layout.addLayout(btn_row)

    dialog.setLayout(layout)
    dialog.exec()
