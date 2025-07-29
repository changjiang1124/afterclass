  生产环境摘要

  ---

  1. 项目详情
   * 项目根目录: /var/www/afterclass
   * 版本控制: Git
   * 当前提交哈希: 021af48

  ---

  2. 系统
   * 操作系统: Ubuntu 24.04.2 LTS

  ---

  3. 应用技术栈
   * 框架: Django 5.1
   * Python 版本: 3.12.3 (在 .venv 虚拟环境中)
   * 依赖管理: 通过 requirements.txt 文件管理
   * 数据库:
       * 引擎: django.db.backends.sqlite3
       * 数据库文件: /var/www/afterclass/db.sqlite3

  ---

  4. 配置
   * 主配置文件: tongcove/settings.py
   * 密钥管理: 密钥和敏感凭证通过 .env 文件加载到环境变量中 (例如 OPENAI_API_KEY, GOOGLE_APPLICATION_CREDENTIALS)。
   * 允许的主机 (ALLOWED_HOSTS): 127.0.0.1, afterclass.learnchineseperth.com.au

  ---

  5. 服务基础设施
   * Web 服务器: 具体的 Web 服务器 (例如 Gunicorn, Nginx) 无法仅从文件结构中确定，需要检查正在运行的进程或部署配置。
   * WSGI 应用入口: tongcove.wsgi.application