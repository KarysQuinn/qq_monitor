# QQ进程守护程序

解决QQ进程崩溃无自愈的问题而设计。当检测到`crashpad_handler.exe`异常转为前台时，自动重启QQ进程。

## 背景说明

在长时间使用QQ时，经常遇到：
1. QQ进程（qq.exe）意外崩溃
2. `crashpad_handler.exe`接管崩溃报告但无法自动恢复
3. 需要人工干预重启QQ

本程序通过24小时监控系统进程，实现：
✅ 异常状态检测  
✅ 自动清理残留进程  
✅ 智能重启QQ  
✅ 防误触机制

## 功能特性

- 实时监控`crashpad_handler.exe`窗口状态
- 自动终止异常进程（qq.exe + crashpad_handler.exe）
- 使用原生方式启动QQ客户端
- 管理员权限自动提权
- 防重复触发的冷却机制
- 低资源占用轮询设计（5秒/次）

## 安装使用

### 前置要求
- Windows 10/11 系统
- Python 3.7+
- QQ客户端已正确安装

### 快速开始
1. 安装依赖库：
```bash
pip install psutil pywin32
