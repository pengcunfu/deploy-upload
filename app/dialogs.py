#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话框模块

包含服务器配置对话框和管理对话框
"""

from typing import Optional, List
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QSpinBox, QComboBox,
    QFileDialog, QGroupBox
)
from PySide6.QtCore import Signal, Qt
from .server_config import ServerConfig
from .server_types import ServerType, get_supported_software


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

        # 服务器类型
        type_layout = QHBoxLayout()
        type_label = QLabel("系统类型:")
        type_label.setMinimumWidth(100)
        self.type_combo = QComboBox()
        for server_type in ServerType:
            self.type_combo.addItem(server_type.value, server_type)
        if self.server:
            # 设置当前服务器类型
            for i in range(self.type_combo.count()):
                if self.type_combo.itemData(i) == self.server.server_type:
                    self.type_combo.setCurrentIndex(i)
                    break
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        layout.addLayout(type_layout)

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
            port=self.port_input.value(),
            server_type=self.type_combo.currentData()
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
        self.server_table.setColumnCount(6)
        self.server_table.setHorizontalHeaderLabels(["服务器名称", "主机地址", "用户名", "端口", "系统类型", "操作"])
        self.server_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.server_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.server_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.server_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.server_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.server_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
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
            self.server_table.setItem(row, 4, QTableWidgetItem(server.server_type.value))

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

            self.server_table.setCellWidget(row, 5, btn_widget)

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


class VueDeployDialog(QDialog):
    """Vue项目部署配置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_root = ""
        self.proxy_configs = []
        self.setWindowTitle("Vue项目部署配置")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        from pathlib import Path
        from PySide6.QtWidgets import QFileDialog, QGroupBox

        layout = QVBoxLayout()
        layout.setSpacing(15)

        # 标题说明
        title_label = QLabel("配置Vue项目部署参数")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(title_label)

        # 项目配置组
        project_group = QGroupBox("项目配置")
        project_layout = QVBoxLayout()
        project_layout.setSpacing(10)

        # 本地项目目录
        root_layout = QHBoxLayout()
        root_label = QLabel("本地项目目录:")
        root_label.setMinimumWidth(100)
        self.root_input = QLineEdit()
        self.root_input.setPlaceholderText("选择本地Vue项目目录")
        browse_btn = QPushButton("选择目录")
        browse_btn.setMaximumWidth(100)
        browse_btn.clicked.connect(self.browse_project)
        root_layout.addWidget(root_label)
        root_layout.addWidget(self.root_input)
        root_layout.addWidget(browse_btn)
        project_layout.addLayout(root_layout)

        # 远程部署目录
        remote_layout = QHBoxLayout()
        remote_label = QLabel("远程部署目录:")
        remote_label.setMinimumWidth(100)
        self.remote_input = QLineEdit()
        self.remote_input.setPlaceholderText("例如: /var/www/vue-apps")
        self.remote_input.setText("/var/www/vue-apps")
        remote_layout.addWidget(remote_label)
        remote_layout.addWidget(self.remote_input)
        project_layout.addLayout(remote_layout)

        # 构建命令
        build_layout = QHBoxLayout()
        build_label = QLabel("构建命令:")
        build_label.setMinimumWidth(100)
        self.build_input = QLineEdit()
        self.build_input.setText("npm run build")
        self.build_input.setPlaceholderText("例如: npm run build 或 pnpm build")
        build_layout.addWidget(build_label)
        build_layout.addWidget(self.build_input)
        project_layout.addLayout(build_layout)

        project_group.setLayout(project_layout)
        layout.addWidget(project_group)

        # Nginx配置组
        nginx_group = QGroupBox("Nginx配置")
        nginx_layout = QVBoxLayout()
        nginx_layout.setSpacing(10)

        # 第一行：端口和服务器名称
        row1_layout = QHBoxLayout()

        port_layout = QHBoxLayout()
        port_label = QLabel("监听端口:")
        port_label.setMinimumWidth(80)
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(80)
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_input)
        port_layout.addStretch()
        row1_layout.addLayout(port_layout)

        server_name_layout = QHBoxLayout()
        server_name_label = QLabel("服务器名称:")
        server_name_label.setMinimumWidth(80)
        self.server_name_input = QLineEdit()
        self.server_name_input.setPlaceholderText("例如: example.com 或 _")
        self.server_name_input.setText("_")
        server_name_layout.addWidget(server_name_label)
        server_name_layout.addWidget(self.server_name_input)
        row1_layout.addLayout(server_name_layout)

        nginx_layout.addLayout(row1_layout)

        # SSL配置
        ssl_layout = QHBoxLayout()
        self.ssl_checkbox = QPushButton("启用HTTPS (SSL)")
        self.ssl_checkbox.setCheckable(True)
        self.ssl_checkbox.setChecked(False)
        ssl_layout.addWidget(self.ssl_checkbox)
        ssl_layout.addStretch()
        nginx_layout.addLayout(ssl_layout)

        nginx_group.setLayout(nginx_layout)
        layout.addWidget(nginx_group)

        # API代理配置组
        proxy_group = QGroupBox("API代理配置")
        proxy_layout = QVBoxLayout()
        proxy_layout.setSpacing(10)

        # 说明标签
        proxy_info = QLabel("配置前端路径到后端API的代理转发（将从vite.config.js自动读取）:")
        proxy_info.setStyleSheet("color: #666; font-size: 11px;")
        proxy_info.setWordWrap(True)
        proxy_layout.addWidget(proxy_info)

        # 代理列表
        self.proxy_table = QTableWidget()
        self.proxy_table.setColumnCount(4)
        self.proxy_table.setHorizontalHeaderLabels(["前端路径", "后端地址", "说明", "操作"])
        self.proxy_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.proxy_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.proxy_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.proxy_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.proxy_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.proxy_table.setMaximumHeight(150)
        self.proxy_table.setAlternatingRowColors(True)
        proxy_layout.addWidget(self.proxy_table)

        # 添加/清除代理按钮
        proxy_btn_layout = QHBoxLayout()
        add_proxy_btn = QPushButton("添加代理规则")
        add_proxy_btn.clicked.connect(lambda: self.add_proxy_row())
        clear_proxy_btn = QPushButton("清空代理")
        clear_proxy_btn.clicked.connect(self.clear_proxy_rows)
        proxy_btn_layout.addWidget(add_proxy_btn)
        proxy_btn_layout.addWidget(clear_proxy_btn)
        proxy_btn_layout.addStretch()
        proxy_layout.addLayout(proxy_btn_layout)

        proxy_group.setLayout(proxy_layout)
        layout.addWidget(proxy_group)

        # 部署选项组
        options_group = QGroupBox("部署选项")
        options_layout = QVBoxLayout()
        options_layout.setSpacing(8)

        # 构建方式选择
        build_mode_label = QLabel("构建方式:")
        build_mode_label.setStyleSheet("font-weight: bold;")
        options_layout.addWidget(build_mode_label)

        from PySide6.QtWidgets import QRadioButton, QButtonGroup
        build_mode_layout = QHBoxLayout()

        self.local_build_radio = QRadioButton("本地构建")
        self.local_build_radio.setChecked(True)
        self.local_build_radio.setToolTip("在本地构建完成后上传dist目录到服务器")

        self.remote_build_radio = QRadioButton("远程构建")
        self.remote_build_radio.setToolTip("上传源代码到服务器后在远程构建")

        # 将按钮添加到按钮组以确保互斥
        build_mode_group = QButtonGroup(self)
        build_mode_group.addButton(self.local_build_radio)
        build_mode_group.addButton(self.remote_build_radio)

        build_mode_layout.addWidget(self.local_build_radio)
        build_mode_layout.addWidget(self.remote_build_radio)
        build_mode_layout.addStretch()
        options_layout.addLayout(build_mode_layout)

        # 构建方式说明
        build_mode_desc = QLabel(
            "• 本地构建: 在本机执行构建，上传dist目录（推荐，服务器负载小）\n"
            "• 远程构建: 上传源码，在服务器执行构建（需服务器安装Node.js）"
        )
        build_mode_desc.setStyleSheet("color: #666; font-size: 11px; padding: 5px 0;")
        build_mode_desc.setWordWrap(True)
        options_layout.addWidget(build_mode_desc)

        options_layout.addSpacing(10)

        self.auto_install_checkbox = QPushButton("自动安装Node.js和npm (如果未安装)")
        self.auto_install_checkbox.setCheckable(True)
        self.auto_install_checkbox.setChecked(True)
        options_layout.addWidget(self.auto_install_checkbox)

        self.clean_build_checkbox = QPushButton("清理并重新构建 (rm -rf node_modules && npm install)")
        self.clean_build_checkbox.setCheckable(True)
        self.clean_build_checkbox.setChecked(False)
        options_layout.addWidget(self.clean_build_checkbox)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        layout.addStretch()
        self.setLayout(layout)

    def load_vite_config(self):
        """读取vite.config.js或vue.config.js配置"""
        import re
        from pathlib import Path

        # 支持的配置文件列表（按优先级排序）
        config_files = [
            "vite.config.js",
            "vite.config.ts",
            "vue.config.js",
            "vue.config.ts"
        ]

        vite_config_path = None
        is_vue_cli = False  # 标记是否为VueCLI配置

        for config_name in config_files:
            test_path = Path(self.project_root) / config_name
            if test_path.exists():
                vite_config_path = test_path
                if config_name.startswith("vue.config"):
                    is_vue_cli = True
                break

        if not vite_config_path or not vite_config_path.exists():
            return

        try:
            content = vite_config_path.read_text(encoding='utf-8')

            if is_vue_cli:
                # VueCLI配置 - 解析devServer.proxy
                self._load_vue_cli_proxy(content)
            else:
                # Vite配置 - 解析server.proxy
                self._load_vite_proxy(content)

        except Exception as e:
            print(f"读取配置文件失败: {e}")

    def _load_vite_proxy(self, content: str):
        """读取Vite的proxy配置"""
        import re

        # 解析server.proxy配置
        # 支持多种格式：
        # 1. proxy: { '/api': { target: '...' } }
        # 2. proxy: { '^/api': { target: '...' } }
        # 3. 使用with子选项的情况

        # 首先尝试提取整个proxy对象
        proxy_pattern = r"proxy\s*:\s*\{([^}]+(?:\{(?:[^{}]|\{[^{}]*\})*\})*[^}]*)\}"
        proxy_match = re.search(proxy_pattern, content, re.DOTALL)

        if proxy_match:
            proxy_block = proxy_match.group(1)

            # 查找所有代理规则
            # 匹配 '/path': { ... } 或 '^/path': { ... }
            rule_pattern = r"['\"](\^?/[^\"]+)['\"]\s*:\s*\{([^}]+(?:\{[^{}]*\})*[^}]*)\}"
            rules = re.findall(rule_pattern, proxy_block, re.DOTALL)

            for path, rule_config in rules:
                # 提取target
                target_match = re.search(r"target\s*:\s*['\"]([^'\"]+)['\"]", rule_config)
                if target_match:
                    target = target_match.group(1)
                    # 清理路径中的^前缀（Nginx不使用这个）
                    clean_path = path.lstrip('^') if path.startswith('^') else path
                    self.add_proxy_row(clean_path, target, "从vite.config.js读取")

    def _load_vue_cli_proxy(self, content: str):
        """读取VueCLI的devServer.proxy配置"""
        import re

        # VueCLI配置格式：
        # module.exports = {
        #   devServer: {
        #     proxy: {
        #       '/api': {
        #         target: 'http://localhost:8080',
        #         ...
        #       }
        #     }
        #   }
        # }

        # 先提取devServer对象
        devserver_pattern = r"devServer\s*:\s*\{([^}]+(?:\{(?:[^{}]|\{[^{}]*\})*\})*[^}]*)\}"
        devserver_match = re.search(devserver_pattern, content, re.DOTALL)

        if devserver_match:
            devserver_block = devserver_match.group(1)

            # 在devServer中查找proxy
            proxy_pattern = r"proxy\s*:\s*\{([^}]+(?:\{(?:[^{}]|\{[^{}]*\})*\})*[^}]*)\}"
            proxy_match = re.search(proxy_pattern, devserver_block, re.DOTALL)

            if proxy_match:
                proxy_block = proxy_match.group(1)

                # 查找所有代理规则
                rule_pattern = r"['\"](\^?/[^\"]+)['\"]\s*:\s*\{([^}]+(?:\{[^{}]*\})*[^}]*)\}"
                rules = re.findall(rule_pattern, proxy_block, re.DOTALL)

                for path, rule_config in rules:
                    # 提取target
                    target_match = re.search(r"target\s*:\s*['\"]([^'\"]+)['\"]", rule_config)
                    if target_match:
                        target = target_match.group(1)
                        # 清理路径中的^前缀
                        clean_path = path.lstrip('^') if path.startswith('^') else path
                        self.add_proxy_row(clean_path, target, "从vue.config.js读取")

    def browse_project(self):
        """浏览项目目录"""
        from pathlib import Path
        directory = QFileDialog.getExistingDirectory(self, "选择Vue项目目录")
        if directory:
            self.root_input.setText(directory)
            self.project_root = directory
            # 清空代理表并重新加载vite配置
            self.proxy_table.setRowCount(0)
            self.load_vite_config()

    def add_proxy_row(self, path: str = "", target: str = "", desc: str = "", editable: bool = True):
        """添加代理行"""
        row = self.proxy_table.rowCount()
        self.proxy_table.insertRow(row)

        # 路径列
        path_item = QTableWidgetItem(path or "/api")
        if editable:
            path_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
        else:
            path_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            path_item.setBackground(Qt.GlobalColor.gray.lighter(130))
        self.proxy_table.setItem(row, 0, path_item)

        # 目标列
        target_item = QTableWidgetItem(target or "http://127.0.0.1:8080")
        if editable:
            target_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
        else:
            target_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            target_item.setBackground(Qt.GlobalColor.gray.lighter(130))
        self.proxy_table.setItem(row, 1, target_item)

        # 说明列
        desc_item = QTableWidgetItem(desc)
        desc_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.proxy_table.setItem(row, 2, desc_item)

        # 删除按钮
        delete_btn = QPushButton("删除")
        delete_btn.setMaximumWidth(60)
        delete_btn.clicked.connect(lambda checked, r=row: self.delete_proxy_row(r))
        self.proxy_table.setCellWidget(row, 3, delete_btn)

    def clear_proxy_rows(self):
        """清空代理行"""
        self.proxy_table.setRowCount(0)

    def delete_proxy_row(self, row: int):
        """删除代理行"""
        self.proxy_table.removeRow(row)

    def accept_dialog(self):
        """确认对话框"""
        remote_dir = self.remote_input.text().strip()
        if not remote_dir:
            QMessageBox.warning(self, "提示", "请输入远程部署目录")
            return

        build_cmd = self.build_input.text().strip()
        if not build_cmd:
            QMessageBox.warning(self, "提示", "请输入构建命令")
            return

        self.accept()

    def get_config(self) -> dict:
        """获取配置"""
        # 收集代理配置
        proxy_configs = []
        for row in range(self.proxy_table.rowCount()):
            path_item = self.proxy_table.item(row, 0)
            target_item = self.proxy_table.item(row, 1)
            if path_item and target_item:
                proxy_configs.append({
                    "path": path_item.text().strip(),
                    "target": target_item.text().strip()
                })

        return {
            "project_root": self.root_input.text().strip(),
            "remote_dir": self.remote_input.text().strip(),
            "build_command": self.build_input.text().strip(),
            "nginx_port": self.port_input.value(),
            "server_name": self.server_name_input.text().strip(),
            "enable_ssl": self.ssl_checkbox.isChecked(),
            "proxy_configs": proxy_configs,
            "auto_install": self.auto_install_checkbox.isChecked(),
            "clean_build": self.clean_build_checkbox.isChecked(),
            "build_mode": "local" if self.local_build_radio.isChecked() else "remote"
        }
