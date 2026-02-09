# DeployUpload

一个用于将本地文件夹打包并上传到远程服务器的Python包。支持进度回调、.gitignore文件过滤等功能。

## 功能特性

- 🚀 **简单易用**: 只需几行代码即可完成文件夹打包上传
- 📦 **智能打包**: 自动忽略.gitignore和.deploy_ignore中指定的文件
- 📊 **进度回调**: 支持自定义进度回调函数，实时监控上传进度
- 🔒 **安全连接**: 使用SSH/SFTP协议安全传输文件
- 🎯 **灵活配置**: 支持自定义忽略模式和文件
- 📱 **命令行工具**: 提供便捷的命令行接口
- 🖥️ **图形界面**: 提供Windows Vista风格的图形界面，操作更加直观

## 安装

```bash
pip install deployupload
```

或者从源码安装：

```bash
git clone https://github.com/pengcunfu/DeployUpload.git
cd DeployUpload
pip install -e .
```

## 快速开始

### 基本使用

```python
from deployupload import ProjectUploader

# 创建上传器实例
uploader = ProjectUploader(
    host='192.168.1.100',
    username='ubuntu',
    password='your_password',
    port=22
)

# 上传项目文件夹
remote_path = uploader.upload_and_extract('/path/to/your/project')
print(f"项目已上传到: {remote_path}")
```

### 带进度回调的使用

```python
from deployupload import ProjectUploader

def my_progress_callback(stage, current, total):
    """自定义进度回调函数"""
    if total > 0:
        percent = (current / total) * 100
        print(f"{stage}: {percent:.1f}% ({current}/{total})")
    else:
        print(f"{stage}: {current}")

# 创建上传器
uploader = ProjectUploader('192.168.1.100', 'ubuntu', 'password')

# 带进度回调的上传
uploader.upload_and_extract(
    '/path/to/project',
    progress_callback=my_progress_callback
)
```

### 高级配置

```python
from deployupload import ProjectUploader

# 创建上传器
uploader = ProjectUploader('192.168.1.100', 'ubuntu', 'password')

# 设置额外的忽略模式
uploader.set_ignore_patterns(['*.log', 'temp/*', '*.tmp'])

# 设置额外的忽略文件
uploader.set_ignore_files(['/path/to/specific/file.txt'])

# 测试连接
if uploader.test_connection():
    print("服务器连接成功")
    
    # 只创建压缩包（不上传）
    archive_path = uploader.create_archive('/path/to/project')
    print(f"压缩包已创建: {archive_path}")
    
    # 只上传文件（不解压）
    remote_path = uploader.upload_file(archive_path)
    print(f"文件已上传到: {remote_path}")
else:
    print("服务器连接失败")
```

## 命令行使用

安装后可以直接使用命令行工具：

```bash
# 交互式使用
deployupload -i

# 直接指定参数
deployupload --host 192.168.1.100 --username ubuntu --password your_password

# 指定项目目录和远程目录
deployupload --host 192.168.1.100 --username ubuntu --password your_password \
             --project-root /path/to/project --remote-dir /home/ubuntu/projects
```

## 图形界面使用

### 启动GUI

安装依赖后，可以通过以下方式启动图形界面：

```bash
# 方法1：直接运行
python deployupload_gui.py

# 方法2：使用命令
deployupload-gui
```

### GUI功能

- **Windows Vista风格界面**：现代化的用户界面设计
- **实时进度显示**：显示上传进度和当前阶段
- **日志输出**：实时查看上传日志
- **连接测试**：上传前测试服务器连接
- **多线程上传**：界面不会冻结，操作流畅
- **Vue项目一键部署**：自动上传、构建并配置Nginx
- **Ubuntu环境安装**：一键安装MySQL、Redis、Nginx

详细使用说明请参考 [GUI使用指南](GUI_USAGE.md)

### 菜单栏功能

GUI提供了两个主要菜单：

#### 部署菜单 (D)
- **Vue项目一键部署 (V)**：自动完成Vue项目的完整部署流程
  1. 上传项目文件到服务器
  2. 执行 `npm install` 安装依赖
  3. 执行 `npm run build` 构建项目
  4. 自动配置Nginx站点
  5. 重启Nginx服务

#### Ubuntu环境菜单 (U)
- **安装MySQL (M)**：在远程Ubuntu服务器上安装MySQL数据库
  - 自动设置root密码
  - 自动启动服务
- **安装Redis (R)**：在远程Ubuntu服务器上安装Redis缓存服务
  - 自动启动服务
- **安装Nginx (N)**：在远程Ubuntu服务器上安装Nginx Web服务器
  - 自动启动服务
- **一键安装全部 (A)**：同时安装MySQL、Redis、Nginx

### 使用前提

1. **配置SSH连接**：在使用任何部署或安装功能前，请先：
   - 填写服务器主机地址、用户名、密码
   - 点击"测试连接"按钮确保连接成功

2. **Vue项目要求**：
   - 本地项目必须是标准的Vue项目（包含package.json）
   - 服务器上需要预装Node.js和npm
   - 服务器需要配置sudo权限（用于配置Nginx）

3. **Ubuntu环境安装要求**：
   - 远程服务器必须是Ubuntu系统
   - 用户需要有sudo权限（用于安装软件包）

## API 文档

### ProjectUploader 类

#### 构造函数

```python
ProjectUploader(host, username, password, port=22)
```

**参数:**
- `host` (str): 服务器IP地址或域名
- `username` (str): 服务器用户名  
- `password` (str): 服务器密码
- `port` (int): SSH端口，默认为22

#### 主要方法

##### upload_and_extract()

打包、上传并解压项目文件夹。

```python
upload_and_extract(project_root, remote_dir=None, progress_callback=None)
```

**参数:**
- `project_root` (str): 项目根目录路径
- `remote_dir` (str, optional): 远程解压目录，默认为用户home目录
- `progress_callback` (callable, optional): 进度回调函数

**返回:** 远程项目目录路径

##### create_archive()

创建项目压缩包。

```python
create_archive(project_root, output_path=None, progress_callback=None)
```

**参数:**
- `project_root` (str): 项目根目录路径
- `output_path` (str, optional): 输出压缩包路径
- `progress_callback` (callable, optional): 进度回调函数

**返回:** 压缩包路径

##### upload_file()

上传文件到服务器。

```python
upload_file(local_path, remote_path=None, progress_callback=None)
```

**参数:**
- `local_path` (str): 本地文件路径
- `remote_path` (str, optional): 远程文件路径
- `progress_callback` (callable, optional): 进度回调函数

**返回:** 远程文件路径

##### test_connection()

测试服务器连接。

```python
test_connection()
```

**返回:** bool - 连接是否成功

## 忽略文件配置

DeployUpload 支持多种方式配置忽略文件：

### .gitignore 文件

自动读取项目中的所有 `.gitignore` 文件，支持标准的 gitignore 语法。

### .deploy_ignore 文件

专门用于部署时的忽略配置，语法与 `.gitignore` 相同。

### 代码配置

```python
# 设置忽略模式
uploader.set_ignore_patterns(['*.log', 'temp/*'])

# 设置忽略文件
uploader.set_ignore_files(['/path/to/file'])
```

## 进度回调

进度回调函数接收三个参数：

```python
def progress_callback(stage, current, total):
    """
    stage: 当前阶段名称 (str)
    current: 当前进度 (int)  
    total: 总进度 (int)
    """
    pass
```

可能的阶段包括：
- "收集忽略模式"
- "计算文件数量" 
- "复制文件"
- "创建压缩包"
- "连接服务器"
- "上传文件"
- "解压文件"

## 依赖要求

- Python >= 3.7
- paramiko >= 3.0.0
- tqdm >= 4.64.0

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v1.0.0
- 初始版本发布
- 支持文件夹打包上传
- 支持进度回调
- 支持 .gitignore 文件过滤
- 提供命令行工具