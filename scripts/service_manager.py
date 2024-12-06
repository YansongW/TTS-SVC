import os
import time
import yaml
import logging
import subprocess
from typing import List, Dict, Any
import requests
import psutil

logger = logging.getLogger(__name__)

class ServiceDependencyManager:
    def __init__(self, config_file: str = 'config/monitor.yml'):
        self.config = self._load_config(config_file)
        self.services = self.config['services']
        self.dependency_graph = self._build_dependency_graph()
        
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_file) as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {str(e)}")
            raise
            
    def _build_dependency_graph(self) -> Dict[str, List[str]]:
        """构建服务依赖图"""
        graph = {}
        for service, config in self.services.items():
            graph[service] = config.get('dependencies', [])
        return graph
        
    def get_startup_order(self) -> List[str]:
        """获取服务启动顺序"""
        visited = set()
        temp = set()
        order = []
        
        def visit(service):
            if service in temp:
                raise ValueError(f"Circular dependency detected: {service}")
            if service in visited:
                return
                
            temp.add(service)
            for dep in self.dependency_graph[service]:
                visit(dep)
            temp.remove(service)
            visited.add(service)
            order.append(service)
            
        for service in self.services:
            if service not in visited:
                visit(service)
                
        return order
        
    def check_service_health(self, service: str) -> bool:
        """检查服务健康状态"""
        config = self.services[service]
        health_check = config.get('health_check', {})
        retries = health_check.get('retries', 3)
        timeout = health_check.get('timeout', 5)
        
        for _ in range(retries):
            try:
                if 'port' in config:
                    # 检查端口
                    for conn in psutil.net_connections():
                        if conn.laddr.port == config['port']:
                            return True
                elif 'process' in config:
                    # 检查进程
                    for proc in psutil.process_iter(['name', 'cmdline']):
                        if config['process'] in str(proc.info['cmdline']):
                            return True
                elif 'url' in config:
                    # 检查HTTP服务
                    response = requests.get(config['url'], timeout=timeout)
                    if response.status_code == 200:
                        return True
                        
                time.sleep(1)
            except Exception as e:
                logger.warning(f"Health check failed for {service}: {str(e)}")
                
        return False
        
    def start_service(self, service: str) -> bool:
        """启动服务"""
        config = self.services[service]
        startup_timeout = config.get('startup_timeout', 30)
        
        try:
            if service == 'redis':
                subprocess.run(['redis-server'], check=True)
            elif service == 'celery':
                subprocess.Popen([
                    'celery', '-A', 'app.celery', 'worker',
                    '--loglevel=info', '--pool=solo'
                ])
            elif service == 'flask':
                subprocess.Popen(['python', 'run.py'])
                
            # 等待服务启动
            start_time = time.time()
            while time.time() - start_time < startup_timeout:
                if self.check_service_health(service):
                    logger.info(f"Service {service} started successfully")
                    return True
                time.sleep(1)
                
            logger.error(f"Service {service} failed to start within {startup_timeout} seconds")
            return False
            
        except Exception as e:
            logger.error(f"Failed to start {service}: {str(e)}")
            return False
            
    def stop_service(self, service: str) -> bool:
        """停止服务"""
        try:
            if service == 'redis':
                subprocess.run(['redis-cli', 'shutdown'], check=True)
            else:
                # 查找并终止进程
                for proc in psutil.process_iter(['name', 'cmdline']):
                    cmdline = str(proc.info['cmdline'])
                    if (service == 'celery' and 'celery worker' in cmdline) or \
                       (service == 'flask' and 'python run.py' in cmdline):
                        proc.terminate()
                        proc.wait(timeout=5)
                        
            logger.info(f"Service {service} stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop {service}: {str(e)}")
            return False
            
    def restart_service(self, service: str) -> bool:
        """重启服务"""
        logger.info(f"Restarting service: {service}")
        
        # 停止依赖此服务的其他服务
        dependent_services = []
        for s, deps in self.dependency_graph.items():
            if service in deps:
                dependent_services.append(s)
                if not self.stop_service(s):
                    logger.error(f"Failed to stop dependent service: {s}")
                    return False
                    
        # 停止目标服务
        if not self.stop_service(service):
            return False
            
        # 启动目标服务
        if not self.start_service(service):
            return False
            
        # 启动依赖服务
        for s in dependent_services:
            if not self.start_service(s):
                logger.error(f"Failed to restart dependent service: {s}")
                return False
                
        return True

def main():
    """测试服务管理功能"""
    manager = ServiceDependencyManager()
    
    # 获取启动顺序
    try:
        startup_order = manager.get_startup_order()
        logger.info(f"Service startup order: {startup_order}")
        
        # 按���序启动服务
        for service in startup_order:
            if not manager.start_service(service):
                logger.error(f"Failed to start {service}")
                break
                
    except Exception as e:
        logger.error(f"Service management failed: {str(e)}")

if __name__ == '__main__':
    main() 