# JavaScript 文件组织和引用的最佳实践

## 为什么要使用外部 JavaScript 文件

1. **代码分离** - 遵循关注点分离原则：HTML 负责结构，CSS 负责样式，JavaScript 负责行为
2. **缓存优势** - 浏览器可以缓存外部 JS 文件，提高页面加载速度
3. **代码维护** - 更容易维护和更新代码，无需在 HTML 文件中查找和更改
4. **代码重用** - 可以在多个页面中重用相同的 JS 代码

## 在 Django 项目中组织 JavaScript

### 目录结构

```
yourproject/
  ├── static/
  │   ├── js/
  │   │   ├── common.js         # 全站共用的 JS
  │   │   ├── module1.js        # 特定模块的 JS
  │   │   └── module2.js        # 另一个模块的 JS
  │   ├── css/
  │   └── ...
  └── ...
```

### 在模板中引用 JavaScript 文件

Django 模板中引用 JavaScript 文件的方法：

```html
{% load static %}

<!-- 在 <head> 或 </body> 前引入 -->
<script src="{% static 'js/common.js' %}"></script>
<script src="{% static 'js/module1.js' %}"></script>
```

### 模板继承中的最佳实践

在使用模板继承时，可以在基础模板中预留 JS 块：

**base.html**
```html
{% load static %}
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}默认标题{% endblock %}</title>
    {% block base_css %}
    <link rel="stylesheet" href="{% static 'css/base.css' %}">
    {% endblock %}
    {% block extra_css %}{% endblock %}
</head>
<body>
    {% block content %}{% endblock %}
    
    {% block base_js %}
    <!-- 基础 JS 文件，如 jQuery、Bootstrap 等 -->
    <script src="{% static 'js/jquery.min.js' %}"></script>
    <script src="{% static 'js/bootstrap.min.js' %}"></script>
    <script src="{% static 'js/common.js' %}"></script>
    {% endblock %}
    
    {% block extra_js %}{% endblock %}
</body>
</html>
```

**page.html**
```html
{% extends "base.html" %}
{% load static %}

{% block extra_css %}
<link rel="stylesheet" href="{% static 'css/page.css' %}">
{% endblock %}

{% block content %}
<!-- 页面内容 -->
{% endblock %}

{% block extra_js %}
<!-- 首先定义页面特定的变量，供 JS 使用 -->
<script>
    const apiEndpoint = "{% url 'api:endpoint' %}";
    const someValue = {{ value|escapejs }};
</script>
<!-- 然后引入特定页面的 JS 文件 -->
<script src="{% static 'js/page.js' %}"></script>
{% endblock %}
```

## 多页面共享 JavaScript

### 公共组件方法

1. **模块化** - 使用模块化模式组织代码，避免全局变量冲突
   ```javascript
   // common.js
   const MyApp = {
       utils: {
           formatDate: function(date) { /* ... */ },
           validateEmail: function(email) { /* ... */ }
       },
       ui: {
           showModal: function(content) { /* ... */ },
           hideModal: function() { /* ... */ }
       }
   };
   ```

2. **依赖管理** - 对于更复杂的项目，考虑使用 Webpack 或 Rollup 等工具管理依赖

3. **按需加载** - 对于较大的 JS 文件，考虑在需要时动态加载
   ```javascript
   // 动态加载
   function loadScript(url) {
       return new Promise((resolve, reject) => {
           const script = document.createElement('script');
           script.src = url;
           script.onload = resolve;
           script.onerror = reject;
           document.body.appendChild(script);
       });
   }
   
   // 使用
   loadScript('/static/js/large-library.js')
       .then(() => {
           // 脚本加载成功后执行
       });
   ```

## 处理模板变量

将后端数据传递给 JavaScript 的方法：

1. **内联变量** - 在模板中定义 JavaScript 变量
   ```html
   <script>
       const userId = "{{ user.id }}";
       const apiUrls = {
           getData: "{% url 'api:get_data' %}",
           updateProfile: "{% url 'api:update_profile' %}"
       };
   </script>
   <script src="{% static 'js/profile.js' %}"></script>
   ```

2. **数据属性** - 将数据存储在 HTML 属性中
   ```html
   <div id="user-profile" 
        data-user-id="{{ user.id }}"
        data-api-url="{% url 'api:user_data' %}">
       <!-- 内容 -->
   </div>
   ```
   
   ```javascript
   // profile.js
   const profileElement = document.getElementById('user-profile');
   const userId = profileElement.dataset.userId;
   const apiUrl = profileElement.dataset.apiUrl;
   ```

3. **JSON 数据** - 对于更复杂的数据结构
   ```html
   <script>
       const initialData = {{ json_data|safe }};
   </script>
   ```

## 性能优化

1. **放置位置** - 通常将 JS 放在 </body> 标签前，以不阻塞页面渲染
2. **异步加载** - 使用 async 或 defer 属性
   ```html
   <script src="{% static 'js/analytics.js' %}" async></script>
   <script src="{% static 'js/non-critical.js' %}" defer></script>
   ```
3. **最小化和压缩** - 在生产环境使用最小化的 JS 文件
4. **按需加载** - 只加载当前页面需要的 JS

## 调试技巧

1. **使用 Django 设置** - 在开发环境显示未压缩的 JS，生产环境使用压缩版本
   ```python
   # settings.py
   if DEBUG:
       JS_URL = 'js/development/'
   else:
       JS_URL = 'js/production/'
   ```

   ```html
   <script src="{% static JS_URL|add:'app.js' %}"></script>
   ```

2. **使用 webpack** - 在现代项目中，可以使用 webpack 和 django-webpack-loader 