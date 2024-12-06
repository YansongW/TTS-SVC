import psutil
import logging
import signal
import time
from typing import List, Dict, Optional, Tuple
import platform
import subprocess
from typing import Optional
import yaml
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def find_process_by_name(name: str) -> List[psutil.Process]:
    """查找进程"""
    processes = []
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if name.lower() in str(proc.info['cmdline']).lower():
                processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return processes

def get_windows_process_priority(priority_class: str) -> Optional[int]:
    """获取Windows进程优先级"""
    priority_map = {
        'realtime': subprocess.HIGH_PRIORITY_CLASS,
        'high': subprocess.ABOVE_NORMAL_PRIORITY_CLASS,
        'normal': subprocess.NORMAL_PRIORITY_CLASS,
        'low': subprocess.BELOW_NORMAL_PRIORITY_CLASS,
        'idle': subprocess.IDLE_PRIORITY_CLASS
    }
    return priority_map.get(priority_class.lower())

def set_process_priority(proc: psutil.Process, priority: str) -> bool:
    """设置进程优先级"""
    try:
        if platform.system() == 'Windows':
            priority_value = get_windows_process_priority(priority)
            if priority_value is not None:
                proc.nice(priority_value)
        else:
            # Unix系统使用nice值(-20到19)
            nice_map = {
                'realtime': -20,
                'high': -10,
                'normal': 0,
                'low': 10,
                'idle': 19
            }
            nice_value = nice_map.get(priority.lower(), 0)
            proc.nice(nice_value)
        return True
    except Exception as e:
        logger.error(f"Failed to set process priority: {str(e)}")
        return False

def kill_process_windows(proc: psutil.Process, timeout: int = 5) -> bool:
    """Windows特定的进程终止"""
    try:
        # 使用taskkill强制终止进程树
        subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to kill Windows process {proc.pid}: {str(e)}")
        return False

def kill_process(proc: psutil.Process, timeout: int = 5) -> bool:
    """终止进程"""
    try:
        if platform.system() == 'Windows':
            return kill_process_windows(proc, timeout)
            
        # Unix系统的进程终止
        proc.terminate()
        try:
            proc.wait(timeout=timeout)
            return True
        except psutil.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=timeout)
            return True
    except psutil.NoSuchProcess:
        return True
    except Exception as e:
        logger.error(f"Failed to kill process {proc.pid}: {str(e)}")
        return False

def cleanup_processes(names: List[str]) -> bool:
    """清理进程"""
    success = True
    for name in names:
        processes = find_process_by_name(name)
        for proc in processes:
            if not kill_process(proc):
                success = False
    return success 

def set_cpu_affinity(proc: psutil.Process, cpu_cores: List[int]) -> bool:
    """设置CPU亲和性"""
    try:
        proc.cpu_affinity(cpu_cores)
        return True
    except Exception as e:
        logger.error(f"Failed to set CPU affinity for process {proc.pid}: {str(e)}")
        return False

def set_memory_limit(proc: psutil.Process, max_memory_mb: int) -> bool:
    """设置内存限制"""
    try:
        if platform.system() == 'Windows':
            import win32job
            import win32api
            
            # 创建作业对象
            job = win32job.CreateJobObject(None, f"MemoryLimit_{proc.pid}")
            
            # 设置内存限制
            info = win32job.QueryInformationJobObject(
                job, win32job.JobObjectExtendedLimitInformation
            )
            info['ProcessMemoryLimit'] = max_memory_mb * 1024 * 1024
            win32job.SetInformationJobObject(
                job, win32job.JobObjectExtendedLimitInformation, info
            )
            
            # 将进程添加到作业对象
            handle = win32api.OpenProcess(
                win32job.PROCESS_TERMINATE | win32job.PROCESS_SET_QUOTA,
                False, proc.pid
            )
            win32job.AssignProcessToJobObject(job, handle)
        else:
            # Unix系统使用资源限制
            import resource
            resource.setrlimit(
                resource.RLIMIT_AS,
                (max_memory_mb * 1024 * 1024, max_memory_mb * 1024 * 1024)
            )
        return True
    except Exception as e:
        logger.error(f"Failed to set memory limit for process {proc.pid}: {str(e)}")
        return False

def monitor_process_resources(proc: psutil.Process) -> Dict[str, float]:
    """监控进程资源使用"""
    try:
        return {
            'cpu_percent': proc.cpu_percent(interval=1),
            'memory_percent': proc.memory_percent(),
            'memory_mb': proc.memory_info().rss / 1024 / 1024,
            'threads': proc.num_threads(),
            'open_files': len(proc.open_files()),
            'connections': len(proc.connections())
        }
    except Exception as e:
        logger.error(f"Failed to monitor process {proc.pid}: {str(e)}")
        return {}

class ProcessStatus:
    """进程状态类"""
    def __init__(self, pid: int):
        self.pid = pid
        self.start_time = datetime.now()
        self.restart_count = 0
        self.last_restart = None
        self.last_error = None
        
    def record_restart(self, error: Optional[str] = None) -> None:
        """记录重启"""
        self.restart_count += 1
        self.last_restart = datetime.now()
        self.last_error = error

class ProcessHealthCheck:
    """进程健康检查"""
    def __init__(self, proc: psutil.Process, config: Dict):
        self.proc = proc
        self.config = config
        self.last_check = datetime.now()
        
    def check_memory(self) -> Tuple[bool, Optional[str]]:
        """检查内存使用"""
        try:
            memory_mb = self.proc.memory_info().rss / 1024 / 1024
            limit = self.config.get('memory_max', float('inf'))
            if memory_mb > limit:
                return False, f"Memory usage {memory_mb:.1f}MB exceeds limit {limit}MB"
            return True, None
        except Exception as e:
            return False, str(e)
            
    def check_cpu(self) -> Tuple[bool, Optional[str]]:
        """检查CPU使用"""
        try:
            cpu_percent = self.proc.cpu_percent(interval=1)
            limit = self.config.get('cpu_max', 100)
            if cpu_percent > limit:
                return False, f"CPU usage {cpu_percent:.1f}% exceeds limit {limit}%"
            return True, None
        except Exception as e:
            return False, str(e)
            
    def check_responsiveness(self) -> Tuple[bool, Optional[str]]:
        """检查进程响应性"""
        try:
            if not self.proc.is_running():
                return False, "Process is not running"
            if self.proc.status() == psutil.STATUS_ZOMBIE:
                return False, "Process is zombie"
            return True, None
        except Exception as e:
            return False, str(e)
            
    def run_health_check(self) -> Tuple[bool, Optional[str]]:
        """运行健康检查"""
        checks = [
            self.check_memory,
            self.check_cpu,
            self.check_responsiveness
        ]
        
        for check in checks:
            ok, error = check()
            if not ok:
                return False, error
                
        self.last_check = datetime.now()
        return True, None

class ProcessManager:
    """进程管理器"""
    def __init__(self, config_file: str = 'config/monitor.yml'):
        self.config = self._load_config(config_file)
        self.process_status: Dict[str, ProcessStatus] = {}
        self.health_checks: Dict[int, ProcessHealthCheck] = {}
        
    def _load_config(self, config_file: str) -> Dict:
        with open(config_file) as f:
            return yaml.safe_load(f)
            
    def start_process(self, service_name: str, cmd: List[str], 
                     timeout: int = 30) -> Optional[psutil.Process]:
        """启动进程"""
        try:
            start_time = datetime.now()
            proc = psutil.Popen(cmd)
            
            # 等待进程启动
            while (datetime.now() - start_time).total_seconds() < timeout:
                if proc.poll() is not None:
                    raise RuntimeError(f"Process exited with code {proc.returncode}")
                    
                if self.check_process_ready(proc):
                    # 记录进程状态
                    self.process_status[service_name] = ProcessStatus(proc.pid)
                    # 创建健康检查
                    self.health_checks[proc.pid] = ProcessHealthCheck(
                        psutil.Process(proc.pid),
                        self.config['process_limits'].get(service_name, {})
                    )
                    return psutil.Process(proc.pid)
                    
                time.sleep(1)
                
            raise TimeoutError(f"Process startup timeout after {timeout}s")
            
        except Exception as e:
            logger.error(f"Failed to start {service_name}: {str(e)}")
            return None
            
    def check_process_ready(self, proc: psutil.Process) -> bool:
        """检查进程是否就绪"""
        try:
            return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
        except Exception:
            return False
            
    def restart_process(self, service_name: str, proc: psutil.Process,
                       error: Optional[str] = None) -> Optional[psutil.Process]:
        """重启进程"""
        try:
            # 记录重启
            if service_name in self.process_status:
                self.process_status[service_name].record_restart(error)
                
            # 检查重启策略
            if not self._check_restart_policy(service_name):
                logger.error(f"Exceeded max restarts for {service_name}")
                return None
                
            # 终止旧进程
            kill_process(proc)
            
            # 启动新进程
            cmd = self._get_service_command(service_name)
            if not cmd:
                raise ValueError(f"No command configured for {service_name}")
                
            return self.start_process(service_name, cmd)
            
        except Exception as e:
            logger.error(f"Failed to restart {service_name}: {str(e)}")
            return None
            
    def _check_restart_policy(self, service_name: str) -> bool:
        """检查重启策略"""
        if service_name not in self.process_status:
            return True
            
        status = self.process_status[service_name]
        policy = self.config.get('restart_policy', {})
        
        # 检查最大重启次数
        max_restarts = policy.get('max_restarts', 3)
        if status.restart_count >= max_restarts:
            return False
            
        # 检查重启时间间隔
        if status.last_restart:
            min_interval = policy.get('min_interval', 60)
            if (datetime.now() - status.last_restart).total_seconds() < min_interval:
                return False
                
        return True
        
    def _get_service_command(self, service_name: str) -> Optional[List[str]]:
        """获取服务启动命令"""
        commands = {
            'flask': ['python', 'run.py'],
            'celery': ['celery', '-A', 'app.celery', 'worker', '--loglevel=info'],
            'redis': ['redis-server']
        }
        return commands.get(service_name)
            
    def setup_process(self, proc: psutil.Process, service_name: str) -> bool:
        """配置进程资源限制和优先级"""
        try:
            # 设置优先级
            priority = self.config['process_priority'].get(service_name, 'normal')
            if not set_process_priority(proc, priority):
                return False
                
            # 设置CPU亲和性
            if service_name in self.config['process_limits']:
                cpu_cores = self.config['process_limits'][service_name].get('cpu_affinity', [])
                if cpu_cores and not set_cpu_affinity(proc, cpu_cores):
                    return False
                    
                # 设置内存限制
                memory_max = self.config['process_limits'][service_name].get('memory_max')
                if memory_max and not set_memory_limit(proc, memory_max):
                    return False
                    
            return True
        except Exception as e:
            logger.error(f"Failed to setup process {proc.pid}: {str(e)}")
            return False
            
    def monitor_service(self, service_name: str) -> Dict:
        """监控服务状态"""
        processes = find_process_by_name(service_name)
        service_stats = {
            'process_count': len(processes),
            'total_cpu': 0,
            'total_memory': 0,
            'processes': []
        }
        
        for proc in processes:
            stats = monitor_process_resources(proc)
            service_stats['total_cpu'] += stats.get('cpu_percent', 0)
            service_stats['total_memory'] += stats.get('memory_mb', 0)
            service_stats['processes'].append({
                'pid': proc.pid,
                'stats': stats
            })
            
        return service_stats