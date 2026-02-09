# DeployUpload

一个用于将本地文件夹打包并上传到远程服务器的图形化工具。支持Vue项目一键部署、Ubuntu环境自动安装等功能。

## 功能特性

- 🚀 **简单易用**: 图形化界面，只需点击即可完成项目部署
- 📦 **智能打包**: 自动忽略.gitignore和.deploy_ignore中指定的文件
- 📊 **进度显示**: 实时显示上传进度和当前阶段
- 🔒 **安全连接**: 使用SSH/SFTP协议安全传输文件
- 🎯 **灵活配置**: 支持自定义远程目录
- 🖥️ **图形界面**: 提供Windows Vista风格的图形界面，操作更加直观
- 🌐 **Vue项目一键部署**: 自动上传、构建并配置Nginx
- ⚙️ **Ubuntu环境安装**: 一键安装MySQL、Redis、Nginx

## 安装

```bash
# 安装依赖
pip install -r requirements.txt

# 运行程序
python main.py
```

或者从源码运行：

```bash
git clone https://github.com/pengcunfu/DeployUpload.git
cd DeployUpload
pip install -r requirements.txt
python main.py
```

## 快速开始

### 启动程序

双击运行 `main.py` 或在命令行中执行：

```bash
python main.py
```

### 基本部署流程

1. **配置服务器信息**
   - 填写服务器主机地址、用户名、密码
   - 设置SSH端口（默认22）
   - 点击"测试连接"确保连接成功

2. **选择项目**
   - 点击"浏览..."选择要部署的项目目录
   - 可选：填写远程目录（留空则使用默认目录）

3. **开始部署**
   - 点击"开始上传"按钮
   - 查看实时日志和进度
   - 等待部署完成

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

## 项目结构

```
DeployUpload/
├── main.py                 # 程序入口
├── app/
│   ├── __init__.py        # 应用包初始化
│   ├── gui.py             # 图形界面
│   └── uploader.py        # 上传核心逻辑
├── requirements.txt        # 依赖列表
└── README.md              # 说明文档
```

## 编程接口

如果你想在自己的代码中使用DeployUpload的功能，可以这样：

```python
from app import ProjectUploader

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

##### deploy_vue_project()

部署Vue项目到远程服务器。

```python
deploy_vue_project(project_root, remote_dir=None, progress_callback=None)
```

**参数:**
- `project_root` (str): Vue项目根目录
- `remote_dir` (str, optional): 远程部署目录
- `progress_callback` (callable, optional): 进度回调函数

**返回:** 远程项目目录路径

##### install_mysql()

在Ubuntu服务器上安装MySQL。

```python
install_mysql(root_password='root', progress_callback=None)
```

**参数:**
- `root_password` (str): MySQL root密码
- `progress_callback` (callable, optional): 进度回调函数

**返回:** bool - 安装是否成功

##### install_redis()

在Ubuntu服务器上安装Redis。

```python
install_redis(progress_callback=None)
```

**参数:**
- `progress_callback` (callable, optional): 进度回调函数

**返回:** bool - 安装是否成功

##### install_nginx()

在Ubuntu服务器上安装Nginx。

```python
install_nginx(progress_callback=None)
```

**参数:**
- `progress_callback` (callable, optional): 进度回调函数

**返回:** bool - 安装是否成功

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