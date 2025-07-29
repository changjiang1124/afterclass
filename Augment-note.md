# Augment Progress Notes

## Current Issue Resolution
- **Problem**: Django server startup failed due to missing `magic` module
- **Root Cause**: The `python-magic` package was listed in requirements.txt but not installed, and the system-level `libmagic` library was missing
- **Solution Applied**:
  1. Installed `python-magic` package using pip
  2. Installed system-level `libmagic` library using Homebrew (`brew install libmagic`)
- **Status**: ✅ Resolved - Dependencies installed successfully

## Magic Library Purpose
The `python-magic` library in this project serves as a crucial security component for audio file validation:

### Primary Functions:
1. **File Type Detection**: Detects real MIME types by reading file headers, not just relying on file extensions
2. **Security Validation**: Prevents file masquerading attacks where malicious files are renamed with audio extensions  
3. **MIME Type Verification**: Ensures uploaded files are genuinely audio files (wav, mp3, m4a, etc.)

### Implementation Location:
- Used in `speak_practice/security.py` within the `AudioSecurityValidator` class
- Part of the comprehensive audio file validation system
- Validates uploaded audio files for the speech practice feature

### Security Benefits:
- Prevents malicious file uploads disguised as audio files
- Provides more reliable file type detection than extension-based checking
- Enhances overall application security for user file uploads
- Works by reading file headers (first 1KB) to detect true file type using libmagic

### Technical Details:
- Requires both Python package (`python-magic`) and system library (`libmagic`)
- On macOS, libmagic is installed via Homebrew
- Used in `validate_mime_type()` method to detect real MIME types
- Falls back to `mimetypes` module if magic detection fails

## Database Configuration Analysis
**User Question**: Confirm if both dev and production environments use SQLite3

### Findings:
- **Development Environment**: ✅ Uses SQLite3 (`tongcove/settings.py`)
  - Database: `db.sqlite3` file in project root
  - Engine: `django.db.backends.sqlite3`

- **Production Environment**: ❌ Uses PostgreSQL (`deployment/production_settings.py`)
  - Engine: `django.db.backends.postgresql` (default)
  - Requires environment variables: DB_NAME, DB_USER, DB_PASSWORD, etc.
  - Service file shows dependency on `postgresql.service`
  - Also configured with Redis cache

### Configuration Details:
- Development uses default `tongcove.settings`
- Production uses `deployment.production_settings` (set in systemd service)
- Production expects `.env.production` file with database credentials
- Current setup follows best practices: SQLite for dev, PostgreSQL for production

## Production Environment SQLite3 Configuration

**User Request**: Make production environment use SQLite3 instead of PostgreSQL

### Changes Made:
1. **Modified `deployment/production_settings.py`**:
   - Changed default database to SQLite3
   - Added option to use PostgreSQL via `USE_POSTGRESQL=true` environment variable
   - Changed cache from Redis to local memory cache
   - Added option to use Redis via `USE_REDIS=true` environment variable

2. **Updated `deployment/tongcove.service`**:
   - Removed PostgreSQL service dependency
   - Simplified service dependencies

3. **Created Configuration Files**:
   - `.env.production.sqlite`: Template for SQLite3 production config
   - `deployment/setup_sqlite_production.sh`: Automated setup script

### Environment Detection Logic:
- **Development**: Uses `tongcove.settings` (default)
  - Hostname check: `socket.gethostname() == 'CJs-MBP-1421.local'`
  - Database: SQLite3 (`db.sqlite3`)

- **Production**: Uses `deployment.production_settings`
  - Set via systemd: `DJANGO_SETTINGS_MODULE=deployment.production_settings`
  - Database: Now SQLite3 (modified from PostgreSQL)
  - URL: afterclass.learnchineseperth.com.au
  - Stack: nginx + gunicorn

### ⚠️ IMPORTANT: Safe Deployment for Existing Production

**User has existing production environment** - created safe update scripts:

#### For New Installations:
- `./deployment/setup_sqlite_production.sh` (Full setup - will overwrite everything)

#### For Existing Production (SAFE):
- `./deployment/update_to_sqlite_safe.sh` (Updates code only, preserves database & config)
- `deployment/DATABASE_MIGRATION_GUIDE.md` (Detailed migration instructions)

#### Safe Update Process:
1. **Backup**: Script automatically creates backup before changes
2. **Code Update**: Only updates application code, preserves:
   - Existing database (`db.sqlite3` or PostgreSQL)
   - Configuration file (`.env.production`)
   - User data and media files
3. **Migration Options**:
   - Keep PostgreSQL: Set `USE_POSTGRESQL=true` in `.env.production`
   - Switch to SQLite3: Follow migration guide for data transfer

## Next Steps:
- Test the modified production configuration
- Verify Django server starts successfully
- Test audio file upload functionality
- Ensure security validation works as expected