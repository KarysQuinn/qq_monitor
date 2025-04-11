import os
import time
import psutil
import ctypes
import win32gui
import win32process
from subprocess import Popen


def is_admin():
    """检查是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def elevate_privileges():
    """提升权限为管理员"""
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", "python", f'"{__file__}"', None, 1)


def get_foreground_pid():
    """获取前台窗口的进程ID"""
    hwnd = win32gui.GetForegroundWindow()
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    return pid


def kill_process(proc_name):
    """终止指定名称的所有进程"""
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == proc_name:
            try:
                psutil.Process(proc.info['pid']).terminate()
                print(f"已终止进程: {proc_name}")
            except Exception as e:
                print(f"终止进程失败: {e}")


def start_qq():
    """启动QQ程序"""
    qq_path = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\腾讯软件\QQ\QQ.lnk"
    try:
        Popen(['explorer', qq_path])  # 使用explorer打开快捷方式
        print("QQ已启动")
    except Exception as e:
        print(f"启动QQ失败: {e}")


def main_loop():
    """主监控循环"""
    last_trigger = 0  # 上次触发时间
    cooldown = 60    # 冷却时间（秒）

    while True:
        try:
            # 检查前台窗口是否属于crashpad_handler.exe
            fg_pid = get_foreground_pid()
            if fg_pid:
                proc = psutil.Process(fg_pid)
                if proc.name() == 'crashpad_handler.exe':
                    # 冷却时间检查（避免重复触发）
                    if time.time() - last_trigger > cooldown:
                        print("检测到crashpad_handler前台窗口")
                        kill_process('crashpad_handler.exe')
                        kill_process('qq.exe')
                        start_qq()
                        last_trigger = time.time()
        except Exception as e:
            print(f"监控出错: {e}")

        time.sleep(5)  # 每5秒检查一次


if __name__ == "__main__":
    if not is_admin():
        elevate_privileges()
    else:
        print("正在启动监控程序...")
        main_loop()
