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

    def execute_remote_command(self, command: str, progress_callback: Optional[Callable[[str, int, int], None]] = None) -> tuple[int, str, str]:
        """
        在远程服务器执行命令

        Args:
            command (str): 要执行的命令
            progress_callback (Callable, optional): 进度回调函数

        Returns:
            tuple[int, str, str]: (退出状态, 标准输出, 错误输出)
        """
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.host, self.port, self.username, self.password, timeout=30)

        if progress_callback:
            progress_callback("执行远程命令", 0, 100)

        stdin, stdout, stderr = ssh.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode()
        error = stderr.read().decode()

        ssh.close()

        if progress_callback:
            progress_callback("执行远程命令", 100, 100)

        return exit_status, output, error

    def deploy_vue_project(self, project_root: str, remote_dir: Optional[str] = None,
                          progress_callback: Optional[Callable[[str, int, int], None]] = None) -> str:
        """
        部署Vue项目到远程服务器
        包括：上传项目、安装依赖、构建、配置Nginx

        Args:
            project_root (str): Vue项目根目录
            remote_dir (str, optional): 远程部署目录
            progress_callback (Callable, optional): 进度回调函数

        Returns:
            str: 部署完成后的项目路径
        """
        project_root = Path(project_root).resolve()

        if remote_dir is None:
            remote_dir = f"/home/{self.username}/vue-apps"

        try:
            # 1. 上传项目
            if progress_callback:
                progress_callback("上传Vue项目", 0, 100)

            remote_project_path = self.upload_and_extract(
                str(project_root),
                remote_dir,
                progress_callback=progress_callback
            )

            # 2. 安装Node.js依赖并构建
            if progress_callback:
                progress_callback("安装Node.js依赖", 0, 100)

            install_cmd = f"cd {remote_project_path} && npm install"
            exit_status, output, error = self.execute_remote_command(install_cmd)

            if exit_status != 0:
                raise Exception(f"安装依赖失败: {error}")

            if progress_callback:
                progress_callback("构建Vue项目", 0, 100)

            build_cmd = f"cd {remote_project_path} && npm run build"
            exit_status, output, error = self.execute_remote_command(build_cmd)

            if exit_status != 0:
                raise Exception(f"构建失败: {error}")

            # 3. 配置Nginx
            if progress_callback:
                progress_callback("配置Nginx", 0, 100)

            project_name = project_root.name
            nginx_config = f"""
server {{
    listen 80;
    server_name _;

    root {remote_project_path}/dist;
    index index.html;

    location / {{
        try_files $uri $uri/ /index.html;
    }}

    location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {{
        expires 1y;
        add_header Cache-Control "public, immutable";
    }}
}}
"""
            nginx_conf_path = f"/etc/nginx/sites-available/{project_name}"
            nginx_enabled_path = f"/etc/nginx/sites-enabled/{project_name}"

            # 写入Nginx配置
            write_config_cmd = f"echo '{nginx_config}' | sudo tee {nginx_conf_path}"
            self.execute_remote_command(write_config_cmd)

            # 启用站点
            enable_site_cmd = f"sudo ln -sf {nginx_conf_path} {nginx_enabled_path}"
            self.execute_remote_command(enable_site_cmd)

            # 测试Nginx配置
            test_nginx_cmd = "sudo nginx -t"
            exit_status, output, error = self.execute_remote_command(test_nginx_cmd)

            if exit_status != 0:
                raise Exception(f"Nginx配置测试失败: {error}")

            # 重启Nginx
            reload_nginx_cmd = "sudo systemctl reload nginx"
            self.execute_remote_command(reload_nginx_cmd)

            if progress_callback:
                progress_callback("配置Nginx", 100, 100)

            return remote_project_path

        except Exception as e:
            raise Exception(f"Vue项目部署失败: {str(e)}")

    def install_mysql(self, root_password: str = 'root',
                     progress_callback: Optional[Callable[[str, int, int], None]] = None) -> bool:
        """
        在Ubuntu服务器上安装MySQL

        Args:
            root_password (str): MySQL root密码
            progress_callback (Callable, optional): 进度回调函数

        Returns:
            bool: 安装是否成功
        """
        try:
            if progress_callback:
                progress_callback("更新软件包列表", 0, 100)

            # 更新软件包列表
            self.execute_remote_command("sudo apt update")

            if progress_callback:
                progress_callback("安装MySQL", 0, 100)

            # 设置MySQL root密码为环境变量，然后安装
            install_cmd = f"""echo "mysql-server mysql-server/root_password password {root_password}" | sudo debconf-set-selections && \
echo "mysql-server mysql-server/root_password_again password {root_password}" | sudo debconf-set-selections && \
sudo DEBIAN_FRONTEND=noninteractive apt install -y mysql-server"""

            exit_status, output, error = self.execute_remote_command(install_cmd)

            if exit_status != 0:
                raise Exception(f"MySQL安装失败: {error}")

            # 启动MySQL服务
            if progress_callback:
                progress_callback("启动MySQL服务", 0, 100)

            start_cmd = "sudo systemctl start mysql && sudo systemctl enable mysql"
            self.execute_remote_command(start_cmd)

            if progress_callback:
                progress_callback("安装MySQL", 100, 100)

            return True

        except Exception as e:
            raise Exception(f"MySQL安装失败: {str(e)}")

    def install_redis(self, progress_callback: Optional[Callable[[str, int, int], None]] = None) -> bool:
        """
        在Ubuntu服务器上安装Redis

        Args:
            progress_callback (Callable, optional): 进度回调函数

        Returns:
            bool: 安装是否成功
        """
        try:
            if progress_callback:
                progress_callback("更新软件包列表", 0, 100)

            # 更新软件包列表
            self.execute_remote_command("sudo apt update")

            if progress_callback:
                progress_callback("安装Redis", 0, 100)

            # 安装Redis
            install_cmd = "sudo DEBIAN_FRONTEND=noninteractive apt install -y redis-server"
            exit_status, output, error = self.execute_remote_command(install_cmd)

            if exit_status != 0:
                raise Exception(f"Redis安装失败: {error}")

            # 启动Redis服务
            if progress_callback:
                progress_callback("启动Redis服务", 0, 100)

            start_cmd = "sudo systemctl start redis && sudo systemctl enable redis"
            self.execute_remote_command(start_cmd)

            if progress_callback:
                progress_callback("安装Redis", 100, 100)

            return True

        except Exception as e:
            raise Exception(f"Redis安装失败: {str(e)}")

    def install_nginx(self, progress_callback: Optional[Callable[[str, int, int], None]] = None) -> bool:
        """
        在Ubuntu服务器上安装Nginx

        Args:
            progress_callback (Callable, optional): 进度回调函数

        Returns:
            bool: 安装是否成功
        """
        try:
            if progress_callback:
                progress_callback("更新软件包列表", 0, 100)

            # 更新软件包列表
            self.execute_remote_command("sudo apt update")

            if progress_callback:
                progress_callback("安装Nginx", 0, 100)

            # 安装Nginx
            install_cmd = "sudo DEBIAN_FRONTEND=noninteractive apt install -y nginx"
            exit_status, output, error = self.execute_remote_command(install_cmd)

            if exit_status != 0:
                raise Exception(f"Nginx安装失败: {error}")

            # 启动Nginx服务
            if progress_callback:
                progress_callback("启动Nginx服务", 0, 100)

            start_cmd = "sudo systemctl start nginx && sudo systemctl enable nginx"
            self.execute_remote_command(start_cmd)

            if progress_callback:
                progress_callback("安装Nginx", 100, 100)

            return True

        except Exception as e:
            raise Exception(f"Nginx安装失败: {str(e)}")

    def install_mongodb(self, progress_callback: Optional[Callable[[str, int, int], None]] = None) -> bool:
        """
        在Ubuntu服务器上安装MongoDB

        Args:
            progress_callback (Callable, optional): 进度回调函数

        Returns:
            bool: 安装是否成功
        """
        try:
            if progress_callback:
                progress_callback("更新软件包列表", 0, 100)

            # 更新软件包列表
            self.execute_remote_command("sudo apt update")

            if progress_callback:
                progress_callback("安装MongoDB", 0, 100)

            # 导入MongoDB公钥
            import_cmd = "wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -"
            self.execute_remote_command(import_cmd)

            # 添加MongoDB源
            source_cmd = "echo 'deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse' | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list"
            self.execute_remote_command(source_cmd)

            # 更新并安装
            self.execute_remote_command("sudo apt update")
            install_cmd = "sudo DEBIAN_FRONTEND=noninteractive apt install -y mongodb-org"
            exit_status, output, error = self.execute_remote_command(install_cmd)

            if exit_status != 0:
                raise Exception(f"MongoDB安装失败: {error}")

            # 启动MongoDB服务
            if progress_callback:
                progress_callback("启动MongoDB服务", 0, 100)

            start_cmd = "sudo systemctl start mongod && sudo systemctl enable mongod"
            self.execute_remote_command(start_cmd)

            if progress_callback:
                progress_callback("安装MongoDB", 100, 100)

            return True

        except Exception as e:
            raise Exception(f"MongoDB安装失败: {str(e)}")

    def install_postgresql(self, progress_callback: Optional[Callable[[str, int, int], None]] = None) -> bool:
        """
        在Ubuntu服务器上安装PostgreSQL

        Args:
            progress_callback (Callable, optional): 进度回调函数

        Returns:
            bool: 安装是否成功
        """
        try:
            if progress_callback:
                progress_callback("更新软件包列表", 0, 100)

            # 更新软件包列表
            self.execute_remote_command("sudo apt update")

            if progress_callback:
                progress_callback("安装PostgreSQL", 0, 100)

            # 安装PostgreSQL
            install_cmd = "sudo DEBIAN_FRONTEND=noninteractive apt install -y postgresql postgresql-contrib"
            exit_status, output, error = self.execute_remote_command(install_cmd)

            if exit_status != 0:
                raise Exception(f"PostgreSQL安装失败: {error}")

            # 启动PostgreSQL服务
            if progress_callback:
                progress_callback("启动PostgreSQL服务", 0, 100)

            start_cmd = "sudo systemctl start postgresql && sudo systemctl enable postgresql"
            self.execute_remote_command(start_cmd)

            if progress_callback:
                progress_callback("安装PostgreSQL", 100, 100)

            return True

        except Exception as e:
            raise Exception(f"PostgreSQL安装失败: {str(e)}")

    def install_jdk(self, progress_callback: Optional[Callable[[str, int, int], None]] = None) -> bool:
        """
        在Ubuntu服务器上安装JDK

        Args:
            progress_callback (Callable, optional): 进度回调函数

        Returns:
            bool: 安装是否成功
        """
        try:
            if progress_callback:
                progress_callback("更新软件包列表", 0, 100)

            # 更新软件包列表
            self.execute_remote_command("sudo apt update")

            if progress_callback:
                progress_callback("安装JDK 11", 0, 100)

            # 安装JDK
            install_cmd = "sudo DEBIAN_FRONTEND=noninteractive apt install -y openjdk-11-jdk"
            exit_status, output, error = self.execute_remote_command(install_cmd)

            if exit_status != 0:
                raise Exception(f"JDK安装失败: {error}")

            # 设置JAVA_HOME
            env_cmd = "echo 'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64' | sudo tee -a /etc/environment"
            self.execute_remote_command(env_cmd)

            if progress_callback:
                progress_callback("安装JDK", 100, 100)

            return True

        except Exception as e:
            raise Exception(f"JDK安装失败: {str(e)}")

    def install_python(self, progress_callback: Optional[Callable[[str, int, int], None]] = None) -> bool:
        """
        在Ubuntu服务器上安装Python

        Args:
            progress_callback (Callable, optional): 进度回调函数

        Returns:
            bool: 安装是否成功
        """
        try:
            if progress_callback:
                progress_callback("更新软件包列表", 0, 100)

            # 更新软件包列表
            self.execute_remote_command("sudo apt update")

            if progress_callback:
                progress_callback("安装Python 3及pip", 0, 100)

            # 安装Python和pip
            install_cmd = "sudo DEBIAN_FRONTEND=noninteractive apt install -y python3 python3-pip python3-venv"
            exit_status, output, error = self.execute_remote_command(install_cmd)

            if exit_status != 0:
                raise Exception(f"Python安装失败: {error}")

            if progress_callback:
                progress_callback("安装Python", 100, 100)

            return True

        except Exception as e:
            raise Exception(f"Python安装失败: {str(e)}")

    def install_nodejs(self, progress_callback: Optional[Callable[[str, int, int], None]] = None) -> bool:
        """
        在Ubuntu服务器上安装Node.js

        Args:
            progress_callback (Callable, optional): 进度回调函数

        Returns:
            bool: 安装是否成功
        """
        try:
            if progress_callback:
                progress_callback("准备安装Node.js", 0, 100)

            # 安装Node.js 18.x
            install_cmd = "curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - && sudo DEBIAN_FRONTEND=noninteractive apt install -y nodejs"
            exit_status, output, error = self.execute_remote_command(install_cmd)

            if exit_status != 0:
                raise Exception(f"Node.js安装失败: {error}")

            if progress_callback:
                progress_callback("安装Node.js", 100, 100)

            return True

        except Exception as e:
            raise Exception(f"Node.js安装失败: {str(e)}")

    def install_git(self, progress_callback: Optional[Callable[[str, int, int], None]] = None) -> bool:
        """
        在Ubuntu服务器上安装Git

        Args:
            progress_callback (Callable, optional): 进度回调函数

        Returns:
            bool: 安装是否成功
        """
        try:
            if progress_callback:
                progress_callback("更新软件包列表", 0, 100)

            # 更新软件包列表
            self.execute_remote_command("sudo apt update")

            if progress_callback:
                progress_callback("安装Git", 0, 100)

            # 安装Git
            install_cmd = "sudo DEBIAN_FRONTEND=noninteractive apt install -y git"
            exit_status, output, error = self.execute_remote_command(install_cmd)

            if exit_status != 0:
                raise Exception(f"Git安装失败: {error}")

            if progress_callback:
                progress_callback("安装Git", 100, 100)

            return True

        except Exception as e:
            raise Exception(f"Git安装失败: {str(e)}")

    def install_docker(self, progress_callback: Optional[Callable[[str, int, int], None]] = None) -> bool:
        """
        在Ubuntu服务器上安装Docker

        Args:
            progress_callback (Callable, optional): 进度回调函数

        Returns:
            bool: 安装是否成功
        """
        try:
            if progress_callback:
                progress_callback("更新软件包列表", 0, 100)

            # 更新软件包列表
            self.execute_remote_command("sudo apt update")

            if progress_callback:
                progress_callback("安装Docker依赖", 0, 100)

            # 安装依赖
            deps_cmd = "sudo DEBIAN_FRONTEND=noninteractive apt install -y ca-certificates curl gnupg lsb-release"
            self.execute_remote_command(deps_cmd)

            # 添加Docker官方GPG密钥
            if progress_callback:
                progress_callback("添加Docker GPG密钥", 0, 100)

            key_cmd = "sudo mkdir -p /etc/apt/keyrings && curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg"
            self.execute_remote_command(key_cmd)

            # 设置Docker仓库
            if progress_callback:
                progress_callback("设置Docker仓库", 0, 100)

            repo_cmd = "echo 'deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable' | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null"
            self.execute_remote_command(repo_cmd)

            # 更新并安装Docker
            if progress_callback:
                progress_callback("安装Docker", 0, 100)

            self.execute_remote_command("sudo apt update")
            install_cmd = "sudo DEBIAN_FRONTEND=noninteractive apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin"
            exit_status, output, error = self.execute_remote_command(install_cmd)

            if exit_status != 0:
                raise Exception(f"Docker安装失败: {error}")

            # 启动Docker服务
            if progress_callback:
                progress_callback("启动Docker服务", 0, 100)

            start_cmd = "sudo systemctl start docker && sudo systemctl enable docker"
            self.execute_remote_command(start_cmd)

            # 添加当前用户到docker组
            user_cmd = f"sudo usermod -aG docker {self.username}"
            self.execute_remote_command(user_cmd)

            if progress_callback:
                progress_callback("安装Docker", 100, 100)

            return True

        except Exception as e:
            raise Exception(f"Docker安装失败: {str(e)}")

    def install_rabbitmq(self, progress_callback: Optional[Callable[[str, int, int], None]] = None) -> bool:
        """
        在Ubuntu服务器上安装RabbitMQ

        Args:
            progress_callback (Callable, optional): 进度回调函数

        Returns:
            bool: 安装是否成功
        """
        try:
            if progress_callback:
                progress_callback("更新软件包列表", 0, 100)

            # 更新软件包列表
            self.execute_remote_command("sudo apt update")

            if progress_callback:
                progress_callback("安装Erlang", 0, 100)

            # 安装Erlang（RabbitMQ依赖）
            erlang_cmd = "sudo DEBIAN_FRONTEND=noninteractive apt install -y erlang-nox"
            self.execute_remote_command(erlang_cmd)

            if progress_callback:
                progress_callback("安装RabbitMQ", 0, 100)

            # 添加RabbitMQ源
            source_cmd = "sudo apt-get install -y erlang && echo 'deb https://dl.bintray.com/rabbitmq/debian ubuntu main' | sudo tee /etc/apt/sources.list.d/bintray.rabbitmq.list"
            self.execute_remote_command(source_cmd)

            # 安装RabbitMQ
            install_cmd = "sudo DEBIAN_FRONTEND=noninteractive apt install -y rabbitmq-server"
            exit_status, output, error = self.execute_remote_command(install_cmd)

            if exit_status != 0:
                raise Exception(f"RabbitMQ安装失败: {error}")

            # 启动RabbitMQ服务
            if progress_callback:
                progress_callback("启动RabbitMQ服务", 0, 100)

            start_cmd = "sudo systemctl start rabbitmq-server && sudo systemctl enable rabbitmq-server"
            self.execute_remote_command(start_cmd)

            if progress_callback:
                progress_callback("安装RabbitMQ", 100, 100)

            return True

        except Exception as e:
            raise Exception(f"RabbitMQ安装失败: {str(e)}")

    def install_php(self, progress_callback: Optional[Callable[[str, int, int], None]] = None) -> bool:
        """
        在Ubuntu服务器上安装PHP

        Args:
            progress_callback (Callable, optional): 进度回调函数

        Returns:
            bool: 安装是否成功
        """
        try:
            if progress_callback:
                progress_callback("更新软件包列表", 0, 100)

            # 更新软件包列表
            self.execute_remote_command("sudo apt update")

            if progress_callback:
                progress_callback("安装PHP 8及常用扩展", 0, 100)

            # 安装PHP和常用扩展
            install_cmd = "sudo DEBIAN_FRONTEND=noninteractive apt install -y php php-fpm php-mysql php-redis php-mongodb php-pgsql php-curl php-gd php-mbstring php-xml php-zip"
            exit_status, output, error = self.execute_remote_command(install_cmd)

            if exit_status != 0:
                raise Exception(f"PHP安装失败: {error}")

            # 启动PHP-FPM服务
            if progress_callback:
                progress_callback("启动PHP-FPM服务", 0, 100)

            start_cmd = "sudo systemctl start php8.1-fpm && sudo systemctl enable php8.1-fpm"
            self.execute_remote_command(start_cmd)

            if progress_callback:
                progress_callback("安装PHP", 100, 100)

            return True

        except Exception as e:
            raise Exception(f"PHP安装失败: {str(e)}")

    def deploy_springboot_project(self, project_root: str, remote_dir: Optional[str] = None,
                                  progress_callback: Optional[Callable[[str, int, int], None]] = None) -> str:
        """
        部署SpringBoot项目到远程服务器
        包括：打包项目、上传jar文件、创建systemd服务、启动应用

        Args:
            project_root (str): SpringBoot项目根目录
            remote_dir (str, optional): 远程部署目录
            progress_callback (Callable, optional): 进度回调函数

        Returns:
            str: 部署完成后的jar文件路径
        """
        project_root = Path(project_root).resolve()

        if remote_dir is None:
            remote_dir = f"/home/{self.username}/springboot-apps"

        try:
            # 1. 检查是否为Maven项目
            pom_xml = project_root / "pom.xml"
            if not pom_xml.exists():
                raise Exception("不是有效的Maven项目，未找到pom.xml文件")

            if progress_callback:
                progress_callback("上传SpringBoot项目", 0, 100)

            # 2. 上传项目文件
            remote_project_path = self.upload_and_extract(
                str(project_root),
                remote_dir,
                progress_callback=progress_callback
            )

            project_name = project_root.name

            # 3. 安装Maven（如果未安装）
            if progress_callback:
                progress_callback("检查Maven环境", 0, 100)

            check_maven_cmd = "command -v mvn"
            exit_status, output, error = self.execute_remote_command(check_maven_cmd)

            if exit_status != 0:
                if progress_callback:
                    progress_callback("安装Maven", 0, 100)

                # 安装Maven
                install_maven_cmd = "sudo DEBIAN_FRONTEND=noninteractive apt install -y maven"
                exit_status, output, error = self.execute_remote_command(install_maven_cmd)

                if exit_status != 0:
                    raise Exception(f"Maven安装失败: {error}")

            # 4. 打包项目
            if progress_callback:
                progress_callback("打包SpringBoot项目", 0, 100)

            package_cmd = f"cd {remote_project_path} && mvn clean package -DskipTests"
            exit_status, output, error = self.execute_remote_command(package_cmd)

            if exit_status != 0:
                # 尝试使用Gradle
                build_gradle = project_root / "build.gradle"
                if build_gradle.exists():
                    if progress_callback:
                        progress_callback("使用Gradle打包", 0, 100)

                    # 检查Gradle
                    check_gradle_cmd = "command -v gradle"
                    exit_status, output, error = self.execute_remote_command(check_gradle_cmd)

                    if exit_status != 0:
                        # 安装Gradle
                        install_gradle_cmd = "sudo DEBIAN_FRONTEND=noninteractive apt install -y gradle"
                        exit_status, output, error = self.execute_remote_command(install_gradle_cmd)

                    # 使用Gradle打包
                    package_cmd = f"cd {remote_project_path} && gradle clean build -x test"
                    exit_status, output, error = self.execute_remote_command(package_cmd)

                    if exit_status != 0:
                        raise Exception(f"Gradle打包失败: {error}")

                    # Gradle构建的jar位置
                    jar_file = f"{remote_project_path}/build/libs/*.jar"
                else:
                    raise Exception(f"Maven打包失败: {error}")
            else:
                # Maven构建的jar位置
                jar_file = f"{remote_project_path}/target/*.jar"

            if progress_callback:
                progress_callback("打包SpringBoot项目", 100, 100)

            # 5. 创建部署目录
            if progress_callback:
                progress_callback("创建部署目录", 0, 100)

            deploy_dir = f"/opt/{project_name}"
            mkdir_cmd = f"sudo mkdir -p {deploy_dir}"
            self.execute_remote_command(mkdir_cmd)

            # 6. 移动jar文件到部署目录
            if progress_callback:
                progress_callback("部署jar文件", 0, 100)

            move_cmd = f"sudo mv {jar_file} {deploy_dir}/{project_name}.jar"
            exit_status, output, error = self.execute_remote_command(move_cmd)

            if exit_status != 0:
                raise Exception(f"移动jar文件失败: {error}")

            # 7. 创建systemd服务文件
            if progress_callback:
                progress_callback("创建systemd服务", 0, 100)

            service_content = f"""[Unit]
Description=Spring Boot Application - {project_name}
After=syslog.target network.target

[Service]
User={self.username}
ExecStart=/usr/bin/java -jar {deploy_dir}/{project_name}.jar
SuccessExitStatus=143
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

            service_file = f"/etc/systemd/system/{project_name}.service"
            write_service_cmd = f"echo '{service_content}' | sudo tee {service_file}"
            self.execute_remote_command(write_service_cmd)

            # 8. 重载systemd并启动服务
            if progress_callback:
                progress_callback("启动应用服务", 0, 100)

            reload_cmd = "sudo systemctl daemon-reload"
            self.execute_remote_command(reload_cmd)

            start_cmd = f"sudo systemctl start {project_name}"
            exit_status, output, error = self.execute_remote_command(start_cmd)

            if exit_status != 0:
                raise Exception(f"启动服务失败: {error}")

            enable_cmd = f"sudo systemctl enable {project_name}"
            self.execute_remote_command(enable_cmd)

            # 9. 检查服务状态
            status_cmd = f"sudo systemctl is-active {project_name}"
            exit_status, output, error = self.execute_remote_command(status_cmd)

            if progress_callback:
                progress_callback("启动应用服务", 100, 100)

            # 返回部署信息
            return f"{deploy_dir}/{project_name}.jar"

        except Exception as e:
            raise Exception(f"SpringBoot项目部署失败: {str(e)}")

