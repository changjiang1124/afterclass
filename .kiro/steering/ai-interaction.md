# AI Interaction Guidelines

## Language Preferences

### Response Language
- **Default explanations**: Provide explanations in Simplified Chinese (简体中文)
- **Technical discussions**: Use Simplified Chinese for concept explanations
- **Code comments**: Write code comments in Simplified Chinese when appropriate
- **Specs writing**: Write specs in Simmplifed Chinese

### UI and Code Language
- **User-facing text**: Use Australian English spelling and terminology
- **Variable names**: Use English (snake_case for Python, camelCase for JavaScript)
- **Database fields**: Use English field names
- **URL patterns**: Use English slugs and paths
- **Error messages**: Display in English (Australian spelling)
- **Form labels**: Use English for form fields

## Communication Style
- Be patient and educational, suitable for language learners
- Explain technical concepts in simple terms
- Provide context for Django/Python concepts when explaining in Chinese
- Use examples relevant to Chinese language learning context

## Code Documentation
- Function docstrings: English
- Inline comments: Simplified Chinese for complex logic explanations
- README files: English
- User documentation: Simplified Chinese

## Examples

### Good Response Pattern:
```
这个Django视图函数用于处理用户登录请求。(This Django view function handles user login requests.)

```python
def user_login(request):
    """Handle user authentication for the Chinese learning platform."""
    # 检查请求方法是否为POST (Check if request method is POST)
    if request.method == 'POST':
        # 处理登录逻辑 (Handle login logic)
        pass
```

### UI Text Examples:
- Button text: "Submit Assignment" (not "Submit Task")
- Error messages: "Please enter a valid email address" (Australian spelling)
- Success messages: "Your profile has been updated successfully"
```