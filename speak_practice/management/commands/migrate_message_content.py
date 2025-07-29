"""
迁移消息内容格式管理命令 (Migrate message content format management command)

This command migrates existing ChatMessage content to the new format
to ensure backward compatibility.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from speak_practice.models import ChatMessage
from speak_practice.message_utils import MessageContentFormatter


class Command(BaseCommand):
    help = '迁移现有聊天消息内容到新格式 (Migrate existing chat message content to new format)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='显示将要迁移的消息但不实际执行迁移 (Show messages to be migrated without actually migrating)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='批处理大小 (Batch size for processing messages)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        
        self.stdout.write(
            self.style.SUCCESS('开始迁移聊天消息内容格式... (Starting chat message content format migration...)')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('这是一次试运行，不会实际修改数据库 (This is a dry run, no database changes will be made)')
            )
        
        # 获取所有需要迁移的消息 (Get all messages that need migration)
        messages_to_migrate = []
        total_messages = ChatMessage.objects.count()
        
        self.stdout.write(f'正在检查 {total_messages} 条消息... (Checking {total_messages} messages...)')
        
        # 分批处理消息 (Process messages in batches)
        for offset in range(0, total_messages, batch_size):
            batch = ChatMessage.objects.all()[offset:offset + batch_size]
            
            for message in batch:
                # 检查消息是否需要迁移 (Check if message needs migration)
                if not MessageContentFormatter.is_backward_compatible(message.message_content):
                    messages_to_migrate.append(message)
                    
                    if dry_run:
                        self.stdout.write(
                            f'消息 ID {message.id} 需要迁移: {str(message.message_content)[:100]}...'
                            f' (Message ID {message.id} needs migration: {str(message.message_content)[:100]}...)'
                        )
        
        migration_count = len(messages_to_migrate)
        
        if migration_count == 0:
            self.stdout.write(
                self.style.SUCCESS('没有找到需要迁移的消息 (No messages found that need migration)')
            )
            return
        
        self.stdout.write(
            f'找到 {migration_count} 条需要迁移的消息 (Found {migration_count} messages that need migration)'
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('试运行完成，使用 --no-dry-run 执行实际迁移 (Dry run complete, use without --dry-run to perform actual migration)')
            )
            return
        
        # 执行实际迁移 (Perform actual migration)
        migrated_count = 0
        error_count = 0
        
        with transaction.atomic():
            for message in messages_to_migrate:
                try:
                    # 迁移消息内容 (Migrate message content)
                    migrated_content = MessageContentFormatter.migrate_legacy_content(
                        message.message_content,
                        message.sender_type
                    )
                    
                    # 更新消息内容 (Update message content)
                    message.message_content = migrated_content
                    
                    # 如果是语音消息且有音频时长信息，更新audio_duration字段
                    # (If it's a voice message with audio duration info, update audio_duration field)
                    if (migrated_content.get('input_method') == 'voice' and 
                        'audio_duration' in migrated_content and 
                        message.audio_duration is None):
                        message.audio_duration = migrated_content['audio_duration']
                        message.input_method = 'voice'
                    elif migrated_content.get('input_method') == 'translation':
                        message.input_method = 'translation'
                    else:
                        message.input_method = 'text'
                    
                    message.save()
                    migrated_count += 1
                    
                    if migrated_count % 10 == 0:
                        self.stdout.write(f'已迁移 {migrated_count}/{migration_count} 条消息... (Migrated {migrated_count}/{migration_count} messages...)')
                
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f'迁移消息 ID {message.id} 时出错: {str(e)} (Error migrating message ID {message.id}: {str(e)})'
                        )
                    )
        
        # 输出迁移结果 (Output migration results)
        if error_count == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'迁移完成！成功迁移 {migrated_count} 条消息 (Migration complete! Successfully migrated {migrated_count} messages)'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'迁移完成，但有 {error_count} 条消息迁移失败 (Migration complete, but {error_count} messages failed to migrate)'
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'成功迁移 {migrated_count} 条消息 (Successfully migrated {migrated_count} messages)'
                )
            )
        
        # 验证迁移结果 (Verify migration results)
        self.stdout.write('正在验证迁移结果... (Verifying migration results...)')
        
        remaining_legacy_messages = 0
        for message in ChatMessage.objects.all():
            if not MessageContentFormatter.is_backward_compatible(message.message_content):
                remaining_legacy_messages += 1
        
        if remaining_legacy_messages == 0:
            self.stdout.write(
                self.style.SUCCESS('验证通过：所有消息都已迁移到新格式 (Verification passed: All messages migrated to new format)')
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f'验证失败：仍有 {remaining_legacy_messages} 条消息使用旧格式 (Verification failed: {remaining_legacy_messages} messages still use old format)'
                )
            )