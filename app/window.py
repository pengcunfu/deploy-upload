#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口模块

包含 DeployUpload 主窗口类
"""

import os
from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLineEdit, QPushButton, QLabel, QTextEdit,
    QProgressBar, QFileDialog, QMessageBox, QStyleFactory,
    QMenuBar, QMenu, QDialog
)
from PySide6.QtCore import QThread, Signal, Slot
from PySide6.QtGui import QFont

from .uploader import ProjectUploader
from .server_config import ServerConfig, ServerConfigManager
from .dialogs import ServerManagerDialog, MySQLInstallDialog
from .threads import UploadThread, VueDeployThread, SpringBootDeployThread, FlaskDeployThread, DjangoDeployThread, ExpressDeployThread, InstallThread
from .server_types import SoftwareType


class DeployUploadWindow(QMainWindow):
    """DeployUpload 主窗口"""

    def __init__(self, server: Optional[ServerConfig] = None):
        super().__init__()
        self.uploader: Optional[ProjectUploader] = None
        self.upload_thread: Optional[UploadThread] = None
        self.servers: List[ServerConfig] = []
        self.current_server: Optional[ServerConfig] = server  # 当前连接的服务器
        self.load_servers_config()
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("DeployUpload - 项目部署工具")
        self.setMinimumSize(700, 650)

        # 创建菜单栏
        self.create_menu_bar()

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 添加各个组件
        main_layout.addWidget(self.create_server_config_group())
        main_layout.addWidget(self.create_project_config_group())
        main_layout.addWidget(self.create_progress_group())
        main_layout.addWidget(self.create_log_group())
        main_layout.addWidget(self.create_button_group())

        # 更新当前服务器信息显示
        self.update_server_display()

        # 设置状态栏
        self.statusBar().showMessage("就绪")

    def create_server_config_group(self) -> QGroupBox:
        """创建服务器配置组"""
        group = QGroupBox("当前服务器")

        layout = QVBoxLayout()
        layout.setSpacing(10)

        # 服务器名称和切换按钮
        server_info_layout = QHBoxLayout()
        self.server_name_label = QLabel("未连接")
        self.server_name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        server_info_layout.addWidget(self.server_name_label)
        server_info_layout.addStretch()

        self.switch_server_btn = QPushButton("切换服务器")
        self.switch_server_btn.setMaximumWidth(120)
        self.switch_server_btn.clicked.connect(self.switch_server)
        server_info_layout.addWidget(self.switch_server_btn)
        layout.addLayout(server_info_layout)

        # 服务器详细信息（只读）
        info_grid = QVBoxLayout()

        # 主机地址
        host_layout = QHBoxLayout()
        host_label = QLabel("主机地址:")
        host_label.setMinimumWidth(80)
        self.host_label = QLabel("-")
        self.host_label.setStyleSheet("color: #666; padding: 2px 5px;")
        host_layout.addWidget(host_label)
        host_layout.addWidget(self.host_label)
        host_layout.addStretch()
        info_grid.addLayout(host_layout)

        # 用户名
        username_layout = QHBoxLayout()
        username_label = QLabel("用户名:")
        username_label.setMinimumWidth(80)
        self.username_label = QLabel("-")
        self.username_label.setStyleSheet("color: #666; padding: 2px 5px;")
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_label)
        username_layout.addStretch()
        info_grid.addLayout(username_layout)

        # 端口
        port_layout = QHBoxLayout()
        port_label = QLabel("SSH端口:")
        port_label.setMinimumWidth(80)
        self.port_label = QLabel("-")
        self.port_label.setStyleSheet("color: #666; padding: 2px 5px;")
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_label)
        port_layout.addStretch()
        info_grid.addLayout(port_layout)

        # 系统类型
        type_layout = QHBoxLayout()
        type_label = QLabel("系统类型:")
        type_label.setMinimumWidth(80)
        self.type_label = QLabel("-")
        self.type_label.setStyleSheet("color: #666; padding: 2px 5px;")
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_label)
        type_layout.addStretch()
        info_grid.addLayout(type_layout)

        layout.addLayout(info_grid)

        # 测试连接按钮
        test_btn_layout = QHBoxLayout()
        test_btn_layout.addStretch()
        self.test_connection_btn = QPushButton("测试连接")
        self.test_connection_btn.setMaximumWidth(120)
        self.test_connection_btn.clicked.connect(self.test_connection)
        test_btn_layout.addWidget(self.test_connection_btn)
        layout.addLayout(test_btn_layout)

        group.setLayout(layout)
        return group

    def create_project_config_group(self) -> QGroupBox:
        """创建项目配置组"""
        group = QGroupBox("项目配置")

        layout = QVBoxLayout()
        layout.setSpacing(10)

        # 项目根目录
        project_layout = QHBoxLayout()
        project_label = QLabel("项目目录:")
        project_label.setMinimumWidth(80)
        self.project_input = QLineEdit()
        self.project_input.setText(os.getcwd())
        self.project_input.setPlaceholderText("选择要上传的项目目录")
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.setMaximumWidth(100)
        self.browse_btn.clicked.connect(self.browse_project)
        project_layout.addWidget(project_label)
        project_layout.addWidget(self.project_input)
        project_layout.addWidget(self.browse_btn)
        layout.addLayout(project_layout)

        # 远程目录
        remote_layout = QHBoxLayout()
        remote_label = QLabel("远程目录:")
        remote_label.setMinimumWidth(80)
        self.remote_input = QLineEdit()
        self.remote_input.setPlaceholderText("留空则使用默认目录 (~/)")
        remote_layout.addWidget(remote_label)
        remote_layout.addWidget(self.remote_input)
        layout.addLayout(remote_layout)

        group.setLayout(layout)
        return group

    def create_progress_group(self) -> QGroupBox:
        """创建进度显示组"""
        group = QGroupBox("上传进度")

        layout = QVBoxLayout()
        layout.setSpacing(10)

        # 当前阶段
        self.stage_label = QLabel("就绪")
        font = self.stage_label.font()
        font.setBold(True)
        self.stage_label.setFont(font)
        layout.addWidget(self.stage_label)

        # 总体进度条
        progress_layout = QHBoxLayout()
        progress_label = QLabel("总体进度:")
        progress_label.setMinimumWidth(80)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(progress_label)
        progress_layout.addWidget(self.progress_bar)
        layout.addLayout(progress_layout)

        # 详细进度信息
        detail_layout = QHBoxLayout()
        detail_label = QLabel("详细信息:")
        detail_label.setMinimumWidth(80)
        self.progress_detail = QLabel("等待开始...")
        detail_layout.addWidget(detail_label)
        detail_layout.addWidget(self.progress_detail)
        layout.addLayout(detail_layout)

        group.setLayout(layout)
        return group

    def create_log_group(self) -> QGroupBox:
        """创建日志输出组"""
        group = QGroupBox("日志输出")

        layout = QVBoxLayout()

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(180)
        # 设置等宽字体用于日志显示
        font = QFont("Consolas", 9)
        if not font.exactMatch():
            font = QFont("Courier New", 9)
        self.log_output.setFont(font)

        # 清除日志按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.clear_log_btn = QPushButton("清除日志")
        self.clear_log_btn.setMaximumWidth(100)
        self.clear_log_btn.clicked.connect(self.clear_log)
        btn_layout.addWidget(self.clear_log_btn)
        layout.addLayout(btn_layout)

        layout.addWidget(self.log_output)
        group.setLayout(layout)
        return group

    def create_button_group(self) -> QWidget:
        """创建按钮组"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setSpacing(10)

        layout.addStretch()

        self.upload_btn = QPushButton("开始上传")
        self.upload_btn.setMinimumHeight(35)
        self.upload_btn.setMinimumWidth(150)
        self.upload_btn.clicked.connect(self.start_upload)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.setMinimumHeight(35)
        self.stop_btn.setMinimumWidth(100)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_upload)

        layout.addWidget(self.upload_btn)
        layout.addWidget(self.stop_btn)
        widget.setLayout(layout)
        return widget

    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()

        # 服务器菜单
        server_menu = menubar.addMenu("服务器(&S)")

        manage_servers_action = server_menu.addAction("服务器配置管理(&M)")
        manage_servers_action.triggered.connect(self.manage_servers)

        server_menu.addSeparator()

        # 部署菜单
        deploy_menu = menubar.addMenu("部署(&D)")

        vue_deploy_action = deploy_menu.addAction("Vue项目一键部署(&V)")
        vue_deploy_action.triggered.connect(self.deploy_vue_project)

        springboot_deploy_action = deploy_menu.addAction("SpringBoot项目一键部署(&S)")
        springboot_deploy_action.triggered.connect(self.deploy_springboot_project)

        flask_deploy_action = deploy_menu.addAction("Flask项目一键部署(&F)")
        flask_deploy_action.triggered.connect(self.deploy_flask_project)

        django_deploy_action = deploy_menu.addAction("Django项目一键部署(&D)")
        django_deploy_action.triggered.connect(self.deploy_django_project)

        express_deploy_action = deploy_menu.addAction("Express项目一键部署(&E)")
        express_deploy_action.triggered.connect(self.deploy_express_project)

        deploy_menu.addSeparator()

        # 软件安装菜单
        software_menu = menubar.addMenu("软件安装(&I)")

        # 数据库子菜单
        database_menu = software_menu.addMenu("数据库(&D)")
        database_menu.addAction("安装 MySQL(&M)").triggered.connect(self.install_mysql)
        database_menu.addAction("安装 Redis(&R)").triggered.connect(self.install_redis)
        database_menu.addAction("安装 MongoDB(&O)").triggered.connect(self.install_mongodb)
        database_menu.addAction("安装 PostgreSQL(&P)").triggered.connect(self.install_postgresql)

        # Web服务器子菜单
        web_menu = software_menu.addMenu("Web服务器(&W)")
        web_menu.addAction("安装 Nginx(&N)").triggered.connect(self.install_nginx)

        # 开发环境子菜单
        dev_menu = software_menu.addMenu("开发环境(&E)")
        dev_menu.addAction("安装 JDK(&J)").triggered.connect(self.install_jdk)
        dev_menu.addAction("安装 Python(&P)").triggered.connect(self.install_python)
        dev_menu.addAction("安装 Node.js(&N)").triggered.connect(self.install_nodejs)
        dev_menu.addAction("安装 Git(&G)").triggered.connect(self.install_git)

        # 容器化子菜单
        container_menu = software_menu.addMenu("容器化(&C)")
        container_menu.addAction("安装 Docker(&D)").triggered.connect(self.install_docker)

        # 消息队列子菜单
        mq_menu = software_menu.addMenu("消息队列(&Q)")
        mq_menu.addAction("安装 RabbitMQ(&R)").triggered.connect(self.install_rabbitmq)

        software_menu.addSeparator()

        # 常用组合安装
        software_menu.addAction("Web服务器环境(&W) - Nginx+PHP+MySQL").triggered.connect(self.install_web_stack)
        software_menu.addAction("Java开发环境(&J) - JDK+MySQL+Redis").triggered.connect(self.install_java_stack)
        software_menu.addAction("全栈开发环境(&F) - 完整开发环境").triggered.connect(self.install_full_stack)
        software_menu.addAction("一键安装全部(&A)").triggered.connect(self.install_all_environment)

    def load_servers_config(self):
        """加载服务器配置"""
        self.servers = ServerConfigManager.load_servers()

    def select_server_on_startup(self):
        """启动时选择服务器"""
        # 如果没有当前服务器，显示选择对话框
        if not self.current_server:
            # 重新加载服务器配置（可能用户添加了新服务器）
            self.servers = ServerConfigManager.load_servers()

            if self.servers:
                # 有服务器配置，显示选择对话框
                dialog = ServerManagerDialog(self, self.servers.copy(), select_mode=True)
                # 连接信号，自动保存服务器配置
                dialog.servers_updated.connect(lambda servers: self._save_servers_from_dialog(servers))
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    # 保存可能更新的服务器列表
                    self.servers = dialog.get_servers()
                    ServerConfigManager.save_servers(self.servers)

                    # 获取选中的服务器
                    selected = dialog.get_selected_server()
                    if selected:
                        self.current_server = selected
                        self.update_server_display()
                        self.statusBar().showMessage(f"已连接到服务器: {selected.name}")
                # 用户取消选择，不关闭主窗口，保持未连接状态
            else:
                # 没有服务器配置，提示用户添加
                reply = QMessageBox.question(
                    self,
                    "欢迎使用 DeployUpload",
                    "还没有配置任何服务器。\n\n是否现在添加服务器配置？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )

                if reply == QMessageBox.StandardButton.Yes:
                    dialog = ServerManagerDialog(self, [], select_mode=False)
                    # 连接信号，自动保存服务器配置
                    dialog.servers_updated.connect(lambda servers: self._save_servers_from_dialog(servers))
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        # 保存服务器配置
                        self.servers = dialog.get_servers()
                        ServerConfigManager.save_servers(self.servers)

                        # 如果添加了服务器，再次显示选择对话框
                        if self.servers:
                            select_dialog = ServerManagerDialog(self, self.servers.copy(), select_mode=True)
                            # 连接信号，自动保存服务器配置
                            select_dialog.servers_updated.connect(lambda servers: self._save_servers_from_dialog(servers))
                            if select_dialog.exec() == QDialog.DialogCode.Accepted:
                                self.servers = select_dialog.get_servers()
                                ServerConfigManager.save_servers(self.servers)

                                selected = select_dialog.get_selected_server()
                                if selected:
                                    self.current_server = selected
                                    self.update_server_display()
                                    self.statusBar().showMessage(f"已连接到服务器: {selected.name}")
                # 无论是否添加服务器，都不关闭主窗口

    def save_servers_config(self):
        """保存服务器配置"""
        try:
            ServerConfigManager.save_servers(self.servers)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存服务器配置失败:\n{str(e)}")

    def _save_servers_from_dialog(self, servers: List[ServerConfig]):
        """从对话框保存服务器配置"""
        self.servers = servers
        self.save_servers_config()

    def update_server_display(self):
        """更新服务器信息显示"""
        if self.current_server:
            self.server_name_label.setText(f"🖥️ {self.current_server.name}")
            self.host_label.setText(self.current_server.host)
            self.username_label.setText(self.current_server.username)
            self.port_label.setText(str(self.current_server.port))
            self.type_label.setText(self.current_server.server_type.value)
            self.switch_server_btn.setText("切换服务器")
        else:
            self.server_name_label.setText("未连接")
            self.host_label.setText("-")
            self.username_label.setText("-")
            self.port_label.setText("-")
            self.type_label.setText("-")
            self.switch_server_btn.setText("选择服务器")

    def switch_server(self):
        """切换服务器"""
        dialog = ServerManagerDialog(self, self.servers.copy(), select_mode=True)
        # 连接信号，自动保存服务器配置
        dialog.servers_updated.connect(lambda servers: self._save_servers_from_dialog(servers))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 保存更新后的服务器列表
            self.servers = dialog.get_servers()
            self.save_servers_config()

            # 获取选中的服务器
            selected = dialog.get_selected_server()
            if selected:
                self.current_server = selected
                self.update_server_display()
                self.statusBar().showMessage(f"已切换到服务器: {selected.name}")

    def manage_servers(self):
        """打开服务器管理对话框"""
        dialog = ServerManagerDialog(self, self.servers.copy(), select_mode=False)
        # 连接信号，自动保存服务器配置
        dialog.servers_updated.connect(lambda servers: self._save_servers_from_dialog(servers))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.servers = dialog.get_servers()
            self.save_servers_config()
            # 如果当前服务器还在列表中，更新显示
            if self.current_server:
                for server in self.servers:
                    if server.name == self.current_server.name:
                        self.current_server = server
                        self.update_server_display()
                        break
            QMessageBox.information(self, "成功", "服务器配置已保存")

    def get_server_config(self) -> Optional[tuple]:
        """获取当前服务器配置"""
        if not self.current_server:
            QMessageBox.warning(self, "提示", "请先选择一个服务器")
            return None

        return (
            self.current_server.host,
            self.current_server.username,
            self.current_server.password,
            self.current_server.port
        )

    def deploy_vue_project(self):
        """Vue项目一键部署"""
        config = self.get_server_config()
        if not config:
            return

        host, username, password, port = config
        project_root = self.project_input.text().strip()

        if not project_root or not Path(project_root).exists():
            QMessageBox.warning(self, "提示", "请选择有效的Vue项目目录")
            return

        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认部署",
            f"确定要部署Vue项目到服务器 {host} 吗？\n\n"
            f"项目目录: {project_root}\n\n"
            "该操作将：\n"
            "1. 上传项目文件\n"
            "2. 安装npm依赖\n"
            "3. 执行npm run build\n"
            "4. 配置Nginx",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 清空日志
            self.log_output.clear()

            # 禁用按钮
            self.set_inputs_enabled(False)

            # 创建上传器
            self.uploader = ProjectUploader(host, username, password, port)

            # 在后台线程执行
            self.deploy_thread = VueDeployThread(self.uploader, project_root)
            self.deploy_thread.log.connect(self.append_log)
            self.deploy_thread.progress.connect(self.update_progress)
            self.deploy_thread.finished.connect(self.vue_deploy_finished)
            self.deploy_thread.error.connect(self.upload_error)
            self.deploy_thread.start()

            self.statusBar().showMessage("正在部署Vue项目...")

    def deploy_springboot_project(self):
        """SpringBoot项目一键部署"""
        config = self.get_server_config()
        if not config:
            return

        host, username, password, port = config
        project_root = self.project_input.text().strip()

        if not project_root or not Path(project_root).exists():
            QMessageBox.warning(self, "提示", "请选择有效的SpringBoot项目目录")
            return

        # 检查是否为有效的Maven/Gradle项目
        pom_xml = Path(project_root) / "pom.xml"
        build_gradle = Path(project_root) / "build.gradle"

        if not pom_xml.exists() and not build_gradle.exists():
            QMessageBox.warning(
                self,
                "提示",
                "不是有效的SpringBoot项目\n\n项目目录必须包含 pom.xml (Maven) 或 build.gradle (Gradle) 文件"
            )
            return

        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认部署",
            f"确定要部署SpringBoot项目到服务器 {host} 吗？\n\n"
            f"项目目录: {project_root}\n\n"
            "该操作将：\n"
            "1. 上传项目文件\n"
            "2. 安装Maven/Gradle（如果需要）\n"
            "3. 执行打包命令\n"
            "4. 创建systemd服务\n"
            "5. 启动应用服务",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 清空日志
            self.log_output.clear()

            # 禁用按钮
            self.set_inputs_enabled(False)

            # 创建上传器
            self.uploader = ProjectUploader(host, username, password, port)

            # 在后台线程执行
            self.deploy_thread = SpringBootDeployThread(self.uploader, project_root)
            self.deploy_thread.log.connect(self.append_log)
            self.deploy_thread.progress.connect(self.update_progress)
            self.deploy_thread.finished.connect(self.springboot_deploy_finished)
            self.deploy_thread.error.connect(self.upload_error)
            self.deploy_thread.start()

            self.statusBar().showMessage("正在部署SpringBoot项目...")

    def springboot_deploy_finished(self, success: bool, message: str):
        """SpringBoot部署完成"""
        self.set_inputs_enabled(True)
        self.statusBar().showMessage("部署完成")

        if success:
            QMessageBox.information(
                self,
                "部署成功",
                f"SpringBoot项目部署成功！\n\n部署路径: {message}\n\n"
                "应用已作为系统服务启动，可以使用以下命令管理：\n"
                f"sudo systemctl status <项目名>\n"
                f"sudo systemctl restart <项目名>\n"
                f"sudo systemctl stop <项目名>"
            )
        else:
            QMessageBox.critical(self, "部署失败", message)

    def deploy_flask_project(self):
        """Flask项目一键部署"""
        config = self.get_server_config()
        if not config:
            return

        host, username, password, port = config
        project_root = self.project_input.text().strip()

        if not project_root or not Path(project_root).exists():
            QMessageBox.warning(self, "提示", "请选择有效的Flask项目目录")
            return

        # 检查是否为有效的Flask项目
        app_py = Path(project_root) / "app.py"
        if not app_py.exists():
            # 检查其他常见的Flask入口文件
            common_entries = ["main.py", "run.py", "wsgi.py"]
            has_entry = any((Path(project_root) / entry).exists() for entry in common_entries)
            if not has_entry:
                QMessageBox.warning(
                    self,
                    "提示",
                    "不是有效的Flask项目\n\n项目目录必须包含app.py或其他入口文件（main.py, run.py, wsgi.py等）"
                )
                return

        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认部署",
            f"确定要部署Flask项目到服务器 {host} 吗？\n\n"
            f"项目目录: {project_root}\n\n"
            "该操作将：\n"
            "1. 上传项目文件\n"
            "2. 创建Python虚拟环境\n"
            "3. 安装依赖（requirements.txt）\n"
            "4. 配置Gunicorn服务\n"
            "5. 配置Nginx反向代理\n"
            "6. 启动应用服务",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 清空日志
            self.log_output.clear()

            # 禁用按钮
            self.set_inputs_enabled(False)

            # 创建上传器
            self.uploader = ProjectUploader(host, username, password, port)

            # 在后台线程执行
            self.deploy_thread = FlaskDeployThread(self.uploader, project_root)
            self.deploy_thread.log.connect(self.append_log)
            self.deploy_thread.progress.connect(self.update_progress)
            self.deploy_thread.finished.connect(self.flask_deploy_finished)
            self.deploy_thread.error.connect(self.upload_error)
            self.deploy_thread.start()

            self.statusBar().showMessage("正在部署Flask项目...")

    def flask_deploy_finished(self, success: bool, message: str):
        """Flask部署完成"""
        self.set_inputs_enabled(True)
        self.statusBar().showMessage("部署完成")

        if success:
            QMessageBox.information(
                self,
                "部署成功",
                f"Flask项目部署成功！\n\n部署路径: {message}\n\n"
                "应用已通过Gunicorn和Nginx部署，可以使用以下命令管理：\n"
                f"sudo systemctl status <项目名>\n"
                f"sudo systemctl restart <项目名>\n"
                f"sudo systemctl stop <项目名>\n\n"
                f"服务已通过Nginx在80端口提供访问"
            )
        else:
            QMessageBox.critical(self, "部署失败", message)

    def deploy_django_project(self):
        """Django项目一键部署"""
        config = self.get_server_config()
        if not config:
            return

        host, username, password, port = config
        project_root = self.project_input.text().strip()

        if not project_root or not Path(project_root).exists():
            QMessageBox.warning(self, "提示", "请选择有效的Django项目目录")
            return

        # 检查是否为有效的Django项目
        manage_py = Path(project_root) / "manage.py"
        if not manage_py.exists():
            QMessageBox.warning(
                self,
                "提示",
                "不是有效的Django项目\n\n项目目录必须包含manage.py文件"
            )
            return

        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认部署",
            f"确定要部署Django项目到服务器 {host} 吗？\n\n"
            f"项目目录: {project_root}\n\n"
            "该操作将：\n"
            "1. 上传项目文件\n"
            "2. 创建Python虚拟环境\n"
            "3. 安装依赖（requirements.txt）\n"
            "4. 执行数据库迁移\n"
            "5. 收集静态文件\n"
            "6. 配置Gunicorn服务\n"
            "7. 配置Nginx反向代理\n"
            "8. 启动应用服务",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 清空日志
            self.log_output.clear()

            # 禁用按钮
            self.set_inputs_enabled(False)

            # 创建上传器
            self.uploader = ProjectUploader(host, username, password, port)

            # 在后台线程执行
            self.deploy_thread = DjangoDeployThread(self.uploader, project_root)
            self.deploy_thread.log.connect(self.append_log)
            self.deploy_thread.progress.connect(self.update_progress)
            self.deploy_thread.finished.connect(self.django_deploy_finished)
            self.deploy_thread.error.connect(self.upload_error)
            self.deploy_thread.start()

            self.statusBar().showMessage("正在部署Django项目...")

    def django_deploy_finished(self, success: bool, message: str):
        """Django部署完成"""
        self.set_inputs_enabled(True)
        self.statusBar().showMessage("部署完成")

        if success:
            QMessageBox.information(
                self,
                "部署成功",
                f"Django项目部署成功！\n\n部署路径: {message}\n\n"
                "应用已通过Gunicorn和Nginx部署，可以使用以下命令管理：\n"
                f"sudo systemctl status <项目名>\n"
                f"sudo systemctl restart <项目名>\n"
                f"sudo systemctl stop <项目名>\n\n"
                f"服务已通过Nginx在80端口提供访问\n"
                f"静态文件和媒体文件已配置"
            )
        else:
            QMessageBox.critical(self, "部署失败", message)

    def deploy_express_project(self):
        """Express项目一键部署"""
        config = self.get_server_config()
        if not config:
            return

        host, username, password, port = config
        project_root = self.project_input.text().strip()

        if not project_root or not Path(project_root).exists():
            QMessageBox.warning(self, "提示", "请选择有效的Express项目目录")
            return

        # 检查是否为有效的Express/Node.js项目
        package_json = Path(project_root) / "package.json"
        if not package_json.exists():
            QMessageBox.warning(
                self,
                "提示",
                "不是有效的Express/Node.js项目\n\n项目目录必须包含package.json文件"
            )
            return

        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认部署",
            f"确定要部署Express项目到服务器 {host} 吗？\n\n"
            f"项目目录: {project_root}\n\n"
            "该操作将：\n"
            "1. 上传项目文件\n"
            "2. 安装PM2进程管理器（如果需要）\n"
            "3. 安装Node.js依赖（npm install）\n"
            "4. 使用PM2启动应用\n"
            "5. 配置Nginx反向代理\n"
            "6. 设置开机自启",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 清空日志
            self.log_output.clear()

            # 禁用按钮
            self.set_inputs_enabled(False)

            # 创建上传器
            self.uploader = ProjectUploader(host, username, password, port)

            # 在后台线程执行
            self.deploy_thread = ExpressDeployThread(self.uploader, project_root)
            self.deploy_thread.log.connect(self.append_log)
            self.deploy_thread.progress.connect(self.update_progress)
            self.deploy_thread.finished.connect(self.express_deploy_finished)
            self.deploy_thread.error.connect(self.upload_error)
            self.deploy_thread.start()

            self.statusBar().showMessage("正在部署Express项目...")

    def express_deploy_finished(self, success: bool, message: str):
        """Express部署完成"""
        self.set_inputs_enabled(True)
        self.statusBar().showMessage("部署完成")

        if success:
            QMessageBox.information(
                self,
                "部署成功",
                f"Express项目部署成功！\n\n部署路径: {message}\n\n"
                "应用已通过PM2和Nginx部署，可以使用以下命令管理：\n"
                f"pm2 status\n"
                f"pm2 restart <项目名>\n"
                f"pm2 stop <项目名>\n"
                f"pm2 logs <项目名>\n\n"
                f"服务已通过Nginx在80端口提供访问\n"
                f"PM2已配置开机自启"
            )
        else:
            QMessageBox.critical(self, "部署失败", message)

    def install_mysql(self):
        """安装MySQL"""
        config = self.get_server_config()
        if not config:
            return

        host, username, password, port = config

        # 弹出密码设置对话框
        dialog = MySQLInstallDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            root_password = dialog.get_password()

            # 确认对话框
            reply = QMessageBox.question(
                self,
                "确认安装",
                f"确定要在服务器 {host} 上安装MySQL吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.log_output.clear()
                self.set_inputs_enabled(False)

                self.uploader = ProjectUploader(host, username, password, port)

                self.install_thread = InstallThread(self.uploader, 'mysql', root_password=root_password)
                self.install_thread.log.connect(self.append_log)
                self.install_thread.progress.connect(self.update_progress)
                self.install_thread.finished.connect(self.install_finished)
                self.install_thread.error.connect(self.upload_error)
                self.install_thread.start()

                self.statusBar().showMessage("正在安装MySQL...")

    def install_redis(self):
        """安装Redis"""
        config = self.get_server_config()
        if not config:
            return

        host, username, password, port = config

        reply = QMessageBox.question(
            self,
            "确认安装",
            f"确定要在服务器 {host} 上安装Redis吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.log_output.clear()
            self.set_inputs_enabled(False)

            self.uploader = ProjectUploader(host, username, password, port)

            self.install_thread = InstallThread(self.uploader, 'redis')
            self.install_thread.log.connect(self.append_log)
            self.install_thread.progress.connect(self.update_progress)
            self.install_thread.finished.connect(self.install_finished)
            self.install_thread.error.connect(self.upload_error)
            self.install_thread.start()

            self.statusBar().showMessage("正在安装Redis...")

    def install_nginx(self):
        """安装Nginx"""
        config = self.get_server_config()
        if not config:
            return

        host, username, password, port = config

        reply = QMessageBox.question(
            self,
            "确认安装",
            f"确定要在服务器 {host} 上安装Nginx吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.log_output.clear()
            self.set_inputs_enabled(False)

            self.uploader = ProjectUploader(host, username, password, port)

            self.install_thread = InstallThread(self.uploader, 'nginx')
            self.install_thread.log.connect(self.append_log)
            self.install_thread.progress.connect(self.update_progress)
            self.install_thread.finished.connect(self.install_finished)
            self.install_thread.error.connect(self.upload_error)
            self.install_thread.start()

            self.statusBar().showMessage("正在安装Nginx...")

    def install_all_environment(self):
        """一键安装全部环境"""
        config = self.get_server_config()
        if not config:
            return

        host, username, password, port = config

        # 弹出MySQL密码设置对话框
        dialog = MySQLInstallDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            root_password = dialog.get_password()

            reply = QMessageBox.question(
                self,
                "确认安装",
                f"确定要在服务器 {host} 上安装全部环境吗？\n\n"
                "将安装：MySQL, Redis, Nginx",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.log_output.clear()
                self.set_inputs_enabled(False)

                self.uploader = ProjectUploader(host, username, password, port)

                self.install_thread = InstallThread(self.uploader, 'all', root_password=root_password)
                self.install_thread.log.connect(self.append_log)
                self.install_thread.progress.connect(self.update_progress)
                self.install_thread.finished.connect(self.install_finished)
                self.install_thread.error.connect(self.upload_error)
                self.install_thread.start()

                self.statusBar().showMessage("正在安装全部环境...")

    def install_mongodb(self):
        """安装MongoDB"""
        self._install_software_with_password(
            software_name="MongoDB",
            software_type="mongodb",
            password_label="MongoDB管理员密码",
            default_password="mongo123"
        )

    def install_postgresql(self):
        """安装PostgreSQL"""
        self._install_software_with_password(
            software_name="PostgreSQL",
            software_type="postgresql",
            password_label="PostgreSQL用户密码",
            default_password="postgres"
        )

    def install_jdk(self):
        """安装JDK"""
        self._install_software_simple("JDK", "jdk")

    def install_python(self):
        """安装Python"""
        self._install_software_simple("Python", "python")

    def install_nodejs(self):
        """安装Node.js"""
        self._install_software_simple("Node.js", "nodejs")

    def install_git(self):
        """安装Git"""
        self._install_software_simple("Git", "git")

    def install_docker(self):
        """安装Docker"""
        self._install_software_simple("Docker", "docker")

    def install_rabbitmq(self):
        """安装RabbitMQ"""
        self._install_software_with_password(
            software_name="RabbitMQ",
            software_type="rabbitmq",
            password_label="RabbitMQ管理员密码",
            default_password="guest"
        )

    def install_web_stack(self):
        """安装Web服务器环境 (Nginx+PHP+MySQL)"""
        self._install_bundle(
            "Web服务器环境",
            ["MySQL", "Redis", "Nginx", "PHP"],
            requires_password=True
        )

    def install_java_stack(self):
        """安装Java开发环境 (JDK+MySQL+Redis)"""
        self._install_bundle(
            "Java开发环境",
            ["JDK", "MySQL", "Redis"],
            requires_password=True
        )

    def install_full_stack(self):
        """安装全栈开发环境"""
        self._install_bundle(
            "全栈开发环境",
            ["MySQL", "Redis", "Nginx", "JDK", "Node.js", "Python", "Docker", "Git"],
            requires_password=True
        )

    def _install_software_with_password(self, software_name, software_type, password_label, default_password):
        """安装需要密码的软件（辅助方法）"""
        config = self.get_server_config()
        if not config:
            return

        host, username, password, port = config

        # 弹出密码设置对话框
        dialog = MySQLInstallDialog(self)
        dialog.setWindowTitle(f"{software_name}配置")
        # 更新对话框标签
        for child in dialog.children():
            if hasattr(child, 'text'):
                if "MySQL" in child.text():
                    child.setText(child.text().replace("MySQL", software_name))
                elif "mysql" in child.text().lower():
                    child.setText(child.text().replace("mysql", software_type.lower()))
                elif "root" in child.text().lower():
                    child.setText(child.text().replace("root", "管理员"))

        dialog.password_input.setText(default_password)
        dialog.confirm_input.setText(default_password)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            root_password = dialog.get_password()

            reply = QMessageBox.question(
                self,
                "确认安装",
                f"确定要在服务器 {host} 上安装{software_name}吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.log_output.clear()
                self.set_inputs_enabled(False)

                self.uploader = ProjectUploader(host, username, password, port)

                self.install_thread = InstallThread(self.uploader, software_type, root_password=root_password)
                self.install_thread.log.connect(self.append_log)
                self.install_thread.progress.connect(self.update_progress)
                self.install_thread.finished.connect(self.install_finished)
                self.install_thread.error.connect(self.upload_error)
                self.install_thread.start()

                self.statusBar().showMessage(f"正在安装{software_name}...")

    def _install_software_simple(self, software_name, software_type):
        """安装不需要密码的软件（辅助方法）"""
        config = self.get_server_config()
        if not config:
            return

        host, username, password, port = config

        reply = QMessageBox.question(
            self,
            "确认安装",
            f"确定要在服务器 {host} 上安装{software_name}吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.log_output.clear()
            self.set_inputs_enabled(False)

            self.uploader = ProjectUploader(host, username, password, port)

            self.install_thread = InstallThread(self.uploader, software_type)
            self.install_thread.log.connect(self.append_log)
            self.install_thread.progress.connect(self.update_progress)
            self.install_thread.finished.connect(self.install_finished)
            self.install_thread.error.connect(self.upload_error)
            self.install_thread.start()

            self.statusBar().showMessage(f"正在安装{software_name}...")

    def _install_bundle(self, bundle_name, software_list, requires_password=False):
        """安装软件组合（辅助方法）"""
        config = self.get_server_config()
        if not config:
            return

        host, username, password, port = config

        software_str = ", ".join(software_list)
        reply = QMessageBox.question(
            self,
            "确认安装",
            f"确定要在服务器 {host} 上安装{bundle_name}吗？\n\n"
            f"将安装：{software_str}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if requires_password:
                # 需要密码，弹出密码设置对话框
                dialog = MySQLInstallDialog(self)
                dialog.setWindowTitle(f"{bundle_name}配置")
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    root_password = dialog.get_password()
                    self._start_bundle_install(bundle_name, software_list, host, username, password, port, root_password)
            else:
                self._start_bundle_install(bundle_name, software_list, host, username, password, port)

    def _start_bundle_install(self, bundle_name, software_list, host, username, password, port, root_password=None):
        """开始安装软件组合"""
        self.log_output.clear()
        self.set_inputs_enabled(False)

        self.uploader = ProjectUploader(host, username, password, port)

        # 使用逗号分隔的软件列表
        software_types = ",".join([s.lower() for s in software_list])

        self.install_thread = InstallThread(self.uploader, software_types, root_password=root_password or "root")
        self.install_thread.log.connect(self.append_log)
        self.install_thread.progress.connect(self.update_progress)
        self.install_thread.finished.connect(self.install_finished)
        self.install_thread.error.connect(self.upload_error)
        self.install_thread.start()

        self.statusBar().showMessage(f"正在安装{bundle_name}...")

    def vue_deploy_finished(self, success: bool, message: str):
        """Vue部署完成"""
        self.set_inputs_enabled(True)
        self.statusBar().showMessage("部署完成")

        if success:
            QMessageBox.information(
                self,
                "部署成功",
                f"Vue项目部署成功！\n\n远程路径: {message}\n\n"
                "请确保服务器防火墙已开放80端口"
            )

    def install_finished(self, success: bool, message: str):
        """环境安装完成"""
        self.set_inputs_enabled(True)
        self.statusBar().showMessage("安装完成")

        if success:
            QMessageBox.information(
                self,
                "安装成功",
                message
            )

    def browse_project(self):
        """浏览项目目录"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择项目目录",
            self.project_input.text()
        )
        if directory:
            self.project_input.setText(directory)

    def test_connection(self):
        """测试服务器连接"""
        config = self.get_server_config()
        if not config:
            return

        host, username, password, port = config

        try:
            self.log_output.append("正在测试服务器连接...")
            self.uploader = ProjectUploader(host, username, password, port)

            if self.uploader.test_connection():
                self.log_output.append("✓ 服务器连接成功")
                QMessageBox.information(self, "成功", "服务器连接成功！")
            else:
                self.log_output.append("✗ 服务器连接失败")
                QMessageBox.critical(self, "失败", "服务器连接失败，请检查配置")

        except Exception as e:
            self.log_output.append(f"✗ 连接测试失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"连接测试失败:\n{str(e)}")

    def start_upload(self):
        """开始上传"""
        # 验证输入
        config = self.get_server_config()
        if not config:
            return

        host, username, password, port = config
        project_root = self.project_input.text().strip()
        remote_dir = self.remote_input.text().strip() or None

        if not project_root:
            QMessageBox.warning(self, "提示", "请选择项目目录")
            return

        if not Path(project_root).exists():
            QMessageBox.warning(self, "提示", "项目目录不存在")
            return

        # 禁用按钮
        self.set_inputs_enabled(False)
        self.upload_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # 清空进度
        self.progress_bar.setValue(0)
        self.stage_label.setText("准备中...")

        # 创建上传器
        self.uploader = ProjectUploader(host, username, password, port)

        # 创建并启动上传线程
        self.upload_thread = UploadThread(self.uploader, project_root, remote_dir)
        self.upload_thread.progress.connect(self.update_progress)
        self.upload_thread.log.connect(self.append_log)
        self.upload_thread.finished.connect(self.upload_finished)
        self.upload_thread.error.connect(self.upload_error)
        self.upload_thread.start()

        self.statusBar().showMessage("正在上传...")

    def stop_upload(self):
        """停止上传"""
        if self.upload_thread and self.upload_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "确认",
                "确定要停止上传吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.upload_thread.stop()
                self.append_log("上传已取消")
                self.set_inputs_enabled(True)
                self.upload_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)
                self.statusBar().showMessage("上传已取消")

    @Slot(str, int, int)
    def update_progress(self, stage: str, current: int, total: int):
        """更新进度"""
        self.stage_label.setText(stage)

        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)
            self.progress_detail.setText(f"{current}/{total} ({percent}%)")
        else:
            self.progress_detail.setText(f"{current}")

    @Slot(str)
    def append_log(self, message: str):
        """添加日志"""
        self.log_output.append(message)
        # 滚动到底部
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_log(self):
        """清除日志"""
        self.log_output.clear()

    @Slot(bool, str)
    def upload_finished(self, success: bool, message: str):
        """上传完成"""
        self.set_inputs_enabled(True)
        self.upload_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.statusBar().showMessage("上传完成")

        if success:
            self.progress_bar.setValue(100)
            QMessageBox.information(
                self,
                "成功",
                f"项目上传成功！\n\n远程路径: {message}"
            )

    @Slot(str)
    def upload_error(self, error_message: str):
        """上传错误"""
        self.set_inputs_enabled(True)
        self.upload_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.statusBar().showMessage("上传失败")

        self.log_output.append(f"✗ {error_message}")
        QMessageBox.critical(self, "错误", error_message)

    def set_inputs_enabled(self, enabled: bool):
        """设置输入控件是否可用"""
        self.project_input.setEnabled(enabled)
        self.browse_btn.setEnabled(enabled)
        self.remote_input.setEnabled(enabled)
        self.switch_server_btn.setEnabled(enabled)
        self.test_connection_btn.setEnabled(enabled)
