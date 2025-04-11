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

# ================= 系统状态检测API =================
user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ('cbSize', ctypes.wintypes.UINT),
        ('dwTime', ctypes.wintypes.DWORD),
    ]

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
logger.setLevel(logging.INFO)

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

# ================= 智能日志管理 =================
class SmartLogger:
    def __init__(self):
        self.last_window_state = None
        self.last_log_time = 0
        self.log_interval = 300  # 5分钟记录一次持续状态

    def log_window_state(self, has_window):
        current_time = time.time()
        if has_window != self.last_window_state:
            if has_window:
                logger.debug("前台窗口恢复 👀")
            else:
                logger.debug("检测到无有效前台窗口 🔍")
            self.last_window_state = has_window
            self.last_log_time = current_time
        elif not has_window and (current_time - self.last_log_time) > self.log_interval:
            logger.debug(f"持续无有效前台窗口已 {self.log_interval}秒 ⏳")
            self.last_log_time = current_time

smart_logger = SmartLogger()

# ================= 系统状态检测 =================
def get_idle_duration():
    """获取系统空闲时间（毫秒）"""
    last_input_info = LASTINPUTINFO()
    last_input_info.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if user32.GetLastInputInfo(ctypes.byref(last_input_info)):
        return kernel32.GetTickCount() - last_input_info.dwTime
    return 0

def is_workstation_locked():
    """检测系统是否处于锁定状态"""
    try:
        hdesk = user32.OpenDesktopW("Default", 0, False, 0x0100)
        if hdesk == 0:
            return True
        user32.CloseDesktop(hdesk)
        return False
    except:
        return False

def is_remote_session():
    """检测是否在远程会话中"""
    try:
        return ctypes.windll.kernel32.GetSystemMetrics(0x1000) != 0  # SM_REMOTESESSION
    except:
        return os.getenv('SESSIONNAME', '').startswith('RDP-')

# ================= 系统函数 =================
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
            None, "runas", "python", f'"{__file__}"', None, 1)
    except Exception as e:
        logger.error(f"权限提升失败: {e} 🚨")
        exit(1)

# ================= 进程管理 =================
def get_foreground_pid():
    """增强版前台进程检测"""
    try:
        # 排除非活动系统状态
        if is_remote_session():
            return None
            
        if is_workstation_locked():
            return None
            
        if get_idle_duration() > 300000:  # 5分钟无操作视为可能锁定
            return None

        hwnd = win32gui.GetForegroundWindow()
        has_window = hwnd != 0
        
        # 智能日志记录
        smart_logger.log_window_state(has_window)
        
        if not has_window:
            return None
            
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        
        # PID有效性验证
        if not isinstance(pid, int) or pid <= 0:
            return None
            
        if not psutil.pid_exists(pid):
            return None
            
        return pid
    except Exception as e:
        logger.error(f"窗口检测异常: {str(e)[:50]} ⚠️")
        return None

def kill_process(proc_name):
    """安全终止进程"""
    logger.info(f"正在终止进程: {proc_name} 💀")
    killed = 0
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'].lower() == proc_name.lower():
                p = psutil.Process(proc.info['pid'])
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
    """智能监控循环"""
    last_trigger = 0
    cooldown = 60
    error_count = 0
    MAX_RETRY_DELAY = 300  # 最大重试延迟5分钟

    logger.info("监控程序已启动 🛡️")
    while True:
        try:
            fg_pid = get_foreground_pid()
            
            # 动态调整检测间隔
            if fg_pid is None:
                sleep_time = 30 if smart_logger.last_window_state is False else 5
                time.sleep(sleep_time)
                continue

            try:
                proc = psutil.Process(fg_pid)
                proc_name = proc.name()
                
                if proc.status() == psutil.STATUS_ZOMBIE:
                    logger.warning(f"检测到僵尸进程: {proc_name}")
                    continue
                    
                if proc_name == 'crashpad_handler.exe':
                    current_time = time.time()
                    if current_time - last_trigger > cooldown:
                        logger.warning("检测到crashpad_handler进入前台! 🔍")
                        
                        killed_crashpad = kill_process('crashpad_handler.exe')
                        killed_qq = kill_process('qq.exe')
                        
                        if start_qq():
                            logger.success(f"操作完成: 终止{killed_crashpad}个crashpad进程和{killed_qq}个QQ进程 🔄")
                        else:
                            logger.error("QQ重启失败，请检查快捷方式路径! 🚧")
                        
                        last_trigger = current_time
                    else:
                        remain = cooldown - int(current_time - last_trigger)
                        logger.info(f"冷却时间剩余: {remain}秒 ⏳")
            
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.warning(f"进程状态异常: {e} ⚠️")
            
            error_count = 0
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
