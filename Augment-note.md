# 增强功能进度笔记

## 当前问题解决
- **问题**: Django 服务器因缺少 `magic` 模块而启动失败。
- **根本原因**: `requirements.txt` 中列出的 `python-magic` 包未安装，并且缺少系统级的 `libmagic` 库。
- **解决方案**:
  1. 使用 pip 安装 `python-magic` 包。
  2. 使用 Homebrew (`brew install libmagic`) 安装系统级的 `libmagic` 库。
- **状态**: ✅ 已解决 - 依赖项已成功安装。

## `magic` 库的用途
项目中的 `python-magic` 库是音频文件验证的关键安全组件：

### 主要功能:
1. **文件类型检测**: 通过读取文件头来检测真实的 MIME 类型，而不仅仅依赖文件扩展名。
2. **安全验证**: 防止攻击者将恶意文件重命名为音频扩展名来进行文件伪装攻击。
3. **MIME 类型验证**: 确保上传的文件确实是音频文件（如 wav、mp3、m4a 等）。

### 实现位置:
- 在 `speak_practice/security.py` 的 `AudioSecurityValidator` 类中使用。
- 作为综合音频文件验证系统的一部分。
- 用于验证“口语练习”功能上传的音频文件。

### 安全优势:
- 防止伪装成音频文件的恶意文件上传。
- 提供比基于扩展名的检查更可靠的文件类型检测。
- 增强用户文件上传的整体应用安全性。
- 通过读取文件头（前 1KB）并使用 `libmagic` 来检测真实文件类型。

### 技术细节:
- 需要 Python 包 (`python-magic`) 和系统库 (`libmagic`)。
- 在 macOS 上，`libmagic` 通过 Homebrew 安装。
- 在 `validate_mime_type()` 方法中用于检测真实的 MIME 类型。
- 如果 `magic` 检测失败，则回退到 `mimetypes` 模块。

## 数据库配置分析
**用户问题**: 确认开发和生产环境是否都使用 SQLite3。

### 调查结果:
- **开发环境**: ✅ 使用 SQLite3 (`tongcove/settings.py`)
  - 数据库: 项目根目录下的 `db.sqlite3` 文件。
  - 引擎: `django.db.backends.sqlite3`。

- **生产环境**: ❌ 使用 PostgreSQL (`deployment/production_settings.py`)
  - 引擎: `django.db.backends.postgresql` (默认)。
  - 需要环境变量: `DB_NAME`, `DB_USER`, `DB_PASSWORD` 等。
  - 服务文件显示依赖于 `postgresql.service`。
  - 同时配置了 Redis 缓存。

### 配置详情:
- 开发环境使用默认的 `tongcove.settings`。
- 生产环境使用 `deployment.production_settings` (在 systemd 服务中设置)。
- 生产环境需要 `.env.production` 文件包含数据库凭据。
- 当前设置遵循最佳实践：开发使用 SQLite，生产使用 PostgreSQL。

## 生产环境 SQLite3 配置

**用户请求**: 将生产环境的数据库从 PostgreSQL 更改为 SQLite3。

### 已做更改:
1. **修改 `deployment/production_settings.py`**:
   - 将默认数据库更改为 SQLite3。
   - 添加了通过 `USE_POSTGRESQL=true` 环境变量使用 PostgreSQL 的选项。
   - 将缓存从 Redis 更改为本地内存缓存。
   - 添加了通过 `USE_REDIS=true` 环境变量使用 Redis 的选项。

2. **更新 `deployment/tongcove.service`**:
   - 移除了对 PostgreSQL 服务的依赖。
   - 简化了服务依赖。

3. **创建配置文件**:
   - `.env.production.sqlite`: 用于 SQLite3 生产配置的模板。
   - `deployment/setup_sqlite_production.sh`: 自动化设置脚本。

### 环境检测逻辑:
- **开发环境**: 使用 `tongcove.settings` (默认)。
  - 主机名检查: `socket.gethostname() == 'CJs-MBP-1421.local'`。
  - 数据库: SQLite3 (`db.sqlite3`)。

- **生产环境**: 使用 `deployment.production_settings`。
  - 通过 systemd 设置: `DJANGO_SETTINGS_MODULE=deployment.production_settings`。
  - 数据库: 现在是 SQLite3 (从 PostgreSQL 修改而来)。
  - URL: afterclass.learnchineseperth.com.au。
  - 技术栈: nginx + gunicorn。

### ⚠️ 重要提示: 对现有生产环境的安全部署

**用户已有生产环境** - 创建了安全更新脚本：

#### 对于新安装:
- `./deployment/setup_sqlite_production.sh` (完整设置 - 将覆盖所有内容)。

#### 对于现有生产环境 (安全):
- `./deployment/update_to_sqlite_safe.sh` (仅更新代码，保留数据库和配置)。
- `deployment/DATABASE_MIGRATION_GUIDE.md` (详细的迁移说明)。

#### 安全更新流程:
1. **备份**: 脚本在更改前会自动创建备份。
2. **代码更新**: 只更新应用程序代码，并保留：
   - 现有数据库 (`db.sqlite3` 或 PostgreSQL)。
   - 配置文件 (`.env.production`)。
   - 用户数据和媒体文件。
3. **迁移选项**:
   - 保留 PostgreSQL: 在 `.env.production` 中设置 `USE_POSTGRESQL=true`。
   - 切换到 SQLite3: 遵循迁移指南进行数据传输。

## 生产环境更新分析

**用户问题**: 在运行 commit `021af48` 的生产环境上执行 `git pull` 会有什么影响？

### ✅ **修正后的生产环境信息** (来自 `deployment/production_env.md`):
- **项目路径**: `/var/www/afterclass` (不是 `/var/www/tongcove`)。
- **数据库**: 已在使用 SQLite3 (`/var/www/afterclass/db.sqlite3`)。
- **设置**: 使用 `tongcove/settings.py` (不是 `production_settings.py`)。
- **系统**: Ubuntu 24.04.2 LTS, Python 3.12.3。

### 当前版本差距:
- **生产环境**: `021af48` ("update")。
- **开发环境**: `d1fe06e` (HEAD)。
- **差距**: 6 个 commits，包含重大变更。

### 自 `021af48` 以来的关键变更:
1. **数据库变更**: 2 个新的迁移文件，需要运行 `manage.py migrate`。
2. **新依赖**: `python-magic==0.4.27` + 系统 `libmagic` 库。
3. **架构变更**: 新的服务层、安全模块、管理命令。
4. **前端大改**: 完整的 UI 重新设计，新的 JavaScript 模块。
5. **部署文件**: 新的 nginx 配置、systemd 服务、生产设置。

### `git pull` 的影响:
- ✅ **安全**: 代码更新本身不会破坏现有功能。
- ✅ **数据库**: 已在使用 SQLite3，因此无需更改数据库引擎。
- ⚠️ **需要**: 数据库迁移、依赖安装、服务重启。
- ⚠️ **风险**: 如果没有正确的迁移步骤，新功能将无法工作。

### ✅ **清理部署目录** (Cleaned Up Deployment Directory):
**移除的不必要文件**:
- ❌ `.env.production.sqlite`, `.env.production.template` (不需要)
- ❌ `deployment/PRODUCTION_UPDATE_GUIDE.md` (过于复杂)
- ❌ `deployment/update_to_sqlite_safe.sh` (过度工程化)
- ❌ `deployment/deploy.sh` (470行，过于复杂)
- ❌ `deployment/production_settings.py` (与实际设置冲突)
- ❌ `deployment/setup_sqlite_production.sh` (路径错误)
- ❌ `deployment/tongcove.service` (路径/配置错误)
- ❌ `deployment/monitoring.py` (486行，过度工程化)
- ❌ `deployment/DATABASE_MIGRATION_GUIDE.md` (不需要)

**保留的核心文件**:
- ✅ `deployment/production_env.md` (实际环境文档)
- ✅ `deployment/SIMPLE_UPDATE_GUIDE.md` (定制更新指南)
- ✅ `deployment/nginx.conf` (已修正路径为 `/var/www/afterclass`)

### 建议操作:
**简单的手动更新流程**:
1. 备份数据库: `cp db.sqlite3 db.sqlite3.backup.$(date +%Y%m%d_%H%M%S)`
2. 更新代码: `git pull origin main`
3. 安装依赖: `apt-get install libmagic1` + `pip install -r requirements.txt`
4. 迁移数据库: `python manage.py migrate`
5. 收集静态文件: `python manage.py collectstatic --noinput`
6. 重启服务

**完整详情请见**: `deployment/SIMPLE_UPDATE_GUIDE.md`

## 后续步骤:
- 测试修改后的生产配置。
- 验证 Django 服务器是否成功启动。
- 测试音频文件上传功能。
- 确保安全验证按预期工作。
