import logging
from datetime import datetime, date
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from .models import PageVisitStatistics, DailyStatistics
import requests
import json
from django.core.cache import cache

# 配置日志
logger = logging.getLogger('namegen.statistics')

class StatisticsService:
    """统计服务类"""
    
    @staticmethod
    def get_client_ip(request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    def get_location_from_ip(ip_address):
        """根据IP地址获取地理位置信息"""
        # 缓存IP地理位置信息，避免重复查询
        cache_key = f"ip_location_{ip_address}"
        cached_location = cache.get(cache_key)
        if cached_location:
            return cached_location
        
        try:
            # 使用免费的IP地理位置API
            response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    location = {
                        'country': data.get('country', ''),
                        'city': data.get('city', ''),
                    }
                    # 缓存30分钟
                    cache.set(cache_key, location, 1800)
                    return location
        except Exception as e:
            logger.error(f"获取IP地理位置失败: {ip_address} - {str(e)}")
        
        return {'country': '', 'city': ''}
    
    @staticmethod
    def record_activity(request, activity_type, **kwargs):
        """记录用户活动"""
        try:
            ip_address = StatisticsService.get_client_ip(request)
            location = StatisticsService.get_location_from_ip(ip_address)
            
            # 获取会话密钥
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
            
            # 创建统计记录
            stat_data = {
                'activity_type': activity_type,
                'ip_address': ip_address,
                'country': location.get('country', ''),
                'city': location.get('city', ''),
                'session_key': session_key,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'page_url': request.build_absolute_uri(),
            }
            
            # 添加额外参数
            stat_data.update(kwargs)
            
            PageVisitStatistics.objects.create(**stat_data)
            
            # 异步更新每日统计
            StatisticsService.update_daily_statistics(activity_type, ip_address, session_key, location)
            
            logger.info(f"记录活动: {activity_type} - IP: {ip_address}")
            
        except Exception as e:
            logger.error(f"记录统计活动失败: {str(e)}")
    
    @staticmethod
    def update_daily_statistics(activity_type, ip_address, session_key, location):
        """更新每日统计"""
        try:
            today = timezone.now().date()
            
            with transaction.atomic():
                # 获取或创建每日统计记录
                daily_stats, created = DailyStatistics.objects.get_or_create(
                    date=today,
                    defaults={
                        'page_visits': 0,
                        'unique_visitors': 0,
                        'unique_ips': 0,
                        'name_generations': 0,
                        'name_card_generations': 0,
                        'tts_requests': 0,
                        'share_clicks': 0,
                        'country_stats': {},
                        'city_stats': {},
                    }
                )
                
                # 更新相应的计数器
                if activity_type == 'page_visit':
                    daily_stats.page_visits += 1
                elif activity_type == 'name_generation':
                    daily_stats.name_generations += 1
                elif activity_type == 'name_card_generation':
                    daily_stats.name_card_generations += 1
                elif activity_type == 'tts_request':
                    daily_stats.tts_requests += 1
                elif activity_type == 'share_click':
                    daily_stats.share_clicks += 1
                
                # 更新独立访客数和IP数
                daily_stats.unique_visitors = PageVisitStatistics.objects.filter(
                    created_at__date=today,
                    activity_type='page_visit'
                ).values('session_key').distinct().count()
                
                daily_stats.unique_ips = PageVisitStatistics.objects.filter(
                    created_at__date=today
                ).values('ip_address').distinct().count()
                
                # 更新地理统计
                if location.get('country'):
                    country_stats = daily_stats.country_stats
                    country_stats[location['country']] = country_stats.get(location['country'], 0) + 1
                    daily_stats.country_stats = country_stats
                
                if location.get('city'):
                    city_stats = daily_stats.city_stats
                    city_stats[location['city']] = city_stats.get(location['city'], 0) + 1
                    daily_stats.city_stats = city_stats
                
                daily_stats.save()
                
        except Exception as e:
            logger.error(f"更新每日统计失败: {str(e)}")
    
    @staticmethod
    def get_statistics_summary(days=30):
        """获取统计摘要"""
        try:
            end_date = timezone.now().date()
            start_date = end_date - timezone.timedelta(days=days)
            
            # 获取每日统计
            daily_stats = DailyStatistics.objects.filter(
                date__range=[start_date, end_date]
            ).order_by('-date')
            
            # 计算总计
            total_visits = sum(stat.page_visits for stat in daily_stats)
            total_unique_visitors = sum(stat.unique_visitors for stat in daily_stats)
            total_name_generations = sum(stat.name_generations for stat in daily_stats)
            total_share_clicks = sum(stat.share_clicks for stat in daily_stats)
            
            # 获取最受欢迎的国家和城市
            all_countries = {}
            all_cities = {}
            
            for stat in daily_stats:
                for country, count in stat.country_stats.items():
                    all_countries[country] = all_countries.get(country, 0) + count
                for city, count in stat.city_stats.items():
                    all_cities[city] = all_cities.get(city, 0) + count
            
            # 排序获取前10名
            top_countries = sorted(all_countries.items(), key=lambda x: x[1], reverse=True)[:10]
            top_cities = sorted(all_cities.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                'period': f"{start_date} to {end_date}",
                'total_visits': total_visits,
                'total_unique_visitors': total_unique_visitors,
                'total_name_generations': total_name_generations,
                'total_share_clicks': total_share_clicks,
                'daily_stats': list(daily_stats.values()),
                'top_countries': top_countries,
                'top_cities': top_cities,
            }
            
        except Exception as e:
            logger.error(f"获取统计摘要失败: {str(e)}")
            return None
    
    @staticmethod
    def get_popular_names(days=30):
        """获取热门生成的姓名"""
        try:
            end_date = timezone.now().date()
            start_date = end_date - timezone.timedelta(days=days)
            
            popular_names = PageVisitStatistics.objects.filter(
                activity_type='name_generation',
                created_at__date__range=[start_date, end_date],
                generated_name__isnull=False
            ).values('generated_name').annotate(
                count=Count('generated_name')
            ).order_by('-count')[:20]
            
            return list(popular_names)
            
        except Exception as e:
            logger.error(f"获取热门姓名失败: {str(e)}")
            return [] 