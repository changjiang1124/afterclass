"""
生产环境监控和日志配置 (Production Monitoring and Logging Configuration)
提供应用程序性能监控、错误跟踪和日志分析功能
"""

import os
import logging
import time
import psutil
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.core.cache import cache
from django.utils import timezone


class SystemMonitor:
    """
    系统监控器 (System Monitor)
    监控系统资源使用情况和应用程序性能
    """
    
    def __init__(self):
        self.logger = logging.getLogger('monitoring')
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        获取系统指标 (Get system metrics)
        """
        try:
            # CPU使用率 (CPU usage)
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # 内存使用情况 (Memory usage)
            memory = psutil.virtual_memory()
            
            # 磁盘使用情况 (Disk usage)
            disk = psutil.disk_usage('/')
            
            # 网络统计 (Network statistics)
            network = psutil.net_io_counters()
            
            return {
                'timestamp': timezone.now().isoformat(),
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count,
                    'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used,
                    'free': memory.free
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100
                },
                'network': {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                }
            }
        except Exception as e:
            self.logger.error(f"Failed to get system metrics: {str(e)}")
            return {}
    
    def get_database_metrics(self) -> Dict[str, Any]:
        """
        获取数据库指标 (Get database metrics)
        """
        try:
            with connection.cursor() as cursor:
                # 数据库连接数 (Database connections)
                cursor.execute("SELECT count(*) FROM pg_stat_activity;")
                active_connections = cursor.fetchone()[0]
                
                # 数据库大小 (Database size)
                cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()));")
                db_size = cursor.fetchone()[0]
                
                # 慢查询统计 (Slow query statistics)
                cursor.execute("""
                    SELECT query, calls, total_time, mean_time 
                    FROM pg_stat_statements 
                    ORDER BY total_time DESC 
                    LIMIT 5;
                """)
                slow_queries = cursor.fetchall()
                
                return {
                    'timestamp': timezone.now().isoformat(),
                    'active_connections': active_connections,
                    'database_size': db_size,
                    'slow_queries': [
                        {
                            'query': query[:100] + '...' if len(query) > 100 else query,
                            'calls': calls,
                            'total_time': total_time,
                            'mean_time': mean_time
                        }
                        for query, calls, total_time, mean_time in slow_queries
                    ]
                }
        except Exception as e:
            self.logger.error(f"Failed to get database metrics: {str(e)}")
            return {}
    
    def get_cache_metrics(self) -> Dict[str, Any]:
        """
        获取缓存指标 (Get cache metrics)
        """
        try:
            # Redis统计信息 (Redis statistics)
            cache_stats = cache._cache.get_client().info()
            
            return {
                'timestamp': timezone.now().isoformat(),
                'redis': {
                    'used_memory': cache_stats.get('used_memory', 0),
                    'used_memory_human': cache_stats.get('used_memory_human', '0B'),
                    'connected_clients': cache_stats.get('connected_clients', 0),
                    'total_commands_processed': cache_stats.get('total_commands_processed', 0),
                    'keyspace_hits': cache_stats.get('keyspace_hits', 0),
                    'keyspace_misses': cache_stats.get('keyspace_misses', 0),
                    'hit_rate': (
                        cache_stats.get('keyspace_hits', 0) / 
                        (cache_stats.get('keyspace_hits', 0) + cache_stats.get('keyspace_misses', 1))
                    ) * 100
                }
            }
        except Exception as e:
            self.logger.error(f"Failed to get cache metrics: {str(e)}")
            return {}
    
    def get_application_metrics(self) -> Dict[str, Any]:
        """
        获取应用程序指标 (Get application metrics)
        """
        try:
            from speak_practice.models import ChatSession, ChatMessage
            from django.contrib.auth.models import User
            
            # 用户统计 (User statistics)
            total_users = User.objects.count()
            active_users_24h = User.objects.filter(
                last_login__gte=timezone.now() - timedelta(hours=24)
            ).count()
            
            # 会话统计 (Session statistics)
            total_sessions = ChatSession.objects.count()
            sessions_24h = ChatSession.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).count()
            
            # 消息统计 (Message statistics)
            total_messages = ChatMessage.objects.count()
            messages_24h = ChatMessage.objects.filter(
                timestamp__gte=timezone.now() - timedelta(hours=24)
            ).count()
            
            return {
                'timestamp': timezone.now().isoformat(),
                'users': {
                    'total': total_users,
                    'active_24h': active_users_24h
                },
                'sessions': {
                    'total': total_sessions,
                    'created_24h': sessions_24h
                },
                'messages': {
                    'total': total_messages,
                    'sent_24h': messages_24h
                }
            }
        except Exception as e:
            self.logger.error(f"Failed to get application metrics: {str(e)}")
            return {}
    
    def check_health(self) -> Dict[str, Any]:
        """
        健康检查 (Health check)
        """
        health_status = {
            'timestamp': timezone.now().isoformat(),
            'status': 'healthy',
            'checks': {}
        }
        
        # 数据库健康检查 (Database health check)
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                health_status['checks']['database'] = 'healthy'
        except Exception as e:
            health_status['checks']['database'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        # 缓存健康检查 (Cache health check)
        try:
            cache.set('health_check', 'ok', 10)
            if cache.get('health_check') == 'ok':
                health_status['checks']['cache'] = 'healthy'
            else:
                health_status['checks']['cache'] = 'unhealthy: cache not working'
                health_status['status'] = 'unhealthy'
        except Exception as e:
            health_status['checks']['cache'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        # 磁盘空间检查 (Disk space check)
        try:
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            if disk_usage_percent > 90:
                health_status['checks']['disk'] = f'warning: {disk_usage_percent:.1f}% used'
                if health_status['status'] == 'healthy':
                    health_status['status'] = 'warning'
            else:
                health_status['checks']['disk'] = 'healthy'
        except Exception as e:
            health_status['checks']['disk'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        # 内存使用检查 (Memory usage check)
        try:
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                health_status['checks']['memory'] = f'warning: {memory.percent:.1f}% used'
                if health_status['status'] == 'healthy':
                    health_status['status'] = 'warning'
            else:
                health_status['checks']['memory'] = 'healthy'
        except Exception as e:
            health_status['checks']['memory'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        return health_status


class LogAnalyzer:
    """
    日志分析器 (Log Analyzer)
    分析应用程序日志并提供洞察
    """
    
    def __init__(self, log_file_path: str):
        self.log_file_path = log_file_path
        self.logger = logging.getLogger('log_analyzer')
    
    def analyze_error_patterns(self, hours: int = 24) -> Dict[str, Any]:
        """
        分析错误模式 (Analyze error patterns)
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            error_patterns = {}
            total_errors = 0
            
            with open(self.log_file_path, 'r') as f:
                for line in f:
                    if 'ERROR' in line:
                        # 简单的时间戳解析 (Simple timestamp parsing)
                        try:
                            # 假设日志格式包含时间戳 (Assume log format contains timestamp)
                            if cutoff_time.strftime('%Y-%m-%d') in line:
                                total_errors += 1
                                
                                # 提取错误类型 (Extract error type)
                                if 'Exception' in line:
                                    error_type = line.split('Exception')[0].split()[-1] + 'Exception'
                                    error_patterns[error_type] = error_patterns.get(error_type, 0) + 1
                        except:
                            continue
            
            return {
                'timestamp': timezone.now().isoformat(),
                'time_range': f'Last {hours} hours',
                'total_errors': total_errors,
                'error_patterns': dict(sorted(error_patterns.items(), key=lambda x: x[1], reverse=True))
            }
        except Exception as e:
            self.logger.error(f"Failed to analyze error patterns: {str(e)}")
            return {}
    
    def get_performance_insights(self) -> Dict[str, Any]:
        """
        获取性能洞察 (Get performance insights)
        """
        try:
            slow_requests = []
            api_usage = {}
            
            with open(self.log_file_path, 'r') as f:
                for line in f:
                    # 查找慢请求 (Look for slow requests)
                    if 'slow' in line.lower() or 'timeout' in line.lower():
                        slow_requests.append(line.strip())
                    
                    # API使用统计 (API usage statistics)
                    if '/api/' in line:
                        try:
                            api_endpoint = line.split('/api/')[1].split()[0]
                            api_usage[api_endpoint] = api_usage.get(api_endpoint, 0) + 1
                        except:
                            continue
            
            return {
                'timestamp': timezone.now().isoformat(),
                'slow_requests': slow_requests[-10:],  # 最近10个慢请求
                'api_usage': dict(sorted(api_usage.items(), key=lambda x: x[1], reverse=True)[:10])
            }
        except Exception as e:
            self.logger.error(f"Failed to get performance insights: {str(e)}")
            return {}


class AlertManager:
    """
    告警管理器 (Alert Manager)
    管理系统告警和通知
    """
    
    def __init__(self):
        self.logger = logging.getLogger('alerts')
        self.alert_thresholds = {
            'cpu_usage': 80,
            'memory_usage': 85,
            'disk_usage': 90,
            'error_rate': 10,  # errors per minute
            'response_time': 5000  # milliseconds
        }
    
    def check_system_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        检查系统告警 (Check system alerts)
        """
        alerts = []
        
        # CPU告警 (CPU alerts)
        if metrics.get('cpu', {}).get('percent', 0) > self.alert_thresholds['cpu_usage']:
            alerts.append({
                'type': 'cpu_high',
                'severity': 'warning',
                'message': f"High CPU usage: {metrics['cpu']['percent']:.1f}%",
                'threshold': self.alert_thresholds['cpu_usage'],
                'current_value': metrics['cpu']['percent']
            })
        
        # 内存告警 (Memory alerts)
        if metrics.get('memory', {}).get('percent', 0) > self.alert_thresholds['memory_usage']:
            alerts.append({
                'type': 'memory_high',
                'severity': 'warning',
                'message': f"High memory usage: {metrics['memory']['percent']:.1f}%",
                'threshold': self.alert_thresholds['memory_usage'],
                'current_value': metrics['memory']['percent']
            })
        
        # 磁盘告警 (Disk alerts)
        if metrics.get('disk', {}).get('percent', 0) > self.alert_thresholds['disk_usage']:
            alerts.append({
                'type': 'disk_high',
                'severity': 'critical',
                'message': f"High disk usage: {metrics['disk']['percent']:.1f}%",
                'threshold': self.alert_thresholds['disk_usage'],
                'current_value': metrics['disk']['percent']
            })
        
        return alerts
    
    def send_alert(self, alert: Dict[str, Any]):
        """
        发送告警 (Send alert)
        """
        try:
            # 记录告警 (Log alert)
            self.logger.critical(f"ALERT: {alert['message']}")
            
            # 发送邮件告警 (Send email alert)
            if hasattr(settings, 'ALERT_EMAIL') and settings.ALERT_EMAIL:
                from django.core.mail import send_mail
                
                subject = f"[ALERT] {alert['type'].upper()}: {alert['message']}"
                message = f"""
Alert Details:
Type: {alert['type']}
Severity: {alert['severity']}
Message: {alert['message']}
Threshold: {alert.get('threshold', 'N/A')}
Current Value: {alert.get('current_value', 'N/A')}
Timestamp: {timezone.now().isoformat()}

Please investigate immediately.
                """
                
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.ALERT_EMAIL],
                    fail_silently=False
                )
            
            # 发送Webhook告警 (Send webhook alert)
            if hasattr(settings, 'ALERT_WEBHOOK') and settings.ALERT_WEBHOOK:
                import requests
                
                payload = {
                    'alert_type': alert['type'],
                    'severity': alert['severity'],
                    'message': alert['message'],
                    'timestamp': timezone.now().isoformat(),
                    'details': alert
                }
                
                requests.post(
                    settings.ALERT_WEBHOOK,
                    json=payload,
                    timeout=10
                )
        
        except Exception as e:
            self.logger.error(f"Failed to send alert: {str(e)}")


class MonitoringDashboard:
    """
    监控仪表板 (Monitoring Dashboard)
    提供监控数据的统一视图
    """
    
    def __init__(self):
        self.system_monitor = SystemMonitor()
        self.alert_manager = AlertManager()
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        获取仪表板数据 (Get dashboard data)
        """
        # 获取各种指标 (Get various metrics)
        system_metrics = self.system_monitor.get_system_metrics()
        database_metrics = self.system_monitor.get_database_metrics()
        cache_metrics = self.system_monitor.get_cache_metrics()
        app_metrics = self.system_monitor.get_application_metrics()
        health_status = self.system_monitor.check_health()
        
        # 检查告警 (Check alerts)
        alerts = self.alert_manager.check_system_alerts(system_metrics)
        
        return {
            'timestamp': timezone.now().isoformat(),
            'health_status': health_status,
            'system_metrics': system_metrics,
            'database_metrics': database_metrics,
            'cache_metrics': cache_metrics,
            'application_metrics': app_metrics,
            'alerts': alerts,
            'summary': {
                'status': health_status.get('status', 'unknown'),
                'active_alerts': len(alerts),
                'cpu_usage': system_metrics.get('cpu', {}).get('percent', 0),
                'memory_usage': system_metrics.get('memory', {}).get('percent', 0),
                'disk_usage': system_metrics.get('disk', {}).get('percent', 0)
            }
        }


# 导出类和函数 (Export classes and functions)
__all__ = [
    'SystemMonitor',
    'LogAnalyzer', 
    'AlertManager',
    'MonitoringDashboard'
]