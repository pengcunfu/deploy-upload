#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作线程模块

包含上传、部署和安装的工作线程
"""

from typing import Optional
from PySide6.QtCore import QThread, Signal
from .uploader import ProjectUploader
from .server_config import ServerConfig


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


class VueDeployThread(QThread):
    """Vue部署线程"""

    log = Signal(str)
    progress = Signal(str, int, int)
    finished = Signal(bool, str)
    error = Signal(str)

    def __init__(self, uploader: ProjectUploader, config: dict):
        super().__init__()
        self.uploader = uploader
        self.config = config

    def run(self):
        """执行Vue部署"""
        try:
            self.log.emit("开始部署Vue项目...")

            def progress_callback(stage, current, total):
                self.progress.emit(stage, current, total)
                if total > 0 and current == total:
                    self.log.emit(f"✓ {stage} 完成")
                else:
                    self.log.emit(f"{stage}...")

            remote_path = self.uploader.deploy_vue_project(
                project_root=self.config.get("project_root", ""),
                remote_dir=self.config.get("remote_dir"),
                build_command=self.config.get("build_command", "npm run build"),
                nginx_port=self.config.get("nginx_port", 80),
                server_name=self.config.get("server_name", "_"),
                enable_ssl=self.config.get("enable_ssl", False),
                proxy_configs=self.config.get("proxy_configs", []),
                auto_install=self.config.get("auto_install", True),
                clean_build=self.config.get("clean_build", False),
                progress_callback=progress_callback
            )

            self.log.emit("✓ Vue项目部署完成")
            self.finished.emit(True, remote_path)

        except Exception as e:
            error_msg = str(e)
            self.log.emit(f"✗ 部署失败: {error_msg}")
            self.error.emit(error_msg)


class SpringBootDeployThread(QThread):
    """SpringBoot部署线程"""

    log = Signal(str)
    progress = Signal(str, int, int)
    finished = Signal(bool, str)
    error = Signal(str)

    def __init__(self, uploader: ProjectUploader, project_root: str):
        super().__init__()
        self.uploader = uploader
        self.project_root = project_root

    def run(self):
        """执行SpringBoot部署"""
        try:
            self.log.emit("开始部署SpringBoot项目...")

            def progress_callback(stage, current, total):
                self.progress.emit(stage, current, total)
                if total > 0 and current == total:
                    self.log.emit(f"✓ {stage} 完成")
                else:
                    self.log.emit(f"{stage}...")

            remote_path = self.uploader.deploy_springboot_project(
                self.project_root,
                progress_callback=progress_callback
            )

            self.log.emit("✓ SpringBoot项目部署完成")
            self.finished.emit(True, remote_path)

        except Exception as e:
            error_msg = str(e)
            self.log.emit(f"✗ 部署失败: {error_msg}")
            self.error.emit(error_msg)


class FlaskDeployThread(QThread):
    """Flask部署线程"""

    log = Signal(str)
    progress = Signal(str, int, int)
    finished = Signal(bool, str)
    error = Signal(str)

    def __init__(self, uploader: ProjectUploader, project_root: str):
        super().__init__()
        self.uploader = uploader
        self.project_root = project_root

    def run(self):
        """执行Flask部署"""
        try:
            self.log.emit("开始部署Flask项目...")

            def progress_callback(stage, current, total):
                self.progress.emit(stage, current, total)
                if total > 0 and current == total:
                    self.log.emit(f"✓ {stage} 完成")
                else:
                    self.log.emit(f"{stage}...")

            remote_path = self.uploader.deploy_flask_project(
                self.project_root,
                progress_callback=progress_callback
            )

            self.log.emit("✓ Flask项目部署完成")
            self.finished.emit(True, remote_path)

        except Exception as e:
            error_msg = str(e)
            self.log.emit(f"✗ 部署失败: {error_msg}")
            self.error.emit(error_msg)


class DjangoDeployThread(QThread):
    """Django部署线程"""

    log = Signal(str)
    progress = Signal(str, int, int)
    finished = Signal(bool, str)
    error = Signal(str)

    def __init__(self, uploader: ProjectUploader, project_root: str):
        super().__init__()
        self.uploader = uploader
        self.project_root = project_root

    def run(self):
        """执行Django部署"""
        try:
            self.log.emit("开始部署Django项目...")

            def progress_callback(stage, current, total):
                self.progress.emit(stage, current, total)
                if total > 0 and current == total:
                    self.log.emit(f"✓ {stage} 完成")
                else:
                    self.log.emit(f"{stage}...")

            remote_path = self.uploader.deploy_django_project(
                self.project_root,
                progress_callback=progress_callback
            )

            self.log.emit("✓ Django项目部署完成")
            self.finished.emit(True, remote_path)

        except Exception as e:
            error_msg = str(e)
            self.log.emit(f"✗ 部署失败: {error_msg}")
            self.error.emit(error_msg)


class ExpressDeployThread(QThread):
    """Express部署线程"""

    log = Signal(str)
    progress = Signal(str, int, int)
    finished = Signal(bool, str)
    error = Signal(str)

    def __init__(self, uploader: ProjectUploader, project_root: str):
        super().__init__()
        self.uploader = uploader
        self.project_root = project_root

    def run(self):
        """执行Express部署"""
        try:
            self.log.emit("开始部署Express项目...")

            def progress_callback(stage, current, total):
                self.progress.emit(stage, current, total)
                if total > 0 and current == total:
                    self.log.emit(f"✓ {stage} 完成")
                else:
                    self.log.emit(f"{stage}...")

            remote_path = self.uploader.deploy_express_project(
                self.project_root,
                progress_callback=progress_callback
            )

            self.log.emit("✓ Express项目部署完成")
            self.finished.emit(True, remote_path)

        except Exception as e:
            error_msg = str(e)
            self.log.emit(f"✗ 部署失败: {error_msg}")
            self.error.emit(error_msg)


class InstallThread(QThread):
    """环境安装线程"""

    log = Signal(str)
    progress = Signal(str, int, int)
    finished = Signal(bool, str)
    error = Signal(str)

    def __init__(self, uploader: ProjectUploader, install_type: str, root_password: str = 'root'):
        super().__init__()
        self.uploader = uploader
        self.install_type = install_type
        self.root_password = root_password

    def run(self):
        """执行环境安装"""
        try:
            def progress_callback(stage, current, total):
                self.progress.emit(stage, current, total)
                if total > 0 and current == total:
                    self.log.emit(f"✓ {stage} 完成")
                else:
                    self.log.emit(f"{stage}...")

            if self.install_type == 'mysql':
                self.log.emit("开始安装MySQL...")
                self.uploader.install_mysql(self.root_password, progress_callback)
                self.log.emit("✓ MySQL安装完成")
                self.finished.emit(True, "MySQL安装成功！\n\n请使用以下信息连接：\n用户名: root\n密码: " + self.root_password)

            elif self.install_type == 'redis':
                self.log.emit("开始安装Redis...")
                self.uploader.install_redis(progress_callback)
                self.log.emit("✓ Redis安装完成")
                self.finished.emit(True, "Redis安装成功！\n\n服务已自动启动")

            elif self.install_type == 'nginx':
                self.log.emit("开始安装Nginx...")
                self.uploader.install_nginx(progress_callback)
                self.log.emit("✓ Nginx安装完成")
                self.finished.emit(True, "Nginx安装成功！\n\n服务已自动启动\n默认监听端口: 80")

            elif self.install_type == 'all':
                self.log.emit("开始安装全部环境...")
                self.log.emit("1/3 安装MySQL...")
                self.uploader.install_mysql(self.root_password, progress_callback)
                self.log.emit("✓ MySQL安装完成")

                self.log.emit("2/3 安装Redis...")
                self.uploader.install_redis(progress_callback)
                self.log.emit("✓ Redis安装完成")

                self.log.emit("3/3 安装Nginx...")
                self.uploader.install_nginx(progress_callback)
                self.log.emit("✓ Nginx安装完成")

                self.finished.emit(True, "全部环境安装成功！\n\n已安装：\n- MySQL\n- Redis\n- Nginx\n\n所有服务已自动启动")

        except Exception as e:
            error_msg = str(e)
            self.log.emit(f"✗ 安装失败: {error_msg}")
            self.error.emit(error_msg)
