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
init(autoreset=True)

# ================= 日志配置 =================
LOG_FILE = "qq_monitor.log"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
EMOJI_MAP = {
    'DEBUG':    '🐛',
    'INFO':     'ℹ️',
    'SUCCESS':  '✅',
    'WARNING':  '⚠️',
    'ERROR':    '❌'
}

LOG_COLORS = {
    'DEBUG':    Fore.WHITE,
    'INFO':     Fore.CYAN,
    'SUCCESS':  Fore.GREEN,
    'WARNING':  Fore.YELLOW,
    'ERROR':    Fore.RED + Style.BRIGHT
}

class EmojiFormatter(logging.Formatter):
    """带颜色和emoji的日志格式化器"""
    def format(self, record):
        record.emoji = EMOJI_MAP.get(record.levelname, '  ')
        color = LOG_COLORS.get(record.levelname, Fore.WHITE)
        message = super().format(record)
        return f"{color}{message}{Style.RESET_ALL}"

# 初始化日志系统
logger = logging.getLogger('QQMonitor')
logger.setLevel(logging.DEBUG)  # 启用DEBUG级别

# 文件日志处理器
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_formatter = logging.Formatter(LOG_FORMAT)
file_handler.setFormatter(file_formatter)

# 控制台日志处理器
console_handler = logging.StreamHandler()
console_formatter = EmojiFormatter(LOG_FORMAT)
console_handler.setFormatter(console_formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ================= 系统函数 =================
def is_admin():
    """检查管理员权限"""
    try:
        admin = ctypes.windll.shell32.IsUserAnAdmin()
        if admin:
            logger.info("管理员权限验证成功 👮♂️")
        return admin
    except Exception as e:
        logger.error(f"权限检查失败: {e} 🚫")
        return False

def elevate_privileges():
    """提升权限"""
    try:
        logger.warning("正在请求管理员权限... 🔒")
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", "python", f'"{__file__}"', None, 1)
    except Exception as e:
        logger.error(f"权限提升失败: {e} 🚨")
        exit(1)

# ================= 进程管理 =================
def get_foreground_pid():
    """获取前台进程ID（增强验证版）"""
    try:
        hwnd = win32gui.GetForegroundWindow()
        
        # 验证窗口句柄有效性
        if hwnd == 0:
            logger.debug("无有效前台窗口")
            return None
            
        # 获取进程ID
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        
        # PID有效性验证
        if not isinstance(pid, int) or pid <= 0:
            logger.warning(f"无效的进程ID: {pid}")
            return None
            
        # 验证进程是否存在
        if not psutil.pid_exists(pid):
            logger.debug(f"进程不存在: PID={pid}")
            return None
            
        return pid
    except Exception as e:
        logger.error(f"获取前台窗口失败: {e} 🖥️")
        return None

def kill_process(proc_name):
    """安全终止进程"""
    logger.info(f"正在终止进程: {proc_name} 💀")
    killed = 0
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'].lower() == proc_name.lower():
                p = psutil.Process(proc.info['pid'])
                # 检查进程状态
                if p.status() == psutil.STATUS_ZOMBIE:
                    logger.warning(f"忽略僵尸进程: {proc_name} (PID: {p.pid})")
                    continue
                p.terminate()
                killed += 1
                logger.success(f"成功终止进程: {proc_name} (PID: {p.pid}) ☠️")
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.warning(f"进程访问异常 [{proc_name}]: {e} ⚠️")
        except Exception as e:
            logger.error(f"终止进程失败 [{proc_name}]: {e} 💥")
    return killed

def start_qq():
    """安全启动QQ"""
    qq_path = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\腾讯软件\QQ\QQ.lnk"
    logger.info(f"正在启动QQ... 🚀")
    try:
        if not os.path.exists(qq_path):
            logger.error("QQ快捷方式不存在！ 📛")
            return False
            
        Popen(['explorer', qq_path])
        logger.success("QQ启动成功 🎉")
        return True
    except Exception as e:
        logger.error(f"QQ启动失败: {e} 💥")
        return False

# ================= 主逻辑 =================
def main_loop():
    """增强型监控循环"""
    last_trigger = 0
    cooldown = 60
    error_count = 0
    MAX_RETRY_DELAY = 300  # 最大重试延迟5分钟

    logger.info("监控程序已启动 🛡️")
    while True:
        try:
            fg_pid = get_foreground_pid()
            if not fg_pid:
                time.sleep(1)  # 无有效PID时快速重试
                continue

            try:
                proc = psutil.Process(fg_pid)
                proc_name = proc.name()
                
                # 检查进程状态
                if proc.status() == psutil.STATUS_ZOMBIE:
                    logger.warning(f"检测到僵尸进程: {proc_name}")
                    continue
                    
                if proc_name == 'crashpad_handler.exe':
                    current_time = time.time()
                    if current_time - last_trigger > cooldown:
                        logger.warning("检测到crashpad_handler进入前台! 🔍")
                        
                        # 终止进程
                        killed_crashpad = kill_process('crashpad_handler.exe')
                        killed_qq = kill_process('qq.exe')
                        
                        # 启动QQ
                        if start_qq():
                            logger.success(f"操作完成: 终止{killed_crashpad}个crashpad进程和{killed_qq}个QQ进程 🔄")
                        else:
                            logger.error("QQ重启失败，请检查快捷方式路径! 🚧")
                        
                        last_trigger = current_time
                    else:
                        logger.info(f"冷却时间剩余: {cooldown - int(current_time - last_trigger)}秒 ⏳")
            
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.warning(f"进程状态异常: {e} ⚠️")
            
            error_count = 0  # 重置错误计数
            time.sleep(5)
            
        except Exception as e:
            error_count += 1
            delay = min(2 ** error_count, MAX_RETRY_DELAY)
            logger.error(f"监控异常: {str(e)[:100]} [将延迟{delay}秒] 🔥")
            time.sleep(delay)

if __name__ == "__main__":
    # 注册自定义日志等级
    logging.addLevelName(25, "SUCCESS")
    setattr(logger, 'success', lambda message, *args: logger._log(25, message, args))
    
    if not is_admin():
        elevate_privileges()
    else:
        try:
            main_loop()
        except KeyboardInterrupt:
            logger.info("监控程序已手动终止 🛑")
        except Exception as e:
            logger.critical(f"未捕获的异常: {e} 💣")
