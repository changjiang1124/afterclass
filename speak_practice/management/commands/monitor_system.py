"""
系统监控管理命令 (System Monitoring Management Command)
用于监控系统状态和性能指标
"""

import json
import time
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from deployment.monitoring import MonitoringDashboard, SystemMonitor, LogAnalyzer, AlertManager


class Command(BaseCommand):
    help = 'System monitoring and performance analysis commands'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['dashboard', 'metrics', 'health', 'alerts', 'logs', 'watch'],
            help='Monitoring action to perform'
        )
        parser.add_argument(
            '--format',
            choices=['json', 'table'],
            default='table',
            help='Output format (default: table)'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='Update interval in seconds for watch mode (default: 5)'
        )
        parser.add_argument(
            '--log-file',
            type=str,
            default='logs/django.log',
            help='Log file path for analysis (default: logs/django.log)'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        try:
            if action == 'dashboard':
                self.show_dashboard(options)
            elif action == 'metrics':
                self.show_metrics(options)
            elif action == 'health':
                self.show_health(options)
            elif action == 'alerts':
                self.show_alerts(options)
            elif action == 'logs':
                self.analyze_logs(options)
            elif action == 'watch':
                self.watch_system(options)
        except Exception as e:
            raise CommandError(f'Monitoring command failed: {str(e)}')

    def show_dashboard(self, options):
        """显示监控仪表板 (Show monitoring dashboard)"""
        dashboard = MonitoringDashboard()
        data = dashboard.get_dashboard_data()
        
        if options['format'] == 'json':
            self.stdout.write(json.dumps(data, indent=2, default=str))
        else:
            self.display_dashboard_table(data)

    def show_metrics(self, options):
        """显示系统指标 (Show system metrics)"""
        monitor = SystemMonitor()
        
        system_metrics = monitor.get_system_metrics()
        database_metrics = monitor.get_database_metrics()
        cache_metrics = monitor.get_cache_metrics()
        app_metrics = monitor.get_application_metrics()
        
        if options['format'] == 'json':
            data = {
                'system': system_metrics,
                'database': database_metrics,
                'cache': cache_metrics,
                'application': app_metrics
            }
            self.stdout.write(json.dumps(data, indent=2, default=str))
        else:
            self.display_metrics_table(system_metrics, database_metrics, cache_metrics, app_metrics)

    def show_health(self, options):
        """显示健康状态 (Show health status)"""
        monitor = SystemMonitor()
        health_data = monitor.check_health()
        
        if options['format'] == 'json':
            self.stdout.write(json.dumps(health_data, indent=2, default=str))
        else:
            self.display_health_table(health_data)

    def show_alerts(self, options):
        """显示告警信息 (Show alerts)"""
        monitor = SystemMonitor()
        alert_manager = AlertManager()
        
        system_metrics = monitor.get_system_metrics()
        alerts = alert_manager.check_system_alerts(system_metrics)
        
        if options['format'] == 'json':
            self.stdout.write(json.dumps(alerts, indent=2, default=str))
        else:
            self.display_alerts_table(alerts)

    def analyze_logs(self, options):
        """分析日志 (Analyze logs)"""
        log_file = options['log_file']
        analyzer = LogAnalyzer(log_file)
        
        error_patterns = analyzer.analyze_error_patterns()
        performance_insights = analyzer.get_performance_insights()
        
        if options['format'] == 'json':
            data = {
                'error_patterns': error_patterns,
                'performance_insights': performance_insights
            }
            self.stdout.write(json.dumps(data, indent=2, default=str))
        else:
            self.display_log_analysis_table(error_patterns, performance_insights)

    def watch_system(self, options):
        """实时监控系统 (Watch system in real-time)"""
        interval = options['interval']
        dashboard = MonitoringDashboard()
        
        self.stdout.write(self.style.SUCCESS(f'Starting system monitoring (update every {interval}s)...'))
        self.stdout.write('Press Ctrl+C to stop')
        
        try:
            while True:
                # 清屏 (Clear screen)
                import os
                os.system('clear' if os.name == 'posix' else 'cls')
                
                # 显示时间戳 (Show timestamp)
                self.stdout.write(self.style.SUCCESS(f'System Monitor - {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'))
                self.stdout.write('=' * 80)
                
                # 获取并显示数据 (Get and display data)
                data = dashboard.get_dashboard_data()
                self.display_dashboard_table(data)
                
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write('\nMonitoring stopped.')

    def display_dashboard_table(self, data):
        """显示仪表板表格 (Display dashboard table)"""
        summary = data.get('summary', {})
        health = data.get('health_status', {})
        alerts = data.get('alerts', [])
        
        # 系统状态 (System status)
        status_color = self.get_status_color(summary.get('status', 'unknown'))
        self.stdout.write(f"\nSystem Status: {status_color(summary.get('status', 'unknown').upper())}")
        
        # 资源使用情况 (Resource usage)
        self.stdout.write(f"\nResource Usage:")
        self.stdout.write(f"  CPU:    {summary.get('cpu_usage', 0):.1f}%")
        self.stdout.write(f"  Memory: {summary.get('memory_usage', 0):.1f}%")
        self.stdout.write(f"  Disk:   {summary.get('disk_usage', 0):.1f}%")
        
        # 健康检查 (Health checks)
        self.stdout.write(f"\nHealth Checks:")
        for check_name, check_status in health.get('checks', {}).items():
            status_symbol = '✓' if 'healthy' in check_status else '✗'
            self.stdout.write(f"  {status_symbol} {check_name}: {check_status}")
        
        # 告警 (Alerts)
        if alerts:
            self.stdout.write(f"\nActive Alerts ({len(alerts)}):")
            for alert in alerts:
                severity_color = self.get_severity_color(alert.get('severity', 'info'))
                self.stdout.write(f"  {severity_color(alert.get('severity', 'info').upper())}: {alert.get('message', '')}")
        else:
            self.stdout.write(f"\nNo active alerts")
        
        # 应用程序指标 (Application metrics)
        app_metrics = data.get('application_metrics', {})
        if app_metrics:
            self.stdout.write(f"\nApplication Metrics:")
            users = app_metrics.get('users', {})
            sessions = app_metrics.get('sessions', {})
            messages = app_metrics.get('messages', {})
            
            self.stdout.write(f"  Users:    {users.get('total', 0)} total, {users.get('active_24h', 0)} active (24h)")
            self.stdout.write(f"  Sessions: {sessions.get('total', 0)} total, {sessions.get('created_24h', 0)} created (24h)")
            self.stdout.write(f"  Messages: {messages.get('total', 0)} total, {messages.get('sent_24h', 0)} sent (24h)")

    def display_metrics_table(self, system, database, cache, application):
        """显示指标表格 (Display metrics table)"""
        # 系统指标 (System metrics)
        if system:
            self.stdout.write(self.style.SUCCESS('\nSystem Metrics:'))
            cpu = system.get('cpu', {})
            memory = system.get('memory', {})
            disk = system.get('disk', {})
            
            self.stdout.write(f"  CPU: {cpu.get('percent', 0):.1f}% ({cpu.get('count', 0)} cores)")
            self.stdout.write(f"  Memory: {memory.get('percent', 0):.1f}% ({self.format_bytes(memory.get('used', 0))}/{self.format_bytes(memory.get('total', 0))})")
            self.stdout.write(f"  Disk: {disk.get('percent', 0):.1f}% ({self.format_bytes(disk.get('used', 0))}/{self.format_bytes(disk.get('total', 0))})")
        
        # 数据库指标 (Database metrics)
        if database:
            self.stdout.write(self.style.SUCCESS('\nDatabase Metrics:'))
            self.stdout.write(f"  Active Connections: {database.get('active_connections', 0)}")
            self.stdout.write(f"  Database Size: {database.get('database_size', 'Unknown')}")
        
        # 缓存指标 (Cache metrics)
        if cache:
            redis = cache.get('redis', {})
            self.stdout.write(self.style.SUCCESS('\nCache Metrics:'))
            self.stdout.write(f"  Memory Used: {redis.get('used_memory_human', '0B')}")
            self.stdout.write(f"  Connected Clients: {redis.get('connected_clients', 0)}")
            self.stdout.write(f"  Hit Rate: {redis.get('hit_rate', 0):.1f}%")

    def display_health_table(self, health_data):
        """显示健康状态表格 (Display health status table)"""
        status = health_data.get('status', 'unknown')
        checks = health_data.get('checks', {})
        
        status_color = self.get_status_color(status)
        self.stdout.write(f"\nOverall Status: {status_color(status.upper())}")
        
        self.stdout.write(f"\nHealth Checks:")
        for check_name, check_status in checks.items():
            if 'healthy' in check_status:
                symbol = self.style.SUCCESS('✓')
            elif 'warning' in check_status:
                symbol = self.style.WARNING('⚠')
            else:
                symbol = self.style.ERROR('✗')
            
            self.stdout.write(f"  {symbol} {check_name}: {check_status}")

    def display_alerts_table(self, alerts):
        """显示告警表格 (Display alerts table)"""
        if not alerts:
            self.stdout.write(self.style.SUCCESS('No active alerts'))
            return
        
        self.stdout.write(f"\nActive Alerts ({len(alerts)}):")
        for alert in alerts:
            severity = alert.get('severity', 'info')
            message = alert.get('message', '')
            
            severity_color = self.get_severity_color(severity)
            self.stdout.write(f"  {severity_color(severity.upper())}: {message}")

    def display_log_analysis_table(self, error_patterns, performance_insights):
        """显示日志分析表格 (Display log analysis table)"""
        # 错误模式 (Error patterns)
        if error_patterns.get('error_patterns'):
            self.stdout.write(self.style.SUCCESS('\nError Patterns:'))
            for error_type, count in error_patterns['error_patterns'].items():
                self.stdout.write(f"  {error_type}: {count}")
        
        # 性能洞察 (Performance insights)
        if performance_insights.get('api_usage'):
            self.stdout.write(self.style.SUCCESS('\nTop API Endpoints:'))
            for endpoint, count in performance_insights['api_usage'].items():
                self.stdout.write(f"  {endpoint}: {count}")

    def get_status_color(self, status):
        """获取状态颜色 (Get status color)"""
        color_map = {
            'healthy': self.style.SUCCESS,
            'warning': self.style.WARNING,
            'unhealthy': self.style.ERROR,
            'unknown': self.style.WARNING
        }
        return color_map.get(status.lower(), self.style.SUCCESS)

    def get_severity_color(self, severity):
        """获取严重程度颜色 (Get severity color)"""
        color_map = {
            'info': self.style.SUCCESS,
            'warning': self.style.WARNING,
            'critical': self.style.ERROR,
            'error': self.style.ERROR
        }
        return color_map.get(severity.lower(), self.style.SUCCESS)

    def format_bytes(self, bytes_value):
        """格式化字节数 (Format bytes)"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f}{unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f}PB"