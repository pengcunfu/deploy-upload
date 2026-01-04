#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目文件夹上传器

提供ProjectUploader类，用于将本地文件夹打包并上传到远程服务器。
"""

import os
import sys
import tarfile
import tempfile
import shutil
import time
from pathlib import Path
from typing import Set, List, Callable, Optional, Dict, Any
import paramiko
from tqdm import tqdm


class ProjectUploader:
    """
    项目文件夹上传器
    
    用于将本地文件夹打包并上传到远程服务器的工具类。
    支持.gitignore文件过滤、进度回调等功能。
    """
    
    def __init__(self, host: str, username: str, password: str, port: int = 22):
        """
        初始化上传器
        
        Args:
            host (str): 服务器IP地址或域名
            username (str): 服务器用户名
            password (str): 服务器密码
            port (int, optional): SSH端口. 默认为22.
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        
        # 内部状态
        self._ignored_patterns: Set[str] = set()
        self._ignored_files: Set[str] = set()
        
    def set_ignore_patterns(self, patterns: List[str]) -> None:
        """
        设置额外的忽略模式
        
        Args:
            patterns (List[str]): 忽略模式列表
        """
        self._ignored_patterns.update(patterns)
    
    def set_ignore_files(self, files: List[str]) -> None:
        """
        设置额外的忽略文件
        
        Args:
            files (List[str]): 忽略文件列表
        """
        self._ignored_files.update(files)
    
    def _collect_gitignore_patterns(self, directory: Path) -> None:
        """
        收集指定目录及其子目录中的所有.gitignore文件中的忽略模式
        
        Args:
            directory (Path): 要扫描的目录
        """
        gitignore_file = directory / '.gitignore'
        deploy_ignore_file = directory / '.deploy_ignore'
        
        # 处理.gitignore文件
        if gitignore_file.exists():
            self._parse_ignore_file(gitignore_file, directory)
        
        # 处理.deploy_ignore文件
        if deploy_ignore_file.exists():
            self._parse_ignore_file(deploy_ignore_file, directory)
        
        # 递归处理子目录
        for item in directory.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                self._collect_gitignore_patterns(item)
    
    def _parse_ignore_file(self, ignore_file: Path, base_directory: Path) -> None:
        """
        解析忽略文件
        
        Args:
            ignore_file (Path): 忽略文件路径
            base_directory (Path): 基础目录
        """
        try:
            with open(ignore_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # 处理相对路径模式
                        if line.startswith('/'):
                            # 绝对路径模式，相对于项目根目录
                            pattern = str(base_directory / line[1:])
                        elif line.startswith('**/'):
                            # 递归匹配模式
                            pattern = str(base_directory / line[3:])
                        elif line.startswith('./'):
                            # 当前目录模式
                            pattern = str(base_directory / line[2:])
                        else:
                            # 相对路径模式
                            pattern = str(base_directory / line)
                        
                        self._ignored_patterns.add(pattern)
        except Exception as e:
            print(f"警告: 读取 {ignore_file} 失败: {e}")
    
    def _should_ignore_file(self, file_path: Path) -> bool:
        """
        判断文件是否应该被忽略
        
        Args:
            file_path (Path): 文件路径
            
        Returns:
            bool: 是否应该忽略
        """
        file_str = str(file_path)
        
        # 检查是否匹配忽略模式
        for pattern in self._ignored_patterns:
            if file_path.match(pattern) or file_str.startswith(pattern):
                return True
        
        # 检查是否在忽略文件列表中
        if file_str in self._ignored_files:
            return True
        
        # 检查常见的系统文件
        ignore_names = {'.DS_Store', 'Thumbs.db', '.git', '.svn', '__pycache__'}
        if file_path.name in ignore_names:
            return True
            
        return False
    
    def create_archive(self, 
                      project_root: str, 
                      output_path: Optional[str] = None,
                      progress_callback: Optional[Callable[[str, int, int], None]] = None) -> str:
        """
        创建项目压缩包，忽略指定的文件
        
        Args:
            project_root (str): 项目根目录路径
            output_path (str, optional): 输出压缩包路径. 如果为None，将使用项目名.tar.gz
            progress_callback (Callable, optional): 进度回调函数，参数为(阶段, 当前进度, 总进度)
                
        Returns:
            str: 创建的压缩包路径
        """
        project_root = Path(project_root).resolve()
        
        if progress_callback:
            progress_callback("收集忽略模式", 0, 100)
        
        # 清空之前的忽略模式
        self._ignored_patterns.clear()
        
        # 收集.gitignore模式
        self._collect_gitignore_patterns(project_root)
        
        if progress_callback:
            progress_callback("收集忽略模式", 100, 100)
        
        # 设置输出路径
        if output_path is None:
            output_path = f"{project_root.name}.tar.gz"
        
        # 创建临时目录
        temp_dir = Path(tempfile.mkdtemp())
        project_name = project_root.name
        archive_dir = temp_dir / project_name
        
        try:
            # 复制项目文件到临时目录，忽略指定的文件
            total_files = 0
            copied_files = 0
            
            if progress_callback:
                progress_callback("计算文件数量", 0, 100)
            
            # 首先计算总文件数
            for root, dirs, files in os.walk(project_root):
                root_path = Path(root)
                for file in files:
                    file_path = root_path / file
                    if not self._should_ignore_file(file_path):
                        total_files += 1
            
            if progress_callback:
                progress_callback("计算文件数量", 100, 100)
            
            # 复制文件
            for root, dirs, files in os.walk(project_root):
                root_path = Path(root)
                rel_root = root_path.relative_to(project_root)
                target_dir = archive_dir / rel_root
                
                # 创建目标目录
                target_dir.mkdir(parents=True, exist_ok=True)
                
                for file in files:
                    file_path = root_path / file
                    
                    if not self._should_ignore_file(file_path):
                        target_file = target_dir / file
                        shutil.copy2(file_path, target_file)
                        copied_files += 1
                        
                        if progress_callback:
                            progress_callback("复制文件", copied_files, total_files)
            
            if progress_callback:
                progress_callback("创建压缩包", 0, 100)
            
            # 创建tar.gz压缩包
            with tarfile.open(output_path, 'w:gz') as tar:
                tar.add(archive_dir, arcname=project_name)
            
            if progress_callback:
                progress_callback("创建压缩包", 100, 100)
            
            return output_path
            
        finally:
            # 清理临时目录
            shutil.rmtree(temp_dir)
    
    def upload_file(self, 
                   local_path: str, 
                   remote_path: Optional[str] = None,
                   progress_callback: Optional[Callable[[str, int, int], None]] = None) -> str:
        """
        上传文件到服务器
        
        Args:
            local_path (str): 本地文件路径
            remote_path (str, optional): 远程文件路径. 如果为None，将上传到用户home目录
            progress_callback (Callable, optional): 进度回调函数，参数为(阶段, 当前进度, 总进度)
            
        Returns:
            str: 远程文件路径
        """
        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(f"本地文件不存在: {local_path}")
        
        if remote_path is None:
            remote_path = f"/home/{self.username}/{local_path.name}"
        
        if progress_callback:
            progress_callback("连接服务器", 0, 100)
        
        try:
            # 创建SSH客户端
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.host, self.port, self.username, self.password, timeout=30)
            
            if progress_callback:
                progress_callback("连接服务器", 100, 100)
            
            # 创建SFTP客户端
            sftp = ssh.open_sftp()
            
            # 获取文件大小
            file_size = local_path.stat().st_size
            
            if progress_callback:
                progress_callback("上传文件", 0, file_size)
            
            # 上传文件
            def sftp_progress_callback(transferred, to_be_transferred):
                if progress_callback:
                    progress_callback("上传文件", transferred, to_be_transferred)
            
            sftp.put(str(local_path), remote_path, callback=sftp_progress_callback)
            
            # 清理
            sftp.close()
            ssh.close()
            
            return remote_path
            
        except Exception as e:
            raise Exception(f"上传失败: {str(e)}")
    
    def upload_and_extract(self, 
                          project_root: str,
                          remote_dir: Optional[str] = None,
                          progress_callback: Optional[Callable[[str, int, int], None]] = None) -> str:
        """
        打包、上传并解压项目文件夹
        
        Args:
            project_root (str): 项目根目录路径
            remote_dir (str, optional): 远程解压目录. 如果为None，将解压到用户home目录
            progress_callback (Callable, optional): 进度回调函数，参数为(阶段, 当前进度, 总进度)
            
        Returns:
            str: 远程解压后的项目目录路径
        """
        project_root = Path(project_root).resolve()
        
        if remote_dir is None:
            remote_dir = f"/home/{self.username}"
        
        try:
            # 创建压缩包
            archive_path = self.create_archive(
                str(project_root), 
                progress_callback=progress_callback
            )
            
            # 上传压缩包
            remote_archive_path = self.upload_file(
                archive_path,
                f"{remote_dir}/{Path(archive_path).name}",
                progress_callback=progress_callback
            )
            
            if progress_callback:
                progress_callback("解压文件", 0, 100)
            
            # 连接服务器并解压
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.host, self.port, self.username, self.password, timeout=30)
            
            # 解压文件
            extract_cmd = f"cd {remote_dir} && tar -xzf {Path(remote_archive_path).name} && rm {Path(remote_archive_path).name}"
            stdin, stdout, stderr = ssh.exec_command(extract_cmd)
            
            # 等待解压完成
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                error = stderr.read().decode()
                raise Exception(f"解压失败: {error}")
            
            ssh.close()
            
            if progress_callback:
                progress_callback("解压文件", 100, 100)
            
            # 清理本地压缩包
            if os.path.exists(archive_path):
                os.remove(archive_path)
            
            # 返回远程项目目录路径
            return f"{remote_dir}/{project_root.name}"
            
        except Exception as e:
            # 清理本地压缩包
            if 'archive_path' in locals() and os.path.exists(archive_path):
                os.remove(archive_path)
            raise
    
    def test_connection(self) -> bool:
        """
        测试服务器连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.host, self.port, self.username, self.password, timeout=10)
            ssh.close()
            return True
        except Exception:
            return False
    
    def get_server_info(self) -> Dict[str, Any]:
        """
        获取服务器信息
        
        Returns:
            Dict[str, Any]: 服务器信息字典
        """
        return {
            'host': self.host,
            'username': self.username,
            'port': self.port,
            'connection_test': self.test_connection()
        }
