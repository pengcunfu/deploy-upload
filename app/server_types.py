#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务器类型和软件安装配置

定义常见的服务器操作系统和可安装的软件
"""

from typing import List, Dict, Callable, Optional
from enum import Enum


class ServerType(Enum):
    """服务器操作系统类型"""
    UBUNTU = "Ubuntu"
    DEBIAN = "Debian"
    CENTOS = "CentOS"
    REDHAT = "RedHat"
    FEDORA = "Fedora"
    AMAZON_LINUX = "Amazon Linux"
    ROCKY_LINUX = "Rocky Linux"
    ALMA_LINUX = "Alma Linux"
    ARCH_LINUX = "Arch Linux"
    OPENSUSE = "openSUSE"


class SoftwareType(Enum):
    """可安装的软件类型"""
    MYSQL = "MySQL"
    REDIS = "Redis"
    NGINX = "Nginx"
    JDK = "JDK"
    DOCKER = "Docker"
    GIT = "Git"
    PYTHON = "Python"
    PHP = "PHP"
    NODEJS = "Node.js"
    MONGODB = "MongoDB"
    POSTGRESQL = "PostgreSQL"
    RABBITMQ = "RabbitMQ"


# 软件描述信息
SOFTWARE_INFO = {
    SoftwareType.MYSQL: {
        "name": "MySQL",
        "description": "流行的关系型数据库管理系统",
        "default_version": "8.0",
        "requires_password": True,
        "password_label": "MySQL root密码"
    },
    SoftwareType.REDIS: {
        "name": "Redis",
        "description": "高性能的键值对数据库",
        "default_version": "latest",
        "requires_password": False,
    },
    SoftwareType.NGINX: {
        "name": "Nginx",
        "description": "高性能的Web服务器和反向代理",
        "default_version": "latest",
        "requires_password": False,
    },
    SoftwareType.JDK: {
        "name": "JDK",
        "description": "Java开发工具包",
        "default_version": "11",
        "requires_password": False,
    },
    SoftwareType.DOCKER: {
        "name": "Docker",
        "description": "容器化平台",
        "default_version": "latest",
        "requires_password": False,
    },
    SoftwareType.GIT: {
        "name": "Git",
        "description": "分布式版本控制系统",
        "default_version": "latest",
        "requires_password": False,
    },
    SoftwareType.PYTHON: {
        "name": "Python",
        "description": "Python编程语言",
        "default_version": "3",
        "requires_password": False,
    },
    SoftwareType.PHP: {
        "name": "PHP",
        "description": "通用脚本语言",
        "default_version": "8",
        "requires_password": False,
    },
    SoftwareType.NODEJS: {
        "name": "Node.js",
        "description": "JavaScript运行时",
        "default_version": "18",
        "requires_password": False,
    },
    SoftwareType.MONGODB: {
        "name": "MongoDB",
        "description": "NoSQL文档数据库",
        "default_version": "6.0",
        "requires_password": True,
        "password_label": "MongoDB管理员密码"
    },
    SoftwareType.POSTGRESQL: {
        "name": "PostgreSQL",
        "description": "高级关系型数据库",
        "default_version": "14",
        "requires_password": True,
        "password_label": "PostgreSQL用户密码"
    },
    SoftwareType.RABBITMQ: {
        "name": "RabbitMQ",
        "description": "消息队列中间件",
        "default_version": "3",
        "requires_password": True,
        "password_label": "RabbitMQ管理员密码"
    },
}


# 不同操作系统支持的软件包管理器
PACKAGE_MANAGERS = {
    # Debian/Ubuntu 系列 (使用 apt)
    ServerType.UBUNTU: "apt",
    ServerType.DEBIAN: "apt",

    # RHEL/CentOS/Fedora 系列 (使用 yum 或 dnf)
    ServerType.CENTOS: "yum",
    ServerType.REDHAT: "yum",
    ServerType.FEDORA: "dnf",
    ServerType.AMAZON_LINUX: "yum",
    ServerType.ROCKY_LINUX: "dnf",
    ServerType.ALMA_LINUX: "dnf",

    # Arch Linux (使用 pacman)
    ServerType.ARCH_LINUX: "pacman",

    # openSUSE (使用 zypper)
    ServerType.OPENSUSE: "zypper",
}


def get_supported_software(server_type: ServerType) -> List[SoftwareType]:
    """获取指定服务器类型支持的软件列表"""
    # 所有系统都支持的软件
    common_software = [
        SoftwareType.GIT,
        SoftwareType.PYTHON,
        SoftwareType.DOCKER,
    ]

    # 根据包管理器返回支持列表
    pkg_manager = PACKAGE_MANAGERS.get(server_type, "apt")

    if pkg_manager in ["apt"]:
        return [
            *common_software,
            SoftwareType.MYSQL,
            SoftwareType.REDIS,
            SoftwareType.NGINX,
            SoftwareType.JDK,
            SoftwareType.NODEJS,
            SoftwareType.MONGODB,
            SoftwareType.POSTGRESQL,
            SoftwareType.RABBITMQ,
        ]
    elif pkg_manager in ["yum", "dnf"]:
        return [
            *common_software,
            SoftwareType.MYSQL,
            SoftwareType.REDIS,
            SoftwareType.NGINX,
            SoftwareType.JDK,
            SoftwareType.NODEJS,
            SoftwareType.MONGODB,
            SoftwareType.POSTGRESQL,
            SoftwareType.RABBITMQ,
        ]
    elif pkg_manager == "pacman":
        return [
            *common_software,
            SoftwareType.MYSQL,
            SoftwareType.REDIS,
            SoftwareType.NGINX,
            SoftwareType.JDK,
            SoftwareType.NODEJS,
        ]
    elif pkg_manager == "zypper":
        return [
            *common_software,
            SoftwareType.MYSQL,
            SoftwareType.REDIS,
            SoftwareType.NGINX,
            SoftwareType.JDK,
            SoftwareType.NODEJS,
            SoftwareType.POSTGRESQL,
        ]
    else:
        return common_software


def get_install_command(
    server_type: ServerType,
    software: SoftwareType,
    version: Optional[str] = None,
    password: Optional[str] = None
) -> str:
    """
    获取软件安装命令

    Args:
        server_type: 服务器类型
        software: 要安装的软件
        version: 软件版本（可选）
        password: 密码（如果需要）

    Returns:
        安装命令字符串
    """
    pkg_manager = PACKAGE_MANAGERS.get(server_type, "apt")
    cmd_parts = []

    # 基础命令：更新包列表
    if pkg_manager == "apt":
        cmd_parts.append("apt-get update")
    elif pkg_manager == "yum":
        cmd_parts.append("yum makecache")
    elif pkg_manager == "dnf":
        cmd_parts.append("dnf makecache")
    elif pkg_manager == "pacman":
        cmd_parts.append("pacman -Sy")
    elif pkg_manager == "zypper":
        cmd_parts.append("zypper refresh")

    # 安装软件的命令
    install_cmd = f"install_{software.name.lower()}"
    install_cmd = install_cmd + f"_{server_type.name.lower()}"
    install_cmd = install_cmd + f"_{pkg_manager}"

    cmd_parts.append(install_cmd)

    return " && ".join(cmd_parts)


# 预定义的软件安装组合
SOFTWARE_BUNDLES = {
    "web_server": {
        "name": "Web服务器",
        "description": "基础的Web服务器环境",
        "software": [SoftwareType.NGINX, SoftwareType.PHP],
    },
    "database": {
        "name": "数据库服务器",
        "description": "完整的数据库环境",
        "software": [SoftwareType.MYSQL, SoftwareType.REDIS],
    },
    "java_development": {
        "name": "Java开发环境",
        "description": "Java应用开发所需环境",
        "software": [SoftwareType.JDK, SoftwareType.MYSQL, SoftwareType.REDIS],
    },
    "docker_deployment": {
        "name": "Docker部署环境",
        "description": "容器化部署所需环境",
        "software": [SoftwareType.DOCKER, SoftwareType.GIT],
    },
    "full_stack": {
        "name": "全栈开发环境",
        "description": "完整的全栈开发环境",
        "software": [
            SoftwareType.MYSQL,
            SoftwareType.REDIS,
            SoftwareType.NGINX,
            SoftwareType.NODEJS,
            SoftwareType.PYTHON,
            SoftwareType.DOCKER,
            SoftwareType.GIT,
        ],
    },
}
