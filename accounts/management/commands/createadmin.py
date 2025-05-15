from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import IntegrityError


class Command(BaseCommand):
    help = '创建或更新用户密码并赋予管理员权限'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='用户名')
        parser.add_argument('password', type=str, help='密码')
        parser.add_argument('email', type=str, nargs='?', default='', help='电子邮箱（可选）')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        email = options['email']

        try:
            user = User.objects.get(username=username)
            user.set_password(password)
            if email:
                user.email = email
            self.stdout.write(self.style.SUCCESS(f'更新用户"{username}"的密码'))
        except User.DoesNotExist:
            user = User.objects.create_user(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f'创建用户"{username}"'))

        # 赋予用户管理员权限
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.stdout.write(self.style.SUCCESS(f'用户"{username}"现在拥有完全管理员权限')) 