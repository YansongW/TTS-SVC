import os
import psutil
import logging
import time
from datetime import datetime, timedelta
import requests
from config import LOG_DIR, DATA_DIR
import subprocess
import json
import yaml

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'monitor.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 添加监控配置
DEFAULT_CONFIG = {
    'intervals': {
        'check': 60,  # 检查间隔(秒)
        'cleanup': 86400  # 清理间隔(秒)
    },
    'thresholds': {
        'cpu': 90,
        'memory': 90,
        'disk': 90
    },
    'retry': {
        'max_attempts': 3,
        'delay': 60
    },
    'data_retention': {
        'days': 30
    }
}

def load_config():
    """加载监控配置"""
    config_file = os.path.join('config', 'monitor.yml')
    try:
        if os.path.exists(config_file):
            with open(config_file) as f:
                config = yaml.safe_load(f)
            return {**DEFAULT_CONFIG, **config}
    except Exception as e:
        logger.error(f"Failed to load config: {str(e)}")
    return DEFAULT_CONFIG

class ServiceManager:
    def __init__(self):
        self.restart_script = os.path.join('scripts', 'restart.sh')
        
    def restart_service(self, service_name):
        """重启指定服务"""
        try:
            logger.info(f"Attempting to restart {service_name}...")
            subprocess.run([self.restart_script], check=True)
            logger.info(f"Successfully restarted {service_name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to restart {service_name}: {str(e)}")
            return False

class AlertManager:
    def __init__(self):
        self.alert_log = os.path.join(LOG_DIR, 'alerts.log')
        self.alert_history = {}
        
    def should_alert(self, alert_type, threshold_minutes=30):
        """检查是否应该发送告警"""
        now = datetime.now()
        if alert_type in self.alert_history:
            last_alert = self.alert_history[alert_type]
            if (now - last_alert).total_seconds() < threshold_minutes * 60:
                return False
        self.alert_history[alert_type] = now
        return True
        
    def send_alert(self, message, level='warning'):
        """发送告警"""
        try:
            # 记录告警
            with open(self.alert_log, 'a') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"[{timestamp}] [{level.upper()}] {message}\n")
            
            # 这里可以添加其他告警方式，如邮件、短信等
            logger.warning(f"Alert: {message}")
            
        except Exception as e:
            logger.error(f"Failed to send alert: {str(e)}")

class DataManager:
    def __init__(self, retention_days):
        self.stats_file = os.path.join(DATA_DIR, 'system_stats.json')
        self.retention_days = retention_days
        
    def save_stats(self, stats):
        """保存监控数据"""
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'stats': stats
            }
            with open(self.stats_file, 'a') as f:
                json.dump(data, f)
                f.write('\n')
        except Exception as e:
            logger.error(f"Failed to save stats: {str(e)}")
            
    def cleanup_old_data(self):
        """清理旧数据"""
        try:
            if not os.path.exists(self.stats_file):
                return
                
            cutoff = datetime.now() - timedelta(days=self.retention_days)
            temp_file = f"{self.stats_file}.tmp"
            
            with open(self.stats_file) as f_in:
                with open(temp_file, 'w') as f_out:
                    for line in f_in:
                        try:
                            data = json.loads(line)
                            timestamp = datetime.fromisoformat(data['timestamp'])
                            if timestamp >= cutoff:
                                f_out.write(line)
                        except:
                            continue
                            
            os.replace(temp_file, self.stats_file)
            logger.info("Cleaned up old monitoring data")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {str(e)}")

class SystemMonitor:
    def __init__(self):
        self.config = load_config()
        self.services = {
            'flask': {'port': 5000, 'url': 'http://localhost:5000/'},
            'redis': {'port': 6379},
            'celery': {'process': 'celery'}
        }
        self.service_manager = ServiceManager()
        self.alert_manager = AlertManager()
        self.data_manager = DataManager(self.config['data_retention']['days'])
        
    def get_system_stats(self):
        """获取系统状态"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent
        }
        
    def check_port(self, port):
        """检查端口是否在使用"""
        for conn in psutil.net_connections():
            if conn.laddr.port == port:
                return True
        return False
        
    def check_process(self, name):
        """检查进程是否运行"""
        for proc in psutil.process_iter(['name', 'cmdline']):
            if name in str(proc.info['cmdline']):
                return True
        return False
        
    def check_web_service(self, url):
        """检查Web服务是否响应"""
        try:
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False
            
    def check_services(self):
        """检查所有服务状态"""
        status = {}
        
        for service, config in self.services.items():
            if 'port' in config:
                status[service] = self.check_port(config['port'])
            if 'process' in config:
                status[service] = self.check_process(config['process'])
            if 'url' in config:
                status[service] = self.check_web_service(config['url'])
                
        return status
        
    def monitor(self):
        """运行监控"""
        consecutive_failures = {service: 0 for service in self.services}
        last_cleanup = datetime.now()
        
        while True:
            try:
                # 检查是否需要清理数据
                now = datetime.now()
                if (now - last_cleanup).total_seconds() >= self.config['intervals']['cleanup']:
                    self.data_manager.cleanup_old_data()
                    last_cleanup = now
                
                # 检查系统状态
                stats = self.get_system_stats()
                self.data_manager.save_stats(stats)
                logger.info(f"System stats: {stats}")
                
                # 检查资源使用
                thresholds = self.config['thresholds']
                if stats['cpu_percent'] > thresholds['cpu']:
                    self.alert_manager.send_alert("High CPU usage!", 'critical')
                
                if stats['memory_percent'] > thresholds['memory']:
                    self.alert_manager.send_alert("High memory usage!", 'critical')
                
                if stats['disk_percent'] > thresholds['disk']:
                    self.alert_manager.send_alert("Low disk space!", 'critical')
                
                # 检查服务状态
                service_status = self.check_services()
                logger.info(f"Service status: {service_status}")
                
                # 处理服务故障
                retry_config = self.config['retry']
                for service, running in service_status.items():
                    if not running:
                        consecutive_failures[service] += 1
                        if consecutive_failures[service] >= retry_config['max_attempts']:
                            if self.alert_manager.should_alert(f'{service}_down'):
                                self.alert_manager.send_alert(
                                    f"Service {service} is down! Attempting restart...",
                                    'critical'
                                )
                            if self.service_manager.restart_service(service):
                                consecutive_failures[service] = 0
                    else:
                        consecutive_failures[service] = 0
                
                time.sleep(self.config['intervals']['check'])
                
            except Exception as e:
                logger.error(f"Monitoring error: {str(e)}")
                time.sleep(self.config['intervals']['check'])

if __name__ == '__main__':
    monitor = SystemMonitor()
    monitor.monitor() 