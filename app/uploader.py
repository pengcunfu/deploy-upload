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

    def deploy_vue_project(
        self,
        project_root: str,
        remote_dir: Optional[str] = None,
        build_command: str = "npm run build",
        nginx_port: int = 80,
        server_name: str = "_",
        enable_ssl: bool = False,
        proxy_configs: Optional[List[dict]] = None,
        auto_install: bool = True,
        clean_build: bool = False,
        build_mode: str = "remote",
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> str:
        """
        部署Vue项目到远程服务器
        包括：上传项目、安装依赖、构建、配置Nginx

        Args:
            project_root (str): Vue项目根目录
            remote_dir (str, optional): 远程部署目录
            build_command (str): 构建命令，默认为 "npm run build"
            nginx_port (int): Nginx监听端口，默认为 80
            server_name (str): 服务器名称，默认为 "_"
            enable_ssl (bool): 是否启用SSL，默认为 False
            proxy_configs (list, optional): API代理配置列表
            auto_install (bool): 自动安装Node.js，默认为 True
            clean_build (bool): 清理并重新构建，默认为 False
            build_mode (str): 构建模式，"local" 或 "remote"，默认为 "remote"
            progress_callback (Callable, optional): 进度回调函数

        Returns:
            str: 部署完成后的项目路径
        """
        project_root = Path(project_root).resolve()
        proxy_configs = proxy_configs or []

        if remote_dir is None:
            remote_dir = f"/home/{self.username}/vue-apps"

        try:
            project_name = project_root.name

            # 本地构建模式
            if build_mode == "local":
                if progress_callback:
                    progress_callback("本地构建模式", 0, 100)

                # 1. 在本地构建项目
                if progress_callback:
                    progress_callback("本地构建Vue项目", 0, 100)

                import subprocess
                import shutil

                # 检查本地是否有Node.js
                if not shutil.which("node"):
                    raise Exception("本地未安装Node.js，请先安装Node.js或使用远程构建模式")

                # 清理旧的构建（如果需要）
                dist_dir = project_root / "dist"
                if clean_build and dist_dir.exists():
                    if progress_callback:
                        progress_callback("清理旧构建", 0, 100)
                    shutil.rmtree(dist_dir)

                # 执行本地构建
                build_process = subprocess.Popen(
                    build_command,
                    shell=True,
                    cwd=str(project_root),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

                _, stderr = build_process.communicate()

                if build_process.returncode != 0:
                    error_msg = stderr.decode('utf-8', errors='ignore')
                    raise Exception(f"本地构建失败: {error_msg}")

                if progress_callback:
                    progress_callback("本地构建完成", 100, 100)

                # 2. 上传dist目录
                if progress_callback:
                    progress_callback("上传构建文件", 0, 100)

                # 创建临时目录用于打包
                import tempfile
                temp_dir = tempfile.mkdtemp()
                temp_dist = Path(temp_dir) / "dist"
                shutil.copytree(dist_dir, temp_dist)

                # 打包并上传
                remote_project_path = self._upload_and_extract_dist(
                    str(temp_dir),
                    remote_dir,
                    progress_callback=progress_callback
                )

                # 清理临时目录
                shutil.rmtree(temp_dir)

            else:
                # 远程构建模式（原有逻辑）
                # 1. 上传项目
                if progress_callback:
                    progress_callback("上传Vue项目", 0, 100)

                remote_project_path = self.upload_and_extract(
                    str(project_root),
                    remote_dir,
                    progress_callback=progress_callback
                )

                # 2. 检查并安装Node.js（如果需要）
                if auto_install:
                    if progress_callback:
                        progress_callback("检查Node.js环境", 0, 100)

                    check_node_cmd = "command -v node"
                    exit_status, output, error = self.execute_remote_command(check_node_cmd)

                    if exit_status != 0:
                        if progress_callback:
                            progress_callback("安装Node.js", 0, 100)

                        # 安装Node.js
                        install_node_cmd = "curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - && sudo DEBIAN_FRONTEND=noninteractive apt install -y nodejs"
                        exit_status, output, error = self.execute_remote_command(install_node_cmd)

                        if exit_status != 0:
                            raise Exception(f"Node.js安装失败: {error}")

                # 3. 安装依赖并构建
                if progress_callback:
                    progress_callback("安装Node.js依赖", 0, 100)

                if clean_build:
                    # 清理node_modules并重新安装
                    install_cmd = f"cd {remote_project_path} && rm -rf node_modules package-lock.json && npm install"
                else:
                    install_cmd = f"cd {remote_project_path} && npm install"

                exit_status, output, error = self.execute_remote_command(install_cmd)

                if exit_status != 0:
                    raise Exception(f"安装依赖失败: {error}")

                if progress_callback:
                    progress_callback("构建Vue项目", 0, 100)

                build_cmd = f"cd {remote_project_path} && {build_command}"
                exit_status, output, error = self.execute_remote_command(build_cmd)

                if exit_status != 0:
                    raise Exception(f"构建失败: {error}")

            # 4. 配置Nginx（两种构建模式都需要）
            if progress_callback:
                progress_callback("配置Nginx", 0, 100)

            # 生成Nginx配置
            listen_directive = f"listen {nginx_port} ssl;" if enable_ssl else f"listen {nginx_port};"

            # 基础Nginx配置
            nginx_config = f"""server {{
    {listen_directive}
    server_name {server_name};

    root {remote_project_path}/dist;
    index index.html;

    # 静态资源缓存
    location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {{
        expires 1y;
        add_header Cache-Control "public, immutable";
    }}

    # Vue Router history模式支持
    location / {{
        try_files $uri $uri/ /index.html;
    }}
"""

            # 添加代理配置
            if proxy_configs:
                nginx_config += "\n    # API代理配置\n"
                for proxy in proxy_configs:
                    path = proxy.get("path", "/api")
                    target = proxy.get("target", "http://127.0.0.1:8080")

                    nginx_config += f"""
    location {path} {{
        proxy_pass {target};
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }}
"""

            nginx_config += "}\n"

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

    def _upload_and_extract_dist(
        self,
        local_dir: str,
        remote_dir: str,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> str:
        """
        上传并解压本地构建的dist目录

        Args:
            local_dir (str): 本地目录（包含dist文件夹）
            remote_dir (str): 远程目录
            progress_callback (Callable, optional): 进度回调函数

        Returns:
            str: 远程项目路径
        """
        local_dir = Path(local_dir).resolve()
        project_name = local_dir.parent.name

        try:
            # 1. 创建临时tar文件
            temp_tar = tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False)

            if progress_callback:
                progress_callback("打包构建文件", 0, 100)

            with tarfile.open(temp_tar.name, "w:gz") as tar:
                for item in local_dir.iterdir():
                    tar.add(item, arcname=item.name)

            if progress_callback:
                progress_callback("打包构建文件", 50, 100)

            # 2. 连接SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=10
            )

            sftp = ssh.open_sftp()

            # 3. 创建远程目录
            remote_project_path = f"{remote_dir}/{project_name}"
            self._create_remote_dirs(sftp, remote_project_path)

            if progress_callback:
                progress_callback("上传构建文件", 50, 100)

            # 4. 上传tar文件
            remote_tar_path = f"/tmp/{project_name}_dist.tar.gz"
            sftp.put(temp_tar.name, remote_tar_path)

            sftp.close()
            ssh.close()

            # 5. 解压文件
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=10
            )

            extract_cmd = f"tar -xzf {remote_tar_path} -C {remote_project_path} && rm {remote_tar_path}"
            ssh.exec_command(extract_cmd)

            ssh.close()

            if progress_callback:
                progress_callback("上传构建文件", 100, 100)

            # 删除临时文件
            Path(temp_tar.name).unlink()

            return remote_project_path

        except Exception as e:
            raise Exception(f"上传dist文件失败: {str(e)}")

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

    def deploy_springboot_project(
        self,
        project_root: str,
        remote_dir: Optional[str] = None,
        build_tool: str = "auto",
        jvm_options: str = "",
        service_port: int = 8080,
        active_profile: str = "",
        build_mode: str = "remote",
        skip_tests: bool = True,
        auto_install: bool = True,
        clean_build: bool = True,
        enable_service: bool = True,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> str:
        """
        部署SpringBoot项目到远程服务器
        包括：打包项目、上传jar文件、创建systemd服务、启动应用

        Args:
            project_root (str): SpringBoot项目根目录
            remote_dir (str, optional): 远程部署目录
            build_tool (str): 构建工具，"auto"/"maven"/"gradle"
            jvm_options (str): JVM参数，如 "-Xms512m -Xmx1024m"
            service_port (int): 服务端口
            active_profile (str): 激活的配置文件
            build_mode (str): 构建模式，"local" 或 "remote"
            skip_tests (bool): 跳过测试
            auto_install (bool): 自动安装构建工具
            clean_build (bool): 清理并重新构建
            enable_service (bool): 启用开机自启
            progress_callback (Callable, optional): 进度回调函数

        Returns:
            str: 部署完成后的jar文件路径
        """
        project_root = Path(project_root).resolve()

        if remote_dir is None:
            remote_dir = f"/home/{self.username}/springboot-apps"

        try:
            project_name = project_root.name

            # 检测构建工具
            pom_xml = project_root / "pom.xml"
            build_gradle = project_root / "build.gradle"
            build_gradle_kts = project_root / "build.gradle.kts"

            if build_tool == "auto":
                if pom_xml.exists():
                    build_tool = "maven"
                elif build_gradle.exists() or build_gradle_kts.exists():
                    build_tool = "gradle"
                else:
                    raise Exception("未找到构建配置文件（pom.xml或build.gradle）")

            # 本地构建模式
            if build_mode == "local":
                if progress_callback:
                    progress_callback("本地构建模式", 0, 100)

                # 检查本地构建工具
                import subprocess
                import shutil

                if build_tool == "maven":
                    if not shutil.which("mvn"):
                        raise Exception("本地未安装Maven，请先安装或使用远程构建模式")
                    build_cmd = "mvn"
                    if clean_build:
                        build_cmd += " clean"
                    build_cmd += " package"
                    if skip_tests:
                        build_cmd += " -DskipTests"
                else:  # gradle
                    if not shutil.which("gradle"):
                        raise Exception("本地未安装Gradle，请先安装或使用远程构建模式")
                    build_cmd = "gradle"
                    if clean_build:
                        build_cmd += " clean"
                    build_cmd += " build"
                    if skip_tests:
                        build_cmd += " -x test"

                # 执行本地构建
                if progress_callback:
                    progress_callback("本地构建SpringBoot项目", 0, 100)

                build_process = subprocess.Popen(
                    build_cmd,
                    shell=True,
                    cwd=str(project_root),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

                _, stderr = build_process.communicate()

                if build_process.returncode != 0:
                    error_msg = stderr.decode('utf-8', errors='ignore')
                    raise Exception(f"本地构建失败: {error_msg}")

                # 查找生成的jar文件
                if build_tool == "maven":
                    local_jar = project_root / "target" / f"{project_name}.jar"
                    if not local_jar.exists():
                        # 尝试查找任何jar文件
                        jar_files = list((project_root / "target").glob("*.jar"))
                        if jar_files:
                            local_jar = jar_files[0]
                        else:
                            raise Exception("未找到构建生成的jar文件")
                else:  # gradle
                    local_jar = project_root / "build" / "libs" / f"{project_name}.jar"
                    if not local_jar.exists():
                        jar_files = list((project_root / "build" / "libs").glob("*.jar"))
                        if jar_files:
                            local_jar = jar_files[0]
                        else:
                            raise Exception("未找到构建生成的jar文件")

                # 上传jar文件
                if progress_callback:
                    progress_callback("上传jar文件", 0, 100)

                deploy_dir = f"/opt/{project_name}"
                mkdir_cmd = f"sudo mkdir -p {deploy_dir}"
                self.execute_remote_command(mkdir_cmd)

                # 使用SFTP上传jar文件
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    timeout=10
                )

                sftp = ssh.open_sftp()
                remote_jar_path = f"{deploy_dir}/{project_name}.jar"
                sftp.put(str(local_jar), remote_jar_path)
                sftp.close()
                ssh.close()

                remote_jar_file = remote_jar_path

            else:
                # 远程构建模式
                # 1. 上传项目文件
                if progress_callback:
                    progress_callback("上传SpringBoot项目", 0, 100)

                remote_project_path = self.upload_and_extract(
                    str(project_root),
                    remote_dir,
                    progress_callback=progress_callback
                )

                # 2. 安装构建工具（如果需要）
                if auto_install:
                    if build_tool == "maven":
                        if progress_callback:
                            progress_callback("检查Maven环境", 0, 100)

                        check_maven_cmd = "command -v mvn"
                        exit_status, output, error = self.execute_remote_command(check_maven_cmd)

                        if exit_status != 0:
                            if progress_callback:
                                progress_callback("安装Maven", 0, 100)

                            install_maven_cmd = "sudo DEBIAN_FRONTEND=noninteractive apt install -y maven"
                            exit_status, output, error = self.execute_remote_command(install_maven_cmd)

                            if exit_status != 0:
                                raise Exception(f"Maven安装失败: {error}")

                    elif build_tool == "gradle":
                        if progress_callback:
                            progress_callback("检查Gradle环境", 0, 100)

                        check_gradle_cmd = "command -v gradle"
                        exit_status, output, error = self.execute_remote_command(check_gradle_cmd)

                        if exit_status != 0:
                            if progress_callback:
                                progress_callback("安装Gradle", 0, 100)

                            install_gradle_cmd = "sudo DEBIAN_FRONTEND=noninteractive apt install -y gradle"
                            exit_status, output, error = self.execute_remote_command(install_gradle_cmd)

                            if exit_status != 0:
                                raise Exception(f"Gradle安装失败: {error}")

                # 3. 打包项目
                if progress_callback:
                    progress_callback("打包SpringBoot项目", 0, 100)

                if build_tool == "maven":
                    package_cmd = "cd {remote_project_path} && "
                    if clean_build:
                        package_cmd += "mvn clean "
                    else:
                        package_cmd += "mvn "
                    package_cmd += "package"
                    if skip_tests:
                        package_cmd += " -DskipTests"

                    exit_status, output, error = self.execute_remote_command(package_cmd)

                    if exit_status != 0:
                        raise Exception(f"Maven打包失败: {error}")

                    jar_file = f"{remote_project_path}/target/*.jar"

                else:  # gradle
                    package_cmd = "cd {remote_project_path} && "
                    if clean_build:
                        package_cmd += "gradle clean "
                    else:
                        package_cmd += "gradle "
                    package_cmd += "build"
                    if skip_tests:
                        package_cmd += " -x test"

                    exit_status, output, error = self.execute_remote_command(package_cmd)

                    if exit_status != 0:
                        raise Exception(f"Gradle打包失败: {error}")

                    jar_file = f"{remote_project_path}/build/libs/*.jar"

                if progress_callback:
                    progress_callback("打包SpringBoot项目", 100, 100)

                # 4. 创建部署目录
                if progress_callback:
                    progress_callback("创建部署目录", 0, 100)

                deploy_dir = f"/opt/{project_name}"
                mkdir_cmd = f"sudo mkdir -p {deploy_dir}"
                self.execute_remote_command(mkdir_cmd)

                # 5. 移动jar文件到部署目录
                if progress_callback:
                    progress_callback("部署jar文件", 0, 100)

                move_cmd = f"sudo mv {jar_file} {deploy_dir}/{project_name}.jar"
                exit_status, output, error = self.execute_remote_command(move_cmd)

                if exit_status != 0:
                    raise Exception(f"移动jar文件失败: {error}")

                remote_jar_file = f"{deploy_dir}/{project_name}.jar"

            # 6. 创建systemd服务文件（两种构建模式都需要）
            if progress_callback:
                progress_callback("创建systemd服务", 0, 100)

            # 构建启动命令
            start_cmd = "/usr/bin/java"
            if jvm_options:
                start_cmd += f" {jvm_options}"
            start_cmd += f" -jar {remote_jar_file}"

            # 添加配置文件参数
            if active_profile:
                start_cmd += f" --spring.profiles.active={active_profile}"

            # 添加端口参数（如果配置了）
            if service_port and service_port != 8080:
                start_cmd += f" --server.port={service_port}"

            service_content = f"""[Unit]
Description=Spring Boot Application - {project_name}
After=syslog.target network.target

[Service]
User={self.username}
ExecStart={start_cmd}
SuccessExitStatus=143
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

            service_file = f"/etc/systemd/system/{project_name}.service"
            write_service_cmd = f"echo '{service_content}' | sudo tee {service_file}"
            self.execute_remote_command(write_service_cmd)

            # 7. 重载systemd并启动服务
            if progress_callback:
                progress_callback("启动应用服务", 0, 100)

            reload_cmd = "sudo systemctl daemon-reload"
            self.execute_remote_command(reload_cmd)

            start_cmd = f"sudo systemctl start {project_name}"
            exit_status, output, error = self.execute_remote_command(start_cmd)

            if exit_status != 0:
                raise Exception(f"启动服务失败: {error}")

            if enable_service:
                enable_cmd = f"sudo systemctl enable {project_name}"
                self.execute_remote_command(enable_cmd)

            # 8. 检查服务状态
            status_cmd = f"sudo systemctl is-active {project_name}"
            exit_status, output, error = self.execute_remote_command(status_cmd)

            if progress_callback:
                progress_callback("启动应用服务", 100, 100)

            # 返回部署信息
            return remote_jar_file

        except Exception as e:
            raise Exception(f"SpringBoot项目部署失败: {str(e)}")

    def deploy_flask_project(self, project_root: str, remote_dir: Optional[str] = None,
                            progress_callback: Optional[Callable[[str, int, int], None]] = None) -> str:
        """
        部署Flask项目到远程服务器
        包括：上传项目、创建虚拟环境、安装依赖、配置Gunicorn、配置Nginx、启动服务

        Args:
            project_root (str): Flask项目根目录
            remote_dir (str, optional): 远程部署目录
            progress_callback (Callable, optional): 进度回调函数

        Returns:
            str: 部署完成后的项目路径
        """
        project_root = Path(project_root).resolve()

        if remote_dir is None:
            remote_dir = f"/home/{self.username}/flask-apps"

        try:
            # 1. 检查是否为Flask项目
            requirements_txt = project_root / "requirements.txt"
            app_py = project_root / "app.py"

            if not app_py.exists():
                # 检查其他常见的Flask入口文件
                common_entries = ["main.py", "run.py", "wsgi.py", "application.py"]
                has_entry = any((project_root / entry).exists() for entry in common_entries)
                if not has_entry:
                    raise Exception("不是有效的Flask项目，未找到app.py或其他入口文件")

            if progress_callback:
                progress_callback("上传Flask项目", 0, 100)

            # 2. 上传项目文件
            remote_project_path = self.upload_and_extract(
                str(project_root),
                remote_dir,
                progress_callback=progress_callback
            )

            project_name = project_root.name

            # 3. 创建Python虚拟环境
            if progress_callback:
                progress_callback("创建Python虚拟环境", 0, 100)

            venv_cmd = f"cd {remote_project_path} && python3 -m venv venv"
            exit_status, output, error = self.execute_remote_command(venv_cmd)

            if exit_status != 0:
                raise Exception(f"创建虚拟环境失败: {error}")

            # 4. 安装Python依赖
            if progress_callback:
                progress_callback("安装Python依赖", 0, 100)

            if requirements_txt.exists():
                pip_cmd = f"cd {remote_project_path} && ./venv/bin/pip install -r requirements.txt"
            else:
                # 安装基础依赖
                pip_cmd = f"cd {remote_project_path} && ./venv/bin/pip install flask gunicorn"

            exit_status, output, error = self.execute_remote_command(pip_cmd)

            if exit_status != 0:
                raise Exception(f"安装依赖失败: {error}")

            # 5. 创建Gunicorn配置
            if progress_callback:
                progress_callback("配置Gunicorn", 0, 100)

            # 查找Flask入口文件
            entry_file = "app.py"
            for file in ["app.py", "main.py", "run.py", "wsgi.py", "application.py"]:
                if (project_root / file).exists():
                    entry_file = file
                    break

            gunicorn_service_content = f"""[Unit]
Description=Gunicorn instance to serve {project_name}
After=network.target

[Service]
User={self.username}
Group=www-data
WorkingDirectory={remote_project_path}
Environment="PATH={remote_project_path}/venv/bin"
ExecStart={remote_project_path}/venv/bin/gunicorn --workers 3 --bind unix:{project_name}.sock -m 007 {entry_file.replace('.py', ':app')}

[Install]
WantedBy=multi-user.target
"""

            service_file = f"/etc/systemd/system/{project_name}.service"
            write_service_cmd = f"echo '{gunicorn_service_content}' | sudo tee {service_file}"
            self.execute_remote_command(write_service_cmd)

            # 6. 启动Gunicorn服务
            if progress_callback:
                progress_callback("启动Gunicorn服务", 0, 100)

            reload_cmd = "sudo systemctl daemon-reload"
            self.execute_remote_command(reload_cmd)

            start_cmd = f"sudo systemctl start {project_name}"
            exit_status, output, error = self.execute_remote_command(start_cmd)

            if exit_status != 0:
                raise Exception(f"启动Gunicorn服务失败: {error}")

            enable_cmd = f"sudo systemctl enable {project_name}"
            self.execute_remote_command(enable_cmd)

            # 7. 配置Nginx
            if progress_callback:
                progress_callback("配置Nginx", 0, 100)

            nginx_config = f"""
server {{
    listen 80;
    server_name _;

    location / {{
        include proxy_params;
        proxy_pass http://unix:{remote_project_path}/{project_name}.sock;
    }}
}}
"""

            nginx_conf_path = f"/etc/nginx/sites-available/{project_name}"
            nginx_enabled_path = f"/etc/nginx/sites-enabled/{project_name}"

            write_config_cmd = f"echo '{nginx_config}' | sudo tee {nginx_conf_path}"
            self.execute_remote_command(write_config_cmd)

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
            raise Exception(f"Flask项目部署失败: {str(e)}")

    def deploy_django_project(self, project_root: str, remote_dir: Optional[str] = None,
                             progress_callback: Optional[Callable[[str, int, int], None]] = None) -> str:
        """
        部署Django项目到远程服务器
        包括：上传项目、创建虚拟环境、安装依赖、迁移数据库、配置Gunicorn、配置Nginx、启动服务

        Args:
            project_root (str): Django项目根目录
            remote_dir (str, optional): 远程部署目录
            progress_callback (Callable, optional): 进度回调函数

        Returns:
            str: 部署完成后的项目路径
        """
        project_root = Path(project_root).resolve()

        if remote_dir is None:
            remote_dir = f"/home/{self.username}/django-apps"

        try:
            # 1. 检查是否为Django项目
            manage_py = project_root / "manage.py"

            if not manage_py.exists():
                raise Exception("不是有效的Django项目，未找到manage.py文件")

            if progress_callback:
                progress_callback("上传Django项目", 0, 100)

            # 2. 上传项目文件
            remote_project_path = self.upload_and_extract(
                str(project_root),
                remote_dir,
                progress_callback=progress_callback
            )

            project_name = project_root.name

            # 3. 创建Python虚拟环境
            if progress_callback:
                progress_callback("创建Python虚拟环境", 0, 100)

            venv_cmd = f"cd {remote_project_path} && python3 -m venv venv"
            exit_status, output, error = self.execute_remote_command(venv_cmd)

            if exit_status != 0:
                raise Exception(f"创建虚拟环境失败: {error}")

            # 4. 安装Python依赖
            if progress_callback:
                progress_callback("安装Python依赖", 0, 100)

            requirements_txt = project_root / "requirements.txt"
            if requirements_txt.exists():
                pip_cmd = f"cd {remote_project_path} && ./venv/bin/pip install -r requirements.txt"
            else:
                # 安装基础依赖
                pip_cmd = f"cd {remote_project_path} && ./venv/bin/pip install django gunicorn psycopg2-binary"

            exit_status, output, error = self.execute_remote_command(pip_cmd)

            if exit_status != 0:
                raise Exception(f"安装依赖失败: {error}")

            # 5. 迁移数据库
            if progress_callback:
                progress_callback("迁移数据库", 0, 100)

            migrate_cmd = f"cd {remote_project_path} && ./venv/bin/python manage.py migrate"
            exit_status, output, error = self.execute_remote_command(migrate_cmd)

            if exit_status != 0:
                # 迁移失败可能不是致命错误，记录警告
                if progress_callback:
                    progress_callback("警告: 数据库迁移失败，请检查配置", 0, 100)

            # 6. 收集静态文件
            if progress_callback:
                progress_callback("收集静态文件", 0, 100)

            # 创建settings文件中的DEBUG=False设置
            static_cmd = f"cd {remote_project_path} && ./venv/bin/python manage.py collectstatic --noinput"
            exit_status, output, error = self.execute_remote_command(static_cmd)

            # 7. 创建Gunicorn配置
            if progress_callback:
                progress_callback("配置Gunicorn", 0, 100)

            # 查找Django项目的wsgi.py
            wsgi_file = "wsgi.py"
            for root, _, files in os.walk(project_root):
                if "wsgi.py" in files:
                    rel_path = Path(root).relative_to(project_root)
                    wsgi_file = str(rel_path / "wsgi.py").replace("\\", "/")
                    break

            # 提取Django项目名称（通常是包含wsgi.py的目录的父目录）
            django_project_name = wsgi_file.split("/")[0] if "/" in wsgi_file else project_name

            gunicorn_service_content = f"""[Unit]
Description=Gunicorn daemon for Django project {project_name}
After=network.target

[Service]
User={self.username}
Group=www-data
WorkingDirectory={remote_project_path}
Environment="PATH={remote_project_path}/venv/bin"
ExecStart={remote_project_path}/venv/bin/gunicorn --workers 3 --bind unix:{project_name}.sock {django_project_name}.wsgi:application

[Install]
WantedBy=multi-user.target
"""

            service_file = f"/etc/systemd/system/{project_name}.service"
            write_service_cmd = f"echo '{gunicorn_service_content}' | sudo tee {service_file}"
            self.execute_remote_command(write_service_cmd)

            # 8. 启动Gunicorn服务
            if progress_callback:
                progress_callback("启动Gunicorn服务", 0, 100)

            reload_cmd = "sudo systemctl daemon-reload"
            self.execute_remote_command(reload_cmd)

            start_cmd = f"sudo systemctl start {project_name}"
            exit_status, output, error = self.execute_remote_command(start_cmd)

            if exit_status != 0:
                raise Exception(f"启动Gunicorn服务失败: {error}")

            enable_cmd = f"sudo systemctl enable {project_name}"
            self.execute_remote_command(enable_cmd)

            # 9. 配置Nginx
            if progress_callback:
                progress_callback("配置Nginx", 0, 100)

            nginx_config = f"""
server {{
    listen 80;
    server_name _;

    location / {{
        include proxy_params;
        proxy_pass http://unix:{remote_project_path}/{project_name}.sock;
    }}

    # 静态文件
    location /static/ {{
        alias {remote_project_path}/static/;
    }}

    # 媒体文件
    location /media/ {{
        alias {remote_project_path}/media/;
    }}
}}
"""

            nginx_conf_path = f"/etc/nginx/sites-available/{project_name}"
            nginx_enabled_path = f"/etc/nginx/sites-enabled/{project_name}"

            write_config_cmd = f"echo '{nginx_config}' | sudo tee {nginx_conf_path}"
            self.execute_remote_command(write_config_cmd)

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
            raise Exception(f"Django项目部署失败: {str(e)}")

    def deploy_express_project(self, project_root: str, remote_dir: Optional[str] = None,
                              progress_callback: Optional[Callable[[str, int, int], None]] = None) -> str:
        """
        部署Express项目到远程服务器
        包括：上传项目、安装依赖、配置PM2、配置Nginx、启动服务

        Args:
            project_root (str): Express项目根目录
            remote_dir (str, optional): 远程部署目录
            progress_callback (Callable, optional): 进度回调函数

        Returns:
            str: 部署完成后的项目路径
        """
        project_root = Path(project_root).resolve()

        if remote_dir is None:
            remote_dir = f"/home/{self.username}/express-apps"

        try:
            # 1. 检查是否为Express项目
            package_json = project_root / "package.json"

            if not package_json.exists():
                raise Exception("不是有效的Express/Node.js项目，未找到package.json文件")

            if progress_callback:
                progress_callback("上传Express项目", 0, 100)

            # 2. 上传项目文件
            remote_project_path = self.upload_and_extract(
                str(project_root),
                remote_dir,
                progress_callback=progress_callback
            )

            project_name = project_root.name

            # 3. 检查并安装PM2（进程管理器）
            if progress_callback:
                progress_callback("检查PM2环境", 0, 100)

            check_pm2_cmd = "command -v pm2"
            exit_status, output, error = self.execute_remote_command(check_pm2_cmd)

            if exit_status != 0:
                if progress_callback:
                    progress_callback("安装PM2", 0, 100)

                # 安装PM2
                install_pm2_cmd = "sudo npm install -g pm2"
                exit_status, output, error = self.execute_remote_command(install_pm2_cmd)

                if exit_status != 0:
                    raise Exception(f"PM2安装失败: {error}")

            # 4. 安装Node.js依赖
            if progress_callback:
                progress_callback("安装Node.js依赖", 0, 100)

            install_cmd = f"cd {remote_project_path} && npm install --production"
            exit_status, output, error = self.execute_remote_command(install_cmd)

            if exit_status != 0:
                raise Exception(f"安装依赖失败: {error}")

            # 5. 查找Express入口文件
            if progress_callback:
                progress_callback("查找入口文件", 0, 100)

            # 读取package.json查找入口文件
            read_package_cmd = f"cat {remote_project_path}/package.json"
            exit_status, package_json_content, error = self.execute_remote_command(read_package_cmd)

            entry_file = "app.js"  # 默认入口文件
            if exit_status == 0 and "main" in package_json_content:
                # 尝试从package.json中提取main字段
                try:
                    import json
                    package_data = json.loads(package_json_content)
                    if "main" in package_data:
                        entry_file = package_data["main"]
                except:
                    pass

            # 验证入口文件存在
            check_entry_cmd = f"test -f {remote_project_path}/{entry_file} && echo 'exists'"
            exit_status, output, error = self.execute_remote_command(check_entry_cmd)

            if exit_status != 0 or "exists" not in output:
                # 尝试其他常见入口文件
                common_entries = ["app.js", "server.js", "index.js", "main.js"]
                for test_entry in common_entries:
                    test_cmd = f"test -f {remote_project_path}/{test_entry} && echo 'found'"
                    exit_status, output, error = self.execute_remote_command(test_cmd)
                    if exit_status == 0 and "found" in output:
                        entry_file = test_entry
                        break

            # 6. 启动Express应用（使用PM2）
            if progress_callback:
                progress_callback("启动Express应用", 0, 100)

            # 先停止可能存在的旧进程
            stop_cmd = f"pm2 stop {project_name} 2>/dev/null || true"
            self.execute_remote_command(stop_cmd)

            delete_cmd = f"pm2 delete {project_name} 2>/dev/null || true"
            self.execute_remote_command(delete_cmd)

            # 启动应用
            start_cmd = f"cd {remote_project_path} && pm2 start {entry_file} --name {project_name}"
            exit_status, output, error = self.execute_remote_command(start_cmd)

            if exit_status != 0:
                raise Exception(f"启动Express应用失败: {error}")

            # 保存PM2进程列表
            save_cmd = "pm2 save"
            self.execute_remote_command(save_cmd)

            # 设置PM2开机自启
            startup_cmd = "pm2 startup systemd -u ${USER} --hp /home/${USER} 2>/dev/null || env PATH=$PATH:/usr/bin pm2 startup systemd -u ${USER} --hp /home/${USER} 2>/dev/null || true"
            self.execute_remote_command(startup_cmd)

            # 7. 配置Nginx反向代理
            if progress_callback:
                progress_callback("配置Nginx", 0, 100)

            # 获取Express应用的端口（默认3000）
            # 可以通过环境变量或配置文件读取，这里使用默认3000
            app_port = "3000"

            nginx_config = f"""
server {{
    listen 80;
    server_name _;

    location / {{
        proxy_pass http://127.0.0.1:{app_port};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }}
}}
"""

            nginx_conf_path = f"/etc/nginx/sites-available/{project_name}"
            nginx_enabled_path = f"/etc/nginx/sites-enabled/{project_name}"

            write_config_cmd = f"echo '{nginx_config}' | sudo tee {nginx_conf_path}"
            self.execute_remote_command(write_config_cmd)

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
            raise Exception(f"Express项目部署失败: {str(e)}")

    def configure_apt_mirror(
        self,
        mirror_name: str,
        ubuntu_version: str = "22.04",
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> bool:
        """
        配置APT软件源（Ubuntu/Debian）

        Args:
            mirror_name: 镜像源名称 (aliyun, tencent, huawei, ustc, tsinghua, netease, sohu)
            ubuntu_version: Ubuntu版本号
            progress_callback: 进度回调函数

        Returns:
            bool: 配置是否成功
        """
        try:
            if progress_callback:
                progress_callback("备份原始源配置", 0, 100)

            # 备份原始源配置
            backup_cmd = "sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup"
            self.execute_remote_command(backup_cmd)

            # 根据镜像源名称生成配置
            mirror_urls = {
                "aliyun": "mirrors.aliyun.com",
                "tencent": "mirrors.cloud.tencent.com",
                "huawei": "mirrors.huaweicloud.com",
                "ustc": "mirrors.ustc.edu.cn",
                "tsinghua": "mirrors.tuna.tsinghua.edu.cn",
                "netease": "mirrors.163.com",
                "sohu": "mirrors.sohu.com",
            }

            if mirror_name not in mirror_urls:
                raise Exception(f"不支持的镜像源: {mirror_name}")

            mirror_url = mirror_urls[mirror_name]

            if progress_callback:
                progress_callback("生成新的源配置", 20, 100)

            # 生成新的源配置
            sources_content = f"""# {mirror_name.upper()} Mirror - Ubuntu {ubuntu_version}
# Generated by DeployUpload

deb https://{mirror_url}/ubuntu/ jammy main restricted universe multiverse
deb https://{mirror_url}/ubuntu/ jammy-updates main restricted universe multiverse
deb https://{mirror_url}/ubuntu/ jammy-backports main restricted universe multiverse
deb https://{mirror_url}/ubuntu/ jammy-security main restricted universe multiverse
"""

            if progress_callback:
                progress_callback("写入新的源配置", 40, 100)

            # 写入新的源配置
            write_cmd = f"echo '{sources_content}' | sudo tee /etc/apt/sources.list"
            exit_status, output, error = self.execute_remote_command(write_cmd)

            if exit_status != 0:
                raise Exception(f"写入源配置失败: {error}")

            if progress_callback:
                progress_callback("更新软件包列表", 60, 100)

            # 更新软件包列表
            update_cmd = "sudo DEBIAN_FRONTEND=noninteractive apt-get update"
            exit_status, output, error = self.execute_remote_command(update_cmd)

            if exit_status != 0:
                # 如果更新失败，恢复原始配置
                restore_cmd = "sudo cp /etc/apt/sources.list.backup /etc/apt/sources.list"
                self.execute_remote_command(restore_cmd)
                raise Exception(f"更新软件包列表失败: {error}")

            if progress_callback:
                progress_callback("配置完成", 100, 100)

            return True

        except Exception as e:
            raise Exception(f"配置APT软件源失败: {str(e)}")

    def configure_yum_mirror(
        self,
        mirror_name: str,
        centos_version: int = 7,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> bool:
        """
        配置YUM软件源（CentOS/RHEL）

        Args:
            mirror_name: 镜像源名称 (aliyun, tencent, huawei, ustc, tsinghua, netease, sohu)
            centos_version: CentOS版本号
            progress_callback: 进度回调函数

        Returns:
            bool: 配置是否成功
        """
        try:
            if progress_callback:
                progress_callback("备份原始源配置", 0, 100)

            # 备份原始源配置
            backup_cmd = "sudo cp -r /etc/yum.repos.d /etc/yum.repos.d.backup"
            self.execute_remote_command(backup_cmd)

            # 根据镜像源名称生成配置
            mirror_urls = {
                "aliyun": "mirrors.aliyun.com",
                "tencent": "mirrors.cloud.tencent.com",
                "huawei": "mirrors.huaweicloud.com",
                "ustc": "mirrors.ustc.edu.cn",
                "tsinghua": "mirrors.tuna.tsinghua.edu.cn",
                "netease": "mirrors.163.com",
                "sohu": "mirrors.sohu.com",
            }

            if mirror_name not in mirror_urls:
                raise Exception(f"不支持的镜像源: {mirror_name}")

            mirror_url = mirror_urls[mirror_name]

            if progress_callback:
                progress_callback("生成新的源配置", 20, 100)

            # 生成CentOS-Base.repo配置
            repo_content = f"""# {mirror_name.upper()} Mirror - CentOS {centos_version}
# Generated by DeployUpload

[base]
name=CentOS-{centos_version} - Base - {mirror_name}
baseurl=https://{mirror_url}/centos/$releasever/os/$basearch/
gpgcheck=1
gpgkey=https://{mirror_url}/centos/RPM-GPG-KEY-CentOS-$releasever
enabled=1

[updates]
name=CentOS-{centos_version} - Updates - {mirror_name}
baseurl=https://{mirror_url}/centos/$releasever/updates/$basearch/
gpgcheck=1
gpgkey=https://{mirror_url}/centos/RPM-GPG-KEY-CentOS-$releasever
enabled=1

[extras]
name=CentOS-{centos_version} - Extras - {mirror_name}
baseurl=https://{mirror_url}/centos/$releasever/extras/$basearch/
gpgcheck=1
gpgkey=https://{mirror_url}/centos/RPM-GPG-KEY-CentOS-$releasever
enabled=1
"""

            if progress_callback:
                progress_callback("写入新的源配置", 40, 100)

            # 写入新的源配置
            write_cmd = f"echo '{repo_content}' | sudo tee /etc/yum.repos.d/CentOS-Base.repo"
            exit_status, output, error = self.execute_remote_command(write_cmd)

            if exit_status != 0:
                raise Exception(f"写入源配置失败: {error}")

            if progress_callback:
                progress_callback("清理缓存", 60, 100)

            # 清理YUM缓存
            clean_cmd = "sudo yum clean all"
            self.execute_remote_command(clean_cmd)

            if progress_callback:
                progress_callback("重建缓存", 80, 100)

            # 重建YUM缓存
            makecache_cmd = "sudo yum makecache"
            exit_status, output, error = self.execute_remote_command(makecache_cmd)

            if exit_status != 0:
                # 如果重建缓存失败，恢复原始配置
                restore_cmd = "sudo rm -rf /etc/yum.repos.d && sudo mv /etc/yum.repos.d.backup /etc/yum.repos.d"
                self.execute_remote_command(restore_cmd)
                raise Exception(f"重建YUM缓存失败: {error}")

            if progress_callback:
                progress_callback("配置完成", 100, 100)

            return True

        except Exception as e:
            raise Exception(f"配置YUM软件源失败: {str(e)}")

    def restore_default_mirror(
        self,
        pkg_manager: str = "apt",
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> bool:
        """
        恢复默认软件源

        Args:
            pkg_manager: 包管理器类型 (apt, yum)
            progress_callback: 进度回调函数

        Returns:
            bool: 恢复是否成功
        """
        try:
            if progress_callback:
                progress_callback("恢复默认源", 0, 100)

            if pkg_manager == "apt":
                # 检查备份文件是否存在
                check_cmd = "test -f /etc/apt/sources.list.backup && echo 'exists'"
                exit_status, output, error = self.execute_remote_command(check_cmd)

                if exit_status == 0 and "exists" in output:
                    # 恢复备份
                    restore_cmd = "sudo cp /etc/apt/sources.list.backup /etc/apt/sources.list"
                    self.execute_remote_command(restore_cmd)

                    # 更新软件包列表
                    if progress_callback:
                        progress_callback("更新软件包列表", 50, 100)

                    update_cmd = "sudo DEBIAN_FRONTEND=noninteractive apt-get update"
                    exit_status, output, error = self.execute_remote_command(update_cmd)

                    if exit_status != 0:
                        raise Exception(f"更新软件包列表失败: {error}")
                else:
                    raise Exception("未找到备份文件，无法恢复")

            elif pkg_manager == "yum":
                # 检查备份目录是否存在
                check_cmd = "test -d /etc/yum.repos.d.backup && echo 'exists'"
                exit_status, output, error = self.execute_remote_command(check_cmd)

                if exit_status == 0 and "exists" in output:
                    # 恢复备份
                    restore_cmd = "sudo rm -rf /etc/yum.repos.d && sudo mv /etc/yum.repos.d.backup /etc/yum.repos.d"
                    self.execute_remote_command(restore_cmd)

                    # 重建缓存
                    if progress_callback:
                        progress_callback("重建缓存", 50, 100)

                    makecache_cmd = "sudo yum makecache"
                    exit_status, output, error = self.execute_remote_command(makecache_cmd)

                    if exit_status != 0:
                        raise Exception(f"重建YUM缓存失败: {error}")
                else:
                    raise Exception("未找到备份目录，无法恢复")

            if progress_callback:
                progress_callback("恢复完成", 100, 100)

            return True

        except Exception as e:
            raise Exception(f"恢复默认软件源失败: {str(e)}")


