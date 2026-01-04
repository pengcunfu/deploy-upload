#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeployUpload GUI - 图形界面

使用PySide6实现的Windows Vista风格图形界面
"""

import sys
import os
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLineEdit, QPushButton, QLabel, QTextEdit,
    QProgressBar, QFileDialog, QSpinBox, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont, QIcon, QPalette, QColor
from uploader import ProjectUploader


class UploadThread(QThread):
    """上传工作线程"""

    # 定义信号
    progress = Signal(str, int, int)  # 阶段, 当前进度, 总进度
    log = Signal(str)  # 日志消息
    finished = Signal(bool, str)  # 完成, 消息
    error = Signal(str)  # 错误消息

    def __init__(self, uploader: ProjectUploader, project_root: str, remote_dir: Optional[str] = None):
        super().__init__()
        self.uploader = uploader
        self.project_root = project_root
        self.remote_dir = remote_dir
        self._is_running = True

    def run(self):
        """执行上传任务"""
        try:
            self.log.emit("开始上传任务...")
            self.log.emit(f"项目根目录: {self.project_root}")

            # 测试连接
            self.log.emit("正在测试服务器连接...")
            if not self.uploader.test_connection():
                self.error.emit("服务器连接失败，请检查服务器信息")
                return
            self.log.emit("✓ 服务器连接成功")

            # 上传项目
            self.log.emit("开始打包并上传项目...")

            def progress_callback(stage: str, current: int, total: int):
                """进度回调函数"""
                self.progress.emit(stage, current, total)
                if total > 0 and current == total:
                    self.log.emit(f"✓ {stage} 完成")

            remote_path = self.uploader.upload_and_extract(
                self.project_root,
                self.remote_dir,
                progress_callback=progress_callback
            )

            self.log.emit(f"✓ 项目上传完成")
            self.log.emit(f"远程项目路径: {remote_path}")
            self.finished.emit(True, remote_path)

        except Exception as e:
            self.error.emit(f"上传失败: {str(e)}")

    def stop(self):
        """停止上传"""
        self._is_running = False
        self.quit()


class DeployUploadWindow(QMainWindow):
    """DeployUpload 主窗口"""

    def __init__(self):
        super().__init__()
        self.uploader: Optional[ProjectUploader] = None
        self.upload_thread: Optional[UploadThread] = None
        self.init_ui()
        self.apply_vista_style()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("DeployUpload - 项目部署工具")
        self.setMinimumSize(700, 650)

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

        # 设置状态栏
        self.statusBar().showMessage("就绪")

    def create_server_config_group(self) -> QGroupBox:
        """创建服务器配置组"""
        group = QGroupBox("服务器配置")
        group.setStyleSheet("QGroupBox { font-weight: bold; }")

        layout = QVBoxLayout()
        layout.setSpacing(10)

        # 主机地址
        host_layout = QHBoxLayout()
        host_label = QLabel("主机地址:")
        host_label.setMinimumWidth(80)
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("例如: 192.168.1.100")
        host_layout.addWidget(host_label)
        host_layout.addWidget(self.host_input)
        layout.addLayout(host_layout)

        # 用户名和密码
        auth_layout = QHBoxLayout()
        username_label = QLabel("用户名:")
        username_label.setMinimumWidth(80)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("例如: ubuntu")
        auth_layout.addWidget(username_label)
        auth_layout.addWidget(self.username_input)

        password_label = QLabel("密码:")
        password_label.setMinimumWidth(60)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("服务器登录密码")
        auth_layout.addWidget(password_label)
        auth_layout.addWidget(self.password_input)
        layout.addLayout(auth_layout)

        # 端口
        port_layout = QHBoxLayout()
        port_label = QLabel("SSH端口:")
        port_label.setMinimumWidth(80)
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(22)
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_input)
        port_layout.addStretch()
        layout.addLayout(port_layout)

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
        group.setStyleSheet("QGroupBox { font-weight: bold; }")

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
        group.setStyleSheet("QGroupBox { font-weight: bold; }")

        layout = QVBoxLayout()
        layout.setSpacing(10)

        # 当前阶段
        self.stage_label = QLabel("就绪")
        self.stage_label.setStyleSheet("font-weight: bold; color: #333;")
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
        self.progress_detail.setStyleSheet("color: #666;")
        detail_layout.addWidget(detail_label)
        detail_layout.addWidget(self.progress_detail)
        layout.addLayout(detail_layout)

        group.setLayout(layout)
        return group

    def create_log_group(self) -> QGroupBox:
        """创建日志输出组"""
        group = QGroupBox("日志输出")
        group.setStyleSheet("QGroupBox { font-weight: bold; }")

        layout = QVBoxLayout()

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(180)
        self.log_output.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9pt;
                border: 1px solid #444;
            }
        """)

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
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 3px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QPushButton:pressed {
                background-color: #004578;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.upload_btn.clicked.connect(self.start_upload)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.setMinimumHeight(35)
        self.stop_btn.setMinimumWidth(100)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #d13438;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 3px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #a82628;
            }
            QPushButton:pressed {
                background-color: #7e1c1e;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_upload)

        layout.addWidget(self.upload_btn)
        layout.addWidget(self.stop_btn)
        widget.setLayout(layout)
        return widget

    def apply_vista_style(self):
        """应用Windows Vista风格"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QGroupBox {
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLineEdit {
                border: 1px solid #7a7a7a;
                border-radius: 3px;
                padding: 4px;
                background-color: white;
                min-height: 20px;
            }
            QLineEdit:focus {
                border: 1px solid #3399ff;
            }
            QPushButton {
                background-color: #f5f5f5;
                border: 1px solid #d9d9d9;
                border-radius: 3px;
                padding: 5px 15px;
                min-height: 23px;
            }
            QPushButton:hover {
                background-color: #e5f3ff;
                border: 1px solid #0078d7;
            }
            QPushButton:pressed {
                background-color: #cce8ff;
            }
            QPushButton:disabled {
                background-color: #f0f0f0;
                color: #a0a0a0;
                border: 1px solid #e0e0e0;
            }
            QSpinBox {
                border: 1px solid #7a7a7a;
                border-radius: 3px;
                padding: 4px;
                background-color: white;
                min-height: 20px;
            }
            QSpinBox:focus {
                border: 1px solid #3399ff;
            }
            QProgressBar {
                border: 1px solid #7a7a7a;
                border-radius: 3px;
                background-color: #f0f0f0;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #0078d7;
                border-radius: 2px;
            }
            QLabel {
                color: #333333;
            }
        """)

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
        host = self.host_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text()
        port = self.port_input.value()

        if not all([host, username, password]):
            QMessageBox.warning(self, "提示", "请填写完整的服务器信息")
            return

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
        host = self.host_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text()
        port = self.port_input.value()
        project_root = self.project_input.text().strip()
        remote_dir = self.remote_input.text().strip() or None

        if not all([host, username, password, project_root]):
            QMessageBox.warning(self, "提示", "请填写完整的服务器信息和项目目录")
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
        self.host_input.setEnabled(enabled)
        self.username_input.setEnabled(enabled)
        self.password_input.setEnabled(enabled)
        self.port_input.setEnabled(enabled)
        self.project_input.setEnabled(enabled)
        self.browse_btn.setEnabled(enabled)
        self.remote_input.setEnabled(enabled)
        self.test_connection_btn.setEnabled(enabled)


def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 设置应用程序信息
    app.setApplicationName("DeployUpload")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("DeployUpload")

    # 创建并显示主窗口
    window = DeployUploadWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
