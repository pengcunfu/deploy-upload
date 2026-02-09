#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeployUpload 应用包

提供图形界面的项目部署工具
"""

__version__ = '1.0.0'
__author__ = 'DeployUpload'

from .uploader import ProjectUploader
from .window import DeployUploadWindow

__all__ = ['ProjectUploader', 'DeployUploadWindow']
