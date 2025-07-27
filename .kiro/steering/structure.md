# Project Structure

## Django Project Layout
```
tongcove/                 # Main Django project directory
├── settings.py          # Django configuration
├── urls.py             # Root URL configuration
├── views.py            # Project-level views (TTS endpoint)
└── wsgi.py/asgi.py     # WSGI/ASGI configuration
```

## Django Applications
Each app follows standard Django structure with models, views, templates, and URLs:

### Core Learning Apps
- **`accounts/`** - User authentication, student profiles, custom backends
- **`dashboard/`** - Main dashboard with feature navigation
- **`assignments/`** - Learning assignments and quizzes
- **`stories/`** - Reading comprehension with interactive stories
- **`chatbots/`** - AI-powered conversational learning
- **`speak_practice/`** - Speaking practice scenarios
- **`typingchinese/`** - Chinese character typing practice
- **`pinyinit/`** - Pinyin conversion tools
- **`namegen/`** - Chinese name generator with statistics

## Static Assets Organization
```
static/
├── css/                 # Application-specific stylesheets
├── js/                  # JavaScript files
├── images/              # Global images (logo, favicon, etc.)
└── namegen/             # App-specific static files
    ├── css/
    └── images/

staticfiles/             # Collected static files for production
```

## Templates Structure
```
templates/
├── base.html           # Base template with navigation
└── 404.html           # Custom error page

{app}/templates/{app}/   # App-specific templates
├── list.html           # List views
├── detail.html         # Detail views
└── form.html           # Form views
```

## Key Directories
- **`logs/`** - Application logs (namegen statistics)
- **`docs/`** - Documentation files
- **`.venv/`** - Python virtual environment
- **`.kiro/`** - Kiro AI assistant configuration

## Django App Conventions

### Models
- Use verbose_name for internationalization
- Include created_at/updated_at timestamps
- Follow Django naming conventions (PascalCase)
- Use choices for predefined options

### Views
- Prefer class-based views for CRUD operations
- Use function-based views for simple logic
- Include proper authentication decorators
- Handle both GET and POST requests appropriately

### URLs
- Use app namespaces (`app_name = 'appname'`)
- Name all URL patterns for reverse lookups
- Group related URLs in app-specific url.py files

### Templates
- Extend from `base.html`
- Use `{% load static %}` for static files
- Include proper block structure (content, extra_css, extra_js)
- Follow Bootstrap 4 component patterns

## File Naming Patterns
- Python files: `snake_case.py`
- Templates: `snake_case.html`
- Static files: `kebab-case.css`, `camelCase.js`
- Model classes: `PascalCase`
- View functions: `snake_case`

## Database Migrations
- Located in `{app}/migrations/`
- Auto-generated with descriptive names
- Include `__init__.py` files