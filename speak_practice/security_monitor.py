"""
安全监控和告警系统 (Security Monitoring and Alerting System)
实时监控安全事件并提供告警功能
"""

import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from django.core.cache import cache
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from collections import defaultdict, deque
import threading
import requests

logger = logging.getLogger(__name__)


class SecurityEventMonitor:
    """
    安全事件监控器 (Security Event Monitor)
    收集、分析和报告安全事件
    """
    
    # 事件类型定义 (Event type definitions)
    EVENT_TYPES = {
        'rate_limit_violation': {'severity': 'medium', 'threshold': 5},
        'malicious_input_detected': {'severity': 'high', 'threshold': 3},
        'malicious_audio_upload': {'severity': 'high', 'threshold': 2},
        'authentication_failure': {'severity': 'medium', 'threshold': 10},
        'suspicious_activity': {'severity': 'medium', 'threshold': 5},
        'api_abuse': {'severity': 'high', 'threshold': 3},
        'security_violation': {'severity': 'high', 'threshold': 1}
    }
    
    def __init__(self):
        self.event_buffer = defaultdict(lambda: deque(maxlen=1000))
        self.alert_cooldown = {}  # 防止告警风暴
        self.lock = threading.Lock()
    
    def record_event(self, event_type: str, user_id: Optional[int], ip_address: str, 
                    details: Dict[str, Any], request_path: str = None):
        """
        记录安全事件 (Record security event)
        
        Args:
            event_type: 事件类型
            user_id: 用户ID
            ip_address: IP地址
            details: 事件详情
            request_path: 请求路径
        """
        timestamp = timezone.now()
        
        event_data = {
            'timestamp': timestamp.isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'ip_address': ip_address,
            'request_path': request_path,
            'details': details,
            'severity': self.EVENT_TYPES.get(event_type, {}).get('severity', 'low')
        }
        
        with self.lock:
            # 添加到事件缓冲区 (Add to event buffer)
            self.event_buffer[event_type].append(event_data)
            
            # 检查是否需要触发告警 (Check if alert should be triggered)
            self._check_alert_conditions(event_type, event_data)
        
        # 记录到日志 (Log to file)
        logger.warning(f"Security Event: {json.dumps(event_data, default=str)}")
    
    def _check_alert_conditions(self, event_type: str, event_data: Dict[str, Any]):
        """
        检查告警条件 (Check alert conditions)
        """
        event_config = self.EVENT_TYPES.get(event_type, {})
        threshold = event_config.get('threshold', 10)
        severity = event_config.get('severity', 'low')
        
        # 获取最近1小时的事件 (Get events from last hour)
        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent_events = [
            event for event in self.event_buffer[event_type]
            if datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')) > one_hour_ago
        ]
        
        # 检查是否超过阈值 (Check if threshold exceeded)
        if len(recent_events) >= threshold:
            alert_key = f"{event_type}_{event_data['ip_address']}"
            
            # 检查告警冷却时间 (Check alert cooldown)
            if self._should_send_alert(alert_key):
                self._send_security_alert(event_type, recent_events, severity)
                self.alert_cooldown[alert_key] = timezone.now()
    
    def _should_send_alert(self, alert_key: str) -> bool:
        """
        检查是否应该发送告警 (Check if alert should be sent)
        """
        last_alert = self.alert_cooldown.get(alert_key)
        if not last_alert:
            return True
        
        # 15分钟冷却时间 (15 minute cooldown)
        cooldown_period = timedelta(minutes=15)
        return timezone.now() - last_alert > cooldown_period
    
    def _send_security_alert(self, event_type: str, events: List[Dict[str, Any]], severity: str):
        """
        发送安全告警 (Send security alert)
        """
        try:
            alert_data = {
                'event_type': event_type,
                'severity': severity,
                'event_count': len(events),
                'time_window': '1 hour',
                'affected_ips': list(set(event['ip_address'] for event in events)),
                'affected_users': list(set(str(event['user_id']) for event in events if event['user_id'])),
                'first_occurrence': events[0]['timestamp'],
                'last_occurrence': events[-1]['timestamp'],
                'sample_details': events[-1]['details']  # 最新事件的详情
            }
            
            # 发送邮件告警 (Send email alert)
            self._send_email_alert(alert_data)
            
            # 发送Webhook告警 (Send webhook alert)
            self._send_webhook_alert(alert_data)
            
            logger.critical(f"Security Alert Sent: {json.dumps(alert_data, default=str)}")
            
        except Exception as e:
            logger.error(f"Failed to send security alert: {str(e)}")
    
    def _send_email_alert(self, alert_data: Dict[str, Any]):
        """
        发送邮件告警 (Send email alert)
        """
        alert_email = getattr(settings, 'SECURITY_ALERT_EMAIL', None)
        if not alert_email:
            return
        
        subject = f"Security Alert: {alert_data['event_type']} ({alert_data['severity']} severity)"
        
        message = f"""
Security Alert Detected

Event Type: {alert_data['event_type']}
Severity: {alert_data['severity']}
Event Count: {alert_data['event_count']} in {alert_data['time_window']}

Affected IPs: {', '.join(alert_data['affected_ips'])}
Affected Users: {', '.join(alert_data['affected_users']) if alert_data['affected_users'] else 'None'}

First Occurrence: {alert_data['first_occurrence']}
Last Occurrence: {alert_data['last_occurrence']}

Sample Event Details:
{json.dumps(alert_data['sample_details'], indent=2)}

Please investigate immediately.
        """
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[alert_email],
                fail_silently=False
            )
        except Exception as e:
            logger.error(f"Failed to send email alert: {str(e)}")
    
    def _send_webhook_alert(self, alert_data: Dict[str, Any]):
        """
        发送Webhook告警 (Send webhook alert)
        """
        webhook_url = getattr(settings, 'SECURITY_ALERT_WEBHOOK', None)
        if not webhook_url:
            return
        
        payload = {
            'alert_type': 'security_event',
            'timestamp': timezone.now().isoformat(),
            'data': alert_data
        }
        
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {str(e)}")
    
    def get_security_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取安全指标 (Get security metrics)
        
        Args:
            hours: 统计时间范围（小时）
            
        Returns:
            Dict: 安全指标数据
        """
        cutoff_time = timezone.now() - timedelta(hours=hours)
        metrics = {
            'time_range': f'Last {hours} hours',
            'total_events': 0,
            'events_by_type': {},
            'events_by_severity': defaultdict(int),
            'top_ips': defaultdict(int),
            'top_users': defaultdict(int),
            'hourly_distribution': defaultdict(int)
        }
        
        with self.lock:
            for event_type, events in self.event_buffer.items():
                recent_events = [
                    event for event in events
                    if datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')) > cutoff_time
                ]
                
                if recent_events:
                    metrics['events_by_type'][event_type] = len(recent_events)
                    metrics['total_events'] += len(recent_events)
                    
                    for event in recent_events:
                        # 按严重程度统计 (Count by severity)
                        metrics['events_by_severity'][event['severity']] += 1
                        
                        # 统计IP地址 (Count IP addresses)
                        metrics['top_ips'][event['ip_address']] += 1
                        
                        # 统计用户 (Count users)
                        if event['user_id']:
                            metrics['top_users'][str(event['user_id'])] += 1
                        
                        # 按小时分布 (Hourly distribution)
                        event_time = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                        hour_key = event_time.strftime('%Y-%m-%d %H:00')
                        metrics['hourly_distribution'][hour_key] += 1
        
        # 转换为列表并排序 (Convert to lists and sort)
        metrics['top_ips'] = sorted(metrics['top_ips'].items(), key=lambda x: x[1], reverse=True)[:10]
        metrics['top_users'] = sorted(metrics['top_users'].items(), key=lambda x: x[1], reverse=True)[:10]
        metrics['events_by_severity'] = dict(metrics['events_by_severity'])
        metrics['hourly_distribution'] = dict(sorted(metrics['hourly_distribution'].items()))
        
        return metrics
    
    def clear_old_events(self, days: int = 7):
        """
        清理旧事件 (Clear old events)
        
        Args:
            days: 保留天数
        """
        cutoff_time = timezone.now() - timedelta(days=days)
        
        with self.lock:
            for event_type in self.event_buffer:
                # 过滤掉旧事件 (Filter out old events)
                recent_events = deque([
                    event for event in self.event_buffer[event_type]
                    if datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')) > cutoff_time
                ], maxlen=1000)
                
                self.event_buffer[event_type] = recent_events
        
        logger.info(f"Cleared security events older than {days} days")


class SecurityDashboard:
    """
    安全仪表板 (Security Dashboard)
    提供安全状态的可视化数据
    """
    
    def __init__(self, monitor: SecurityEventMonitor):
        self.monitor = monitor
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        获取仪表板数据 (Get dashboard data)
        """
        # 获取24小时指标 (Get 24-hour metrics)
        metrics_24h = self.monitor.get_security_metrics(24)
        
        # 获取1小时指标 (Get 1-hour metrics)
        metrics_1h = self.monitor.get_security_metrics(1)
        
        # 计算趋势 (Calculate trends)
        trend_data = self._calculate_trends()
        
        # 获取系统状态 (Get system status)
        system_status = self._get_system_status()
        
        return {
            'current_time': timezone.now().isoformat(),
            'system_status': system_status,
            'metrics_24h': metrics_24h,
            'metrics_1h': metrics_1h,
            'trends': trend_data,
            'alerts': self._get_active_alerts(),
            'recommendations': self._get_security_recommendations()
        }
    
    def _calculate_trends(self) -> Dict[str, Any]:
        """
        计算安全趋势 (Calculate security trends)
        """
        # 比较过去24小时和前24小时的数据
        current_24h = self.monitor.get_security_metrics(24)
        previous_24h = self.monitor.get_security_metrics(48)  # 48小时数据，取前24小时
        
        trends = {}
        for event_type in current_24h['events_by_type']:
            current_count = current_24h['events_by_type'][event_type]
            previous_count = previous_24h['events_by_type'].get(event_type, 0)
            
            if previous_count > 0:
                change_percent = ((current_count - previous_count) / previous_count) * 100
            else:
                change_percent = 100 if current_count > 0 else 0
            
            trends[event_type] = {
                'current': current_count,
                'previous': previous_count,
                'change_percent': round(change_percent, 1),
                'trend': 'up' if change_percent > 0 else 'down' if change_percent < 0 else 'stable'
            }
        
        return trends
    
    def _get_system_status(self) -> Dict[str, Any]:
        """
        获取系统安全状态 (Get system security status)
        """
        metrics_1h = self.monitor.get_security_metrics(1)
        
        # 计算风险级别 (Calculate risk level)
        high_severity_events = metrics_1h['events_by_severity'].get('high', 0)
        medium_severity_events = metrics_1h['events_by_severity'].get('medium', 0)
        
        if high_severity_events > 5:
            risk_level = 'critical'
            status_color = 'red'
        elif high_severity_events > 2 or medium_severity_events > 10:
            risk_level = 'high'
            status_color = 'orange'
        elif medium_severity_events > 5:
            risk_level = 'medium'
            status_color = 'yellow'
        else:
            risk_level = 'low'
            status_color = 'green'
        
        return {
            'risk_level': risk_level,
            'status_color': status_color,
            'total_events_1h': metrics_1h['total_events'],
            'high_severity_events_1h': high_severity_events,
            'medium_severity_events_1h': medium_severity_events,
            'last_updated': timezone.now().isoformat()
        }
    
    def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """
        获取活跃告警 (Get active alerts)
        """
        # 这里可以从数据库或缓存中获取活跃的告警
        # 目前返回模拟数据
        return []
    
    def _get_security_recommendations(self) -> List[str]:
        """
        获取安全建议 (Get security recommendations)
        """
        recommendations = []
        metrics_24h = self.monitor.get_security_metrics(24)
        
        # 基于事件类型提供建议 (Provide recommendations based on event types)
        if metrics_24h['events_by_type'].get('rate_limit_violation', 0) > 50:
            recommendations.append("Consider implementing more aggressive rate limiting")
        
        if metrics_24h['events_by_type'].get('malicious_input_detected', 0) > 10:
            recommendations.append("Review and strengthen input validation rules")
        
        if metrics_24h['events_by_type'].get('malicious_audio_upload', 0) > 5:
            recommendations.append("Enhance audio file security scanning")
        
        if len(metrics_24h['top_ips']) > 0 and metrics_24h['top_ips'][0][1] > 100:
            recommendations.append(f"Investigate suspicious activity from IP: {metrics_24h['top_ips'][0][0]}")
        
        if not recommendations:
            recommendations.append("Security status is normal. Continue monitoring.")
        
        return recommendations


# 全局监控实例 (Global monitor instance)
security_monitor = SecurityEventMonitor()
security_dashboard = SecurityDashboard(security_monitor)


def log_security_event(event_type: str, request, details: Dict[str, Any]):
    """
    记录安全事件的便捷函数 (Convenience function to log security events)
    
    Args:
        event_type: 事件类型
        request: Django请求对象
        details: 事件详情
    """
    from .security import RateLimiter
    
    user_id = request.user.id if request.user.is_authenticated else None
    ip_address = RateLimiter.get_client_ip(request)
    request_path = request.path
    
    security_monitor.record_event(event_type, user_id, ip_address, details, request_path)


# 定期清理任务 (Periodic cleanup task)
def cleanup_old_security_events():
    """
    清理旧的安全事件 (Clean up old security events)
    这个函数应该通过定时任务调用
    """
    try:
        security_monitor.clear_old_events(days=7)
        logger.info("Security event cleanup completed")
    except Exception as e:
        logger.error(f"Security event cleanup failed: {str(e)}")


# 导出函数 (Export functions)
__all__ = [
    'SecurityEventMonitor',
    'SecurityDashboard', 
    'security_monitor',
    'security_dashboard',
    'log_security_event',
    'cleanup_old_security_events'
]