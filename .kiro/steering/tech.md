# Technology Stack

## Framework & Backend
- **Django 5.1** - Python web framework
- **Python 3.x** - Primary programming language
- **SQLite** - Development database
- **Gunicorn** - WSGI HTTP Server for production

## Frontend Technologies
- **Bootstrap 4.6.0** - CSS framework for responsive design
- **jQuery 3.5.1** - JavaScript library
- **Font Awesome 5.15.3** - Icon library
- **Google Fonts** - Noto Sans SC, Noto Serif SC, Roboto

## Key Dependencies
- **OpenAI API** - AI-powered features and chatbots
- **Google Cloud Text-to-Speech** - TTS functionality
- **django-ckeditor-5** - Rich text editor
- **python-dotenv** - Environment variable management
- **pypinyin** - Pinyin conversion
- **jieba** - Chinese text segmentation
- **qrcode** - QR code generation
- **Pillow** - Image processing

## Development Tools
- **Virtual Environment** (`.venv/`) - Python dependency isolation
- **Environment Variables** (`.env`) - Configuration management

## Common Commands

### Development Setup
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Database Management
```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create admin user (custom command)
python manage.py createadmin
```

### Static Files
```bash
# Collect static files for production
python manage.py collectstatic
```

### Custom Management Commands
```bash
# Update daily statistics
python manage.py update_daily_stats
```

## Configuration Notes
- Uses hostname detection for environment-specific settings
- Logging configured for namegen statistics
- Cache configuration for IP location data
- Custom authentication backend for case-insensitive login