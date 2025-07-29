"""
安全监控管理命令 (Security Monitoring Management Command)
用于管理和监控系统安全状态
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from speak_practice.security_monitor import security_monitor, security_dashboard, cleanup_old_security_events
from speak_practice.security_config import validate_production_security
import json


class Command(BaseCommand):
    help = 'Security monitoring and management commands'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['status', 'metrics', 'cleanup', 'validate', 'dashboard'],
            help='Action to perform'
        )
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Time range in hours for metrics (default: 24)'
        )
        parser.add_argument(
            '--format',
            choices=['json', 'table'],
            default='table',
            help='Output format (default: table)'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        try:
            if action == 'status':
                self.show_security_status(options)
            elif action == 'metrics':
                self.show_security_metrics(options)
            elif action == 'cleanup':
                self.cleanup_events(options)
            elif action == 'validate':
                self.validate_security_config(options)
            elif action == 'dashboard':
                self.show_dashboard(options)
        except Exception as e:
            raise CommandError(f'Command failed: {str(e)}')

    def show_security_status(self, options):
        """显示安全状态 (Show security status)"""
        dashboard_data = security_dashboard.get_dashboard_data()
        system_status = dashboard_data['system_status']
        
        if options['format'] == 'json':
            self.stdout.write(json.dumps(system_status, indent=2))
        else:
            self.stdout.write(self.style.SUCCESS('=== Security Status ==='))
            self.stdout.write(f"Risk Level: {self.get_colored_risk_level(system_status['risk_level'])}")
            self.stdout.write(f"Total Events (1h): {system_status['total_events_1h']}")
            self.stdout.write(f"High Severity Events (1h): {system_status['high_severity_events_1h']}")
            self.stdout.write(f"Medium Severity Events (1h): {system_status['medium_severity_events_1h']}")
            self.stdout.write(f"Last Updated: {system_status['last_updated']}")

    def show_security_metrics(self, options):
        """显示安全指标 (Show security metrics)"""
        hours = options['hours']
        metrics = security_monitor.get_security_metrics(hours)
        
        if options['format'] == 'json':
            self.stdout.write(json.dumps(metrics, indent=2))
        else:
            self.stdout.write(self.style.SUCCESS(f'=== Security Metrics ({metrics["time_range"]}) ==='))
            
            # 总体统计 (Overall statistics)
            self.stdout.write(f"\nTotal Events: {metrics['total_events']}")
            
            # 按类型统计 (By event type)
            if metrics['events_by_type']:
                self.stdout.write("\nEvents by Type:")
                for event_type, count in metrics['events_by_type'].items():
                    self.stdout.write(f"  {event_type}: {count}")
            
            # 按严重程度统计 (By severity)
            if metrics['events_by_severity']:
                self.stdout.write("\nEvents by Severity:")
                for severity, count in metrics['events_by_severity'].items():
                    color_func = self.get_severity_color(severity)
                    self.stdout.write(f"  {color_func(severity)}: {count}")
            
            # 热点IP (Top IPs)
            if metrics['top_ips']:
                self.stdout.write("\nTop IPs:")
                for ip, count in metrics['top_ips'][:5]:
                    self.stdout.write(f"  {ip}: {count}")
            
            # 热点用户 (Top Users)
            if metrics['top_users']:
                self.stdout.write("\nTop Users:")
                for user_id, count in metrics['top_users'][:5]:
                    self.stdout.write(f"  User {user_id}: {count}")

    def cleanup_events(self, options):
        """清理旧事件 (Cleanup old events)"""
        self.stdout.write("Cleaning up old security events...")
        cleanup_old_security_events()
        self.stdout.write(self.style.SUCCESS("Security event cleanup completed"))

    def validate_security_config(self, options):
        """验证安全配置 (Validate security configuration)"""
        validation_result = validate_production_security()
        
        if options['format'] == 'json':
            self.stdout.write(json.dumps(validation_result, indent=2))
        else:
            self.stdout.write(self.style.SUCCESS('=== Security Configuration Validation ==='))
            
            if validation_result['is_secure']:
                self.stdout.write(self.style.SUCCESS("✓ All security checks passed"))
            else:
                self.stdout.write(self.style.WARNING(f"⚠ {validation_result['passed']}/{validation_result['total']} checks passed ({validation_result['percentage']:.1f}%)"))
                
                if validation_result['failed_checks']:
                    self.stdout.write("\nFailed Checks:")
                    for check in validation_result['failed_checks']:
                        self.stdout.write(self.style.ERROR(f"  ✗ {check}"))
            
            self.stdout.write(f"\nSecurity Score: {validation_result['percentage']:.1f}%")

    def show_dashboard(self, options):
        """显示安全仪表板 (Show security dashboard)"""
        dashboard_data = security_dashboard.get_dashboard_data()
        
        if options['format'] == 'json':
            self.stdout.write(json.dumps(dashboard_data, indent=2, default=str))
        else:
            self.stdout.write(self.style.SUCCESS('=== Security Dashboard ==='))
            
            # 系统状态 (System status)
            system_status = dashboard_data['system_status']
            self.stdout.write(f"\nSystem Status: {self.get_colored_risk_level(system_status['risk_level'])}")
            
            # 24小时指标 (24-hour metrics)
            metrics_24h = dashboard_data['metrics_24h']
            self.stdout.write(f"\n24-Hour Summary:")
            self.stdout.write(f"  Total Events: {metrics_24h['total_events']}")
            
            # 趋势 (Trends)
            trends = dashboard_data['trends']
            if trends:
                self.stdout.write(f"\nTrends (vs previous 24h):")
                for event_type, trend_data in trends.items():
                    trend_symbol = self.get_trend_symbol(trend_data['trend'])
                    self.stdout.write(f"  {event_type}: {trend_data['current']} {trend_symbol} ({trend_data['change_percent']:+.1f}%)")
            
            # 建议 (Recommendations)
            recommendations = dashboard_data['recommendations']
            if recommendations:
                self.stdout.write(f"\nRecommendations:")
                for rec in recommendations:
                    self.stdout.write(f"  • {rec}")

    def get_colored_risk_level(self, risk_level):
        """获取带颜色的风险级别 (Get colored risk level)"""
        color_map = {
            'low': self.style.SUCCESS,
            'medium': self.style.WARNING,
            'high': self.style.ERROR,
            'critical': self.style.ERROR
        }
        color_func = color_map.get(risk_level, self.style.SUCCESS)
        return color_func(risk_level.upper())

    def get_severity_color(self, severity):
        """获取严重程度颜色 (Get severity color)"""
        color_map = {
            'low': self.style.SUCCESS,
            'medium': self.style.WARNING,
            'high': self.style.ERROR
        }
        return color_map.get(severity, self.style.SUCCESS)

    def get_trend_symbol(self, trend):
        """获取趋势符号 (Get trend symbol)"""
        symbol_map = {
            'up': '↑',
            'down': '↓',
            'stable': '→'
        }
        return symbol_map.get(trend, '→')