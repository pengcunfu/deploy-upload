#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务器配置管理模块

包含服务器配置类和配置管理器
"""

import json
from pathlib import Path
from typing import List, Optional
from .server_types import ServerType

# 服务器配置文件路径
SERVER_CONFIG_FILE = Path.home() / '.deployupload_servers.json'


class ServerConfig:
    """服务器配置类"""

    def __init__(
        self,
        name: str,
        host: str,
        username: str,
        password: str,
        port: int = 22,
        server_type: ServerType = ServerType.UBUNTU
    ):
        self.name = name
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.server_type = server_type

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'name': self.name,
            'host': self.host,
            'username': self.username,
            'password': self.password,
            'port': self.port,
            'server_type': self.server_type.value
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ServerConfig':
        """从字典创建"""
        server_type_str = data.get('server_type', 'Ubuntu')
        # 兼容旧配置，如果没有服务器类型，默认为Ubuntu
        try:
            server_type = ServerType(server_type_str)
        except ValueError:
            server_type = ServerType.UBUNTU

        return cls(
            name=data['name'],
            host=data['host'],
            username=data['username'],
            password=data['password'],
            port=data.get('port', 22),
            server_type=server_type
        )

    def __repr__(self):
        return f"ServerConfig(name='{self.name}', host='{self.host}', username='{self.username}', port={self.port}, type={self.server_type.value})"


class ServerConfigManager:
    """服务器配置管理器"""

    @staticmethod
    def load_servers() -> List[ServerConfig]:
        """加载服务器配置"""
        if not SERVER_CONFIG_FILE.exists():
            return []

        try:
            with open(SERVER_CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [ServerConfig.from_dict(item) for item in data]
        except Exception:
            return []

    @staticmethod
    def save_servers(servers: List[ServerConfig]):
        """保存服务器配置"""
        try:
            with open(SERVER_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump([s.to_dict() for s in servers], f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"保存配置失败: {str(e)}")
