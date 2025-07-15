# Namegen Statistics System

这个统计系统为名字生成器应用提供全面的使用分析和跟踪功能。

## 功能特点

### 自动跟踪的活动

1. **页面访问** (page_visit) - 自动记录所有namegen页面的访问
2. **姓名生成** (name_generation) - 记录用户生成中文姓名的活动
3. **名片生成** (name_card_generation) - 跟踪名片图片生成请求
4. **语音合成** (tts_request) - 记录文字转语音请求
5. **分享点击** (share_click) - 跟踪不同平台的分享按钮点击
6. **结果查看** (result_view) - 记录用户查看生成结果的活动

### 收集的数据

- **基本信息**: IP地址、用户代理、页面URL、会话密钥
- **地理位置**: 国家、城市（基于IP地址自动获取）
- **时间戳**: 精确的活动时间记录
- **性能指标**: 页面响应时间
- **关联数据**: 生成的姓名、请求ID、分享平台等

## 系统组件

### 1. 数据模型

#### PageVisitStatistics
详细记录每个用户活动的模型。

#### DailyStatistics
每日汇总统计，包含：
- 访问量、独立访客数、独立IP数
- 各功能使用次数
- 地理分布统计

### 2. 中间件

**StatisticsMiddleware** - 自动记录所有namegen页面的访问活动。

### 3. 统计服务

**StatisticsService** 提供以下功能：
- `record_activity()` - 记录用户活动
- `get_statistics_summary()` - 获取统计摘要
- `get_popular_names()` - 获取热门姓名列表

### 4. 前端跟踪

JavaScript函数自动跟踪分享按钮点击，支持：
- Facebook分享
- Twitter分享  
- WhatsApp分享
- 复制到剪贴板
- 原生分享API

## 使用方法

### 查看统计数据

1. **管理后台**
   - 访问 `/admin/` 查看详细的统计记录
   - 可以按活动类型、地理位置、时间等过滤

2. **统计仪表板**
   - 访问 `/namegen/statistics/` 查看可视化统计报告
   - 支持不同时间段的数据查看

3. **API接口**
   - GET `/namegen/statistics/api/?days=30` 获取JSON格式的统计数据

### 管理命令

#### 更新每日统计
```bash
# 更新昨天的统计数据
python manage.py update_daily_stats

# 更新特定日期的统计
python manage.py update_daily_stats --date 2024-01-15

# 更新最近7天的统计
python manage.py update_daily_stats --days 7
```

#### 建议的定时任务
```bash
# 添加到crontab，每天凌晨2点更新统计
0 2 * * * cd /var/www/afterclass && python manage.py update_daily_stats
```

## 配置选项

### 地理位置API
使用免费的ip-api.com服务获取IP地理位置：
- 自动缓存IP位置信息30分钟
- 失败时优雅降级，不影响主要功能

### 缓存配置
- IP地理位置信息缓存30分钟
- 使用Django内存缓存存储

### 日志配置
- 统计活动记录到 `logs/namegen_statistics.log`
- 错误和重要事件同时输出到控制台

## 数据隐私

### 收集的信息
- **匿名化处理**: 不收集个人身份信息
- **IP地址**: 仅用于地理统计，不与个人关联
- **会话跟踪**: 用于计算独立访客，不长期存储

### 数据保留策略
- 详细统计记录建议保留90天
- 每日汇总统计可长期保留
- 管理命令支持自动清理旧数据

## 性能考虑

### 优化措施
- 异步记录统计信息，不影响用户体验
- IP地理位置查询有缓存机制
- 数据库索引优化查询性能
- 批量处理每日统计更新

### 监控建议
- 定期检查统计中间件性能
- 监控IP地理位置API调用频率
- 关注数据库存储空间增长

## 扩展功能

### 可添加的统计维度
- 用户设备类型检测
- 浏览器类型统计
- 搜索引擎来源跟踪
- 页面停留时间分析

### 集成第三方分析
可以轻松集成Google Analytics、百度统计等第三方服务。

## 故障排除

### 常见问题

1. **统计记录不显示**
   - 检查中间件是否正确配置
   - 确认数据库迁移已完成
   - 查看日志文件确认错误信息

2. **地理位置信息缺失**
   - 检查网络连接到ip-api.com
   - 查看缓存配置是否正确
   - 确认IP地址格式有效

3. **分享跟踪不工作**
   - 确认JavaScript代码已加载
   - 检查CSRF令牌配置
   - 查看浏览器控制台错误信息

### 调试模式
```python
# 在settings.py中启用调试日志
LOGGING['loggers']['namegen.statistics']['level'] = 'DEBUG'
```

## 数据导出

### 导出统计数据
```bash
# 导出特定时间段的统计数据
python manage.py dumpdata namegen.PageVisitStatistics --indent 2 > statistics_export.json

# 导出每日汇总
python manage.py dumpdata namegen.DailyStatistics --indent 2 > daily_stats_export.json
``` 