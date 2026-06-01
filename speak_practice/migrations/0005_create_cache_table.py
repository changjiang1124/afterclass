"""
创建 DatabaseCache 所需的缓存表 (Create the table required by DatabaseCache).

settings.CACHES['default'] 已从 LocMemCache 切换为 DatabaseCache(LOCATION='afterclass_cache')，
该后端需要一张数据库表。这里用 createcachetable 创建（幂等，已存在则跳过），
使部署 / CI / 全新 clone 在 migrate 后即可直接使用缓存，无需手动跑额外命令。
(DatabaseCache needs a DB table; create it via createcachetable so migrate is enough.)
"""

from django.core.management import call_command
from django.db import migrations


def create_cache_table(apps, schema_editor):
    call_command('createcachetable', database=schema_editor.connection.alias)


def drop_cache_table(apps, schema_editor):
    schema_editor.execute('DROP TABLE IF EXISTS afterclass_cache')


class Migration(migrations.Migration):

    dependencies = [
        ('speak_practice', '0004_practicescenetemplate_usersceneexposure_and_more'),
    ]

    operations = [
        migrations.RunPython(create_cache_table, drop_cache_table),
    ]
