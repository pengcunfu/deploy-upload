#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话框模块

包含服务器配置对话框和管理对话框
"""

from typing import Optional, List
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QSpinBox
)
from PySide6.QtCore import Signal
from .server_config import ServerConfig


class ServerConfigDialog(QDialog):
    """单个服务器配置对话框"""

    def __init__(self, parent=None, server: Optional[ServerConfig] = None):
        super().__init__(parent)
        self.server = server
        self.setWindowTitle("编辑服务器配置" if server else "添加服务器")
        self.setMinimumWidth(450)
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # 服务器名称
        name_layout = QHBoxLayout()
        name_label = QLabel("服务器名称:")
        name_label.setMinimumWidth(100)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("例如: 生产服务器")
        if self.server:
            self.name_input.setText(self.server.name)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        # 主机地址
        host_layout = QHBoxLayout()
        host_label = QLabel("主机地址:")
        host_label.setMinimumWidth(100)
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("例如: 192.168.1.100")
        if self.server:
            self.host_input.setText(self.server.host)
        host_layout.addWidget(host_label)
        host_layout.addWidget(self.host_input)
        layout.addLayout(host_layout)

        # 用户名
        username_layout = QHBoxLayout()
        username_label = QLabel("用户名:")
        username_label.setMinimumWidth(100)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("例如: ubuntu")
        if self.server:
            self.username_input.setText(self.server.username)
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        layout.addLayout(username_layout)

        # 密码
        password_layout = QHBoxLayout()
        password_label = QLabel("密码:")
        password_label.setMinimumWidth(100)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("服务器登录密码")
        if self.server:
            self.password_input.setText(self.server.password)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)

        # SSH端口
        port_layout = QHBoxLayout()
        port_label = QLabel("SSH端口:")
        port_label.setMinimumWidth(100)
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(22)
        if self.server:
            self.port_input.setValue(self.server.port)
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_input)
        port_layout.addStretch()
        layout.addLayout(port_layout)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        layout.addStretch()
        self.setLayout(layout)

    def accept_dialog(self):
        """确认对话框"""
        name = self.name_input.text().strip()
        host = self.host_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not all([name, host, username, password]):
            QMessageBox.warning(self, "提示", "请填写完整的服务器信息")
            return

        self.accept()

    def get_server_config(self) -> ServerConfig:
        """获取服务器配置"""
        return ServerConfig(
            name=self.name_input.text().strip(),
            host=self.host_input.text().strip(),
            username=self.username_input.text().strip(),
            password=self.password_input.text(),
            port=self.port_input.value()
        )


class ServerManagerDialog(QDialog):
    """服务器管理对话框"""

    servers_updated = Signal(list)

    def __init__(self, parent=None, servers: List[ServerConfig] = None, select_mode: bool = False):
        super().__init__(parent)
        self.servers = servers or []
        self.select_mode = select_mode  # 是否为选择模式（启动时）
        self.selected_server = None
        self.setWindowTitle("选择服务器" if select_mode else "服务器配置管理")
        self.setMinimumSize(750, 500)
        self.init_ui()

    def done(self, result: int):
        """对话框关闭时自动保存配置"""
        if result == QDialog.DialogCode.Accepted:
            # 对话框被接受时，发出更新信号
            self.servers_updated.emit(self.servers)
        super().done(result)

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # 说明标签
        if self.select_mode:
            info_label = QLabel("请选择一个服务器进行连接，或管理服务器配置")
            info_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        else:
            info_label = QLabel("管理已保存的服务器配置，可以添加、编辑或删除服务器")
        layout.addWidget(info_label)

        # 服务器列表表格
        self.server_table = QTableWidget()
        self.server_table.setColumnCount(5)
        self.server_table.setHorizontalHeaderLabels(["服务器名称", "主机地址", "用户名", "端口", "操作"])
        self.server_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.server_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.server_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.server_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.server_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.server_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.server_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.server_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.server_table.verticalHeader().setVisible(False)
        self.server_table.setAlternatingRowColors(True)
        self.server_table.doubleClicked.connect(self.on_table_double_clicked)
        layout.addWidget(self.server_table)

        # 按钮组
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        if self.select_mode:
            # 选择模式：显示连接按钮
            self.connect_btn = QPushButton("连接")
            self.connect_btn.setMinimumWidth(100)
            self.connect_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px 16px; } QPushButton:hover { background-color: #45a049; }")
            self.connect_btn.clicked.connect(self.connect_to_server)
            btn_layout.addWidget(self.connect_btn)

        self.add_btn = QPushButton("添加服务器")
        self.add_btn.setMinimumWidth(120)
        self.add_btn.clicked.connect(self.add_server)
        btn_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("编辑服务器")
        self.edit_btn.setMinimumWidth(120)
        self.edit_btn.clicked.connect(self.edit_server)
        btn_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("删除服务器")
        self.delete_btn.setMinimumWidth(120)
        self.delete_btn.clicked.connect(self.delete_server)
        btn_layout.addWidget(self.delete_btn)

        if not self.select_mode:
            # 管理模式：显示关闭按钮
            self.close_btn = QPushButton("关闭")
            self.close_btn.setMinimumWidth(100)
            self.close_btn.clicked.connect(self.accept)
            btn_layout.addWidget(self.close_btn)
        else:
            # 选择模式：显示取消按钮
            self.cancel_btn = QPushButton("取消")
            self.cancel_btn.setMinimumWidth(100)
            self.cancel_btn.clicked.connect(self.reject)
            btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.refresh_table()

    def on_table_double_clicked(self, index):
        """表格双击事件"""
        if self.select_mode:
            self.connect_to_server()

    def connect_to_server(self):
        """连接到选中的服务器"""
        selected_rows = self.server_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要连接的服务器")
            return

        row = selected_rows[0].row()
        self.selected_server = self.servers[row]
        self.accept()

    def get_selected_server(self) -> Optional[ServerConfig]:
        """获取选中的服务器"""
        return self.selected_server

    def refresh_table(self):
        """刷新服务器列表"""
        self.server_table.setRowCount(len(self.servers))
        for row, server in enumerate(self.servers):
            self.server_table.setItem(row, 0, QTableWidgetItem(server.name))
            self.server_table.setItem(row, 1, QTableWidgetItem(server.host))
            self.server_table.setItem(row, 2, QTableWidgetItem(server.username))
            self.server_table.setItem(row, 3, QTableWidgetItem(str(server.port)))

            # 操作按钮
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(5, 2, 5, 2)
            btn_layout.setSpacing(5)

            edit_btn = QPushButton("编辑")
            edit_btn.setMaximumWidth(50)
            edit_btn.clicked.connect(lambda checked, r=row: self.edit_server_at_row(r))
            btn_layout.addWidget(edit_btn)

            delete_btn = QPushButton("删除")
            delete_btn.setMaximumWidth(50)
            delete_btn.clicked.connect(lambda checked, r=row: self.delete_server_at_row(r))
            btn_layout.addWidget(delete_btn)

            self.server_table.setCellWidget(row, 4, btn_widget)

    def add_server(self):
        """添加服务器"""
        dialog = ServerConfigDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_server = dialog.get_server_config()
            self.servers.append(new_server)
            self.refresh_table()

    def edit_server(self):
        """编辑选中的服务器"""
        selected_rows = self.server_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要编辑的服务器")
            return

        row = selected_rows[0].row()
        self.edit_server_at_row(row)

    def edit_server_at_row(self, row: int):
        """编辑指定行的服务器"""
        server = self.servers[row]
        dialog = ServerConfigDialog(self, server)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.servers[row] = dialog.get_server_config()
            self.refresh_table()

    def delete_server(self):
        """删除选中的服务器"""
        selected_rows = self.server_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要删除的服务器")
            return

        row = selected_rows[0].row()
        self.delete_server_at_row(row)

    def delete_server_at_row(self, row: int):
        """删除指定行的服务器"""
        server = self.servers[row]
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除服务器 '{server.name}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            del self.servers[row]
            self.refresh_table()

    def get_servers(self) -> List[ServerConfig]:
        """获取服务器列表"""
        return self.servers.copy()


class MySQLInstallDialog(QDialog):
    """MySQL安装配置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MySQL配置")
        self.setMinimumWidth(400)
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()

        # 说明标签
        info_label = QLabel("请设置MySQL root用户密码：")
        layout.addWidget(info_label)

        # 密码输入
        password_layout = QHBoxLayout()
        password_label = QLabel("密码:")
        password_label.setMinimumWidth(80)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setText("root")
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)

        # 确认密码输入
        confirm_layout = QHBoxLayout()
        confirm_label = QLabel("确认密码:")
        confirm_label.setMinimumWidth(80)
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.setText("root")
        confirm_layout.addWidget(confirm_label)
        confirm_layout.addWidget(self.confirm_input)
        layout.addLayout(confirm_layout)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def accept_dialog(self):
        """确认对话框"""
        password = self.password_input.text()
        confirm = self.confirm_input.text()

        if not password:
            QMessageBox.warning(self, "提示", "密码不能为空")
            return

        if password != confirm:
            QMessageBox.warning(self, "提示", "两次输入的密码不一致")
            return

        self.accept()

    def get_password(self) -> str:
        """获取密码"""
        return self.password_input.text()
