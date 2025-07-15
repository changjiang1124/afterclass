import time
import logging
from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve
from .statistics import StatisticsService

logger = logging.getLogger('namegen.middleware')

class StatisticsMiddleware(MiddlewareMixin):
    """统计中间件 - 自动记录页面访问和性能指标"""
    
    def process_request(self, request):
        """请求开始时记录时间"""
        request.start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """响应完成时记录统计信息"""
        try:
            # 只统计namegen应用的页面
            if hasattr(request, 'resolver_match') and request.resolver_match:
                if request.resolver_match.app_name == 'namegen':
                    # 计算响应时间
                    response_time = time.time() - getattr(request, 'start_time', time.time())
                    
                    # 记录页面访问
                    StatisticsService.record_activity(
                        request, 
                        'page_visit',
                        response_time=response_time
                    )
        except Exception as e:
            logger.error(f"统计中间件错误: {str(e)}")
        
        return response 