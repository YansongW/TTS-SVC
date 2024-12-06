import os
import glob
import shutil
from datetime import datetime, timedelta
import logging
from config import LOG_DIR
import gzip
import tarfile
import json
from collections import defaultdict
import re

# 配置日志分析参数
LOG_PATTERNS = {
    'error': r'\[ERROR\]|\bERROR\b|Exception|Error:|Failed',
    'warning': r'\[WARN\]|\bWARN\b|Warning:|warning',
    'info': r'\[INFO\]|\bINFO\b',
    'debug': r'\[DEBUG\]|\bDEBUG\b'
}

def analyze_logs():
    """分析日志文件"""
    try:
        stats = defaultdict(lambda: {
            'count': 0,
            'examples': [],
            'last_seen': None
        })
        
        total_stats = {
            'total_lines': 0,
            'errors': 0,
            'warnings': 0,
            'start_time': None,
            'end_time': None
        }
        
        # 分析所有日志文件
        for log_file in glob.glob(os.path.join(LOG_DIR, '*.log')):
            with open(log_file, encoding='utf-8', errors='ignore') as f:
                for line in f:
                    total_stats['total_lines'] += 1
                    
                    # 提取时间戳
                    timestamp_match = re.search(r'\[([\d\-\: ]+)\]', line)
                    if timestamp_match:
                        timestamp = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')
                        if not total_stats['start_time'] or timestamp < total_stats['start_time']:
                            total_stats['start_time'] = timestamp
                        if not total_stats['end_time'] or timestamp > total_stats['end_time']:
                            total_stats['end_time'] = timestamp
                    
                    # 匹配日志级别
                    for level, pattern in LOG_PATTERNS.items():
                        if re.search(pattern, line):
                            stats[level]['count'] += 1
                            if level == 'error':
                                total_stats['errors'] += 1
                            elif level == 'warning':
                                total_stats['warnings'] += 1
                            
                            # 保存示例
                            if len(stats[level]['examples']) < 5:
                                stats[level]['examples'].append(line.strip())
                            stats[level]['last_seen'] = timestamp
                            break
        
        # 生成分析报告
        report_file = os.path.join(LOG_DIR, 'log_analysis.txt')
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"Log Analysis Report\n")
            f.write("=" * 50 + "\n\n")
            
            f.write("Summary\n")
            f.write("-" * 20 + "\n")
            f.write(f"Analysis period: {total_stats['start_time']} to {total_stats['end_time']}\n")
            f.write(f"Total lines processed: {total_stats['total_lines']}\n")
            f.write(f"Total errors: {total_stats['errors']}\n")
            f.write(f"Total warnings: {total_stats['warnings']}\n\n")
            
            for level in ['error', 'warning', 'info', 'debug']:
                if stats[level]['count'] > 0:
                    f.write(f"\n{level.upper()} Details\n")
                    f.write("-" * 20 + "\n")
                    f.write(f"Count: {stats[level]['count']}\n")
                    f.write(f"Last seen: {stats[level]['last_seen']}\n")
                    if stats[level]['examples']:
                        f.write("Recent examples:\n")
                        for example in stats[level]['examples']:
                            f.write(f"  - {example}\n")
                    f.write("\n")
        
        # 保存JSON格式的详细统计
        json_file = os.path.join(LOG_DIR, 'log_stats.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'total_stats': {k: str(v) if isinstance(v, datetime) else v 
                              for k, v in total_stats.items()},
                'level_stats': {k: {
                    'count': v['count'],
                    'last_seen': str(v['last_seen']) if v['last_seen'] else None
                } for k, v in stats.items()}
            }, f, indent=2)
            
        return total_stats
        
    except Exception as e:
        logging.error(f"Failed to analyze logs: {str(e)}")
        return None

def compress_log(log_file):
    """压缩日志文件"""
    try:
        with open(log_file, 'rb') as f_in:
            with gzip.open(f"{log_file}.gz", 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(log_file)
        return True
    except Exception as e:
        logging.error(f"Failed to compress log file {log_file}: {str(e)}")
        return False

def create_backup_archive():
    """创建日志备份归档"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d')
        archive_name = os.path.join(LOG_DIR, f'logs_backup_{timestamp}.tar.gz')
        
        with tarfile.open(archive_name, 'w:gz') as tar:
            for log_file in glob.glob(os.path.join(LOG_DIR, '*.log.*')):
                tar.add(log_file, arcname=os.path.basename(log_file))
        
        return archive_name
    except Exception as e:
        logging.error(f"Failed to create backup archive: {str(e)}")
        return None

def rotate_logs():
    """轮转日志文件"""
    try:
        # 分析当前日志
        stats = analyze_logs()
        if not stats:
            logging.error("Log analysis failed")
        
        # 获取所有日志文件
        log_files = glob.glob(os.path.join(LOG_DIR, '*.log'))
        
        for log_file in log_files:
            try:
                # 检查文件大小
                size = os.path.getsize(log_file)
                if size > 10 * 1024 * 1024:  # 10MB
                    # 创建备份文件名
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_name = f"{log_file}.{timestamp}"
                    
                    # 移动并压缩日志文件
                    shutil.move(log_file, backup_name)
                    if not compress_log(backup_name):
                        logging.error(f"Failed to compress {backup_name}")
                        continue
                    
                    # 创建新的日志文件
                    open(log_file, 'a').close()
                    os.chmod(log_file, 0o644)  # 设置适当的权限
                    
            except Exception as e:
                logging.error(f"Failed to rotate {log_file}: {str(e)}")
                continue
        
        # 清理旧日志
        try:
            # 删除30天前的日志文件
            cutoff = datetime.now() - timedelta(days=30)
            old_logs = []
            for backup_file in glob.glob(os.path.join(LOG_DIR, '*.log.*')):
                try:
                    timestamp = datetime.strptime(backup_file.split('.')[-2], '%Y%m%d_%H%M%S')
                    if timestamp < cutoff:
                        old_logs.append(backup_file)
                except:
                    continue
            
            # 如果有旧日志，创建备份后删除
            if old_logs:
                archive_name = create_backup_archive()
                if archive_name:
                    for log in old_logs:
                        try:
                            os.remove(log)
                            logging.info(f"Removed old log: {log}")
                        except Exception as e:
                            logging.error(f"Failed to remove {log}: {str(e)}")
                else:
                    logging.error("Failed to create backup archive, keeping old logs")
                    
        except Exception as e:
            logging.error(f"Failed to clean up old logs: {str(e)}")
            
    except Exception as e:
        logging.error(f"Log rotation failed: {str(e)}")

if __name__ == '__main__':
    try:
        rotate_logs()
    except Exception as e:
        logging.error(f"Script execution failed: {str(e)}")
        exit(1) 