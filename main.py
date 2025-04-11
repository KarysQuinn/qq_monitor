import os
import time
import logging
import psutil
import ctypes
import win32gui
import win32process
from subprocess import Popen
from datetime import datetime
from colorama import init, Fore, Back, Style

# 初始化colorama
init(convert=True)

# 日志配置
LOG_FILE = "qq_monitor.log"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
EMOJI_MAP = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌"}

# 自定义日志等级颜色
LOG_COLORS = {
    "INFO": Fore.CYAN,
    "SUCCESS": Fore.GREEN,
    "WARNING": Fore.YELLOW,
    "ERROR": Fore.RED,
}


class ColorfulFormatter(logging.Formatter):
    """带颜色和emoji的日志格式化器"""

    def format(self, record):
        # 添加emoji
        record.emoji = EMOJI_MAP.get(record.levelname, "  ")
        # 添加颜色
        color = LOG_COLORS.get(record.levelname, Fore.WHITE)
        message = super().format(record)
        return f"{color}{message}{Style.RESET_ALL}"


# 初始化日志系统
logger = logging.getLogger("QQMonitor")
logger.setLevel(logging.INFO)

# 文件日志（无颜色）
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_formatter = logging.Formatter(LOG_FORMAT)
file_handler.setFormatter(file_formatter)

# 控制台日志（带颜色）
console_handler = logging.StreamHandler()
console_formatter = ColorfulFormatter(LOG_FORMAT)
console_handler.setFormatter(console_formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)


def is_admin():
    """检查管理员权限"""
    try:
        admin = ctypes.windll.shell32.IsUserAnAdmin()
        if admin:
            logger.info("管理员权限验证成功 👮")
        return admin
    except Exception as e:
        logger.error(f"权限检查失败: {e} 🚫")
        return False


def elevate_privileges():
    """提升权限"""
    try:
        logger.warning("正在请求管理员权限... 🔒")
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", "python", f'"{__file__}"', None, 1
        )
    except Exception as e:
        logger.error(f"权限提升失败: {e} 🚨")


def get_foreground_pid():
    """获取前台进程ID"""
    try:
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return pid
    except Exception as e:
        logger.error(f"获取前台窗口失败: {e} 🖥️")
        return None


def kill_process(proc_name):
    """终止进程"""
    logger.info(f"正在终止进程: {proc_name} 💀")
    killed = 0
    for proc in psutil.process_iter(["pid", "name"]):
        if proc.info["name"].lower() == proc_name.lower():
            try:
                psutil.Process(proc.info["pid"]).terminate()
                killed += 1
                logger.success(f"成功终止进程: {proc_name} (PID: {proc.info['pid']}) ☠️")
            except Exception as e:
                logger.error(f"终止进程失败 [{proc_name}]: {e} ⚠️")
    return killed


def start_qq():
    """启动QQ"""
    qq_path = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\腾讯软件\QQ\QQ.lnk"
    logger.info(f"正在启动QQ... 🚀")
    try:
        Popen(["explorer", qq_path])
        logger.success("QQ启动成功 🎉")
        return True
    except Exception as e:
        logger.error(f"QQ启动失败: {e} 💥")
        return False


def main_loop():
    """主监控循环"""
    last_trigger = 0
    cooldown = 60

    logger.info("监控程序已启动 🛡️")
    while True:
        try:
            fg_pid = get_foreground_pid()
            if fg_pid:
                proc = psutil.Process(fg_pid)
                if proc.name() == "crashpad_handler.exe":
                    if time.time() - last_trigger > cooldown:
                        logger.warning("检测到crashpad_handler进入前台! 🔍")

                        # 终止进程
                        killed_crashpad = kill_process("crashpad_handler.exe")
                        killed_qq = kill_process("qq.exe")

                        # 启动QQ
                        if start_qq():
                            logger.success(
                                f"操作完成: 终止{crashed_crashpad}个crashpad进程和{killed_qq}个QQ进程 🔄"
                            )
                        else:
                            logger.error("QQ重启失败，请检查快捷方式路径! 🚧")

                        last_trigger = time.time()
                    else:
                        logger.info("冷却时间中，跳过处理 ⏳")
        except Exception as e:
            logger.error(f"监控异常: {e} 🔥")

        time.sleep(5)


if __name__ == "__main__":
    # 添加自定义日志等级
    logging.addLevelName(25, "SUCCESS")
    setattr(logger, "success", lambda message, *args: logger._log(25, message, args))

    if not is_admin():
        elevate_privileges()
    else:
        try:
            main_loop()
        except KeyboardInterrupt:
            logger.info("监控程序已手动终止 🛑")
