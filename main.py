#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeployUpload - 主程序入口

项目部署工具的图形界面启动入口
"""

import sys
from PySide6.QtWidgets import QApplication, QStyleFactory
from app.window import DeployUploadWindow


def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 设置应用程序信息
    app.setApplicationName("DeployUpload")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("DeployUpload")

    # 设置Windows Vista风格
    app.setStyle(QStyleFactory.create("windowsvista"))

    # 先创建并显示主窗口
    window = DeployUploadWindow()
    window.show()

    # 显示服务器选择对话框（在主窗口之上）
    window.select_server_on_startup()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
