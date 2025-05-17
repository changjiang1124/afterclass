from django.shortcuts import render
import markdown
import re
from pypinyin import pinyin, Style, lazy_pinyin
import jieba
from typing import List, Tuple

# Create your views here.

class PinyinMarker:
    def __init__(self):
        # 常见多音字词典（可以扩展）
        self.polyphonic_chars = {
            '好': ['hǎo', 'hào'],
            '长': ['cháng', 'zhǎng'],
            '中': ['zhōng', 'zhòng'],
            '行': ['xíng', 'háng'],
            '地': ['dì', 'de'],
            '得': ['dé', 'de', 'děi'],
            '重': ['zhòng', 'chóng'],
            # 可以继续添加更多多音字
        }

    def is_polyphonic(self, char: str) -> bool:
        """判断一个汉字是否是多音字"""
        if char in self.polyphonic_chars:
            return True
            
        # 使用pypinyin获取所有可能的读音
        all_pinyin = pinyin(char, heteronym=True)
        return len(all_pinyin[0]) > 1
        
    def get_pinyin_for_char(self, char: str, context: str = '', index: int = 0) -> str:
        """获取单个汉字的拼音，可选择提供上下文"""
        if not re.match(r'[\u4e00-\u9fff]', char):
            return ''
            
        # 如果有上下文，使用jieba分词来获取更准确的拼音
        if context:
            words = list(jieba.cut(context))
            word = None
            
            # 找出包含当前字符的词
            current_pos = 0
            for w in words:
                if index >= current_pos and index < current_pos + len(w):
                    word = w
                    break
                current_pos += len(w)
                
            if word and len(word) > 1:
                # 对整个词获取拼音，然后取出对应位置的拼音
                word_pinyin = pinyin(word, style=Style.TONE)
                char_index = index - current_pos
                if 0 <= char_index < len(word_pinyin):
                    return word_pinyin[char_index][0]
        
        # 默认方法
        py = pinyin(char, style=Style.TONE)[0][0]
        return py
        
    def get_all_readings(self, char: str) -> List[str]:
        """获取一个汉字的所有可能读音"""
        if char in self.polyphonic_chars:
            return self.polyphonic_chars[char]
            
        if not re.match(r'[\u4e00-\u9fff]', char):
            return []
            
        readings = pinyin(char, heteronym=True, style=Style.TONE)[0]
        return readings

    def process_text(self, text: str) -> str:
        """处理文本，为每个汉字添加拼音标注"""
        result = ""
        
        # 检查是否是列表项的数字开头（如"3."、"4."等）
        match = re.match(r'^(\d+\.)\s*(.*)', text.strip())
        if match:
            # 将数字索引部分作为一个整体放入hanzi-group
            index_part = match.group(1)
            rest_text = match.group(2)
            result += f'<div class="hanzi-group"><div class="pinyin"></div><div class="hanzi"><span style="margin: 0 2px;">{index_part}</span></div></div>'
            # 处理剩余部分
            result += self.process_text(rest_text)
            return result
        
        # 正常处理文本
        for i, char in enumerate(text):
            if re.match(r'[\u4e00-\u9fff]', char):
                py = self.get_pinyin_for_char(char, text, i)
                
                # 如果是多音字，添加一个特殊的类
                # polyphonic_class = ' polyphonic-char' if self.is_polyphonic(char) else ''
                polyphonic_class = '' # 暂时不显示多音字
                
                result += f'<div class="hanzi-group{polyphonic_class}"><div class="pinyin">{py}</div><div class="hanzi">{char}</div></div>'
            else:
                if char.strip():
                    if re.match(r'[a-zA-Z0-9()-]', char):
                        result += f'<span style="vertical-align: bottom;font-size: 30px;">{char}</span>'
                    else:
                        result += f'<div class="hanzi-group"><div class="pinyin"></div><div class="hanzi"><span style="margin: 0 2px;">{char}</span></div></div>'
                else:
                    result += char
        return result

    def process_markdown(self, content: str) -> str:
        """处理Markdown内容"""
        # 预处理：检查是否有手动编号的列表项（如"3. 内容"）
        # 将它们转换为标准的Markdown列表格式
        lines = content.split('\n')
        for i in range(len(lines)):
            # 匹配行首的数字+点+空格
            if re.match(r'^\s*\d+\.\s+', lines[i]):
                # 确保这一行是一个列表项
                lines[i] = re.sub(r'^\s*(\d+\.\s+)', r'\1', lines[i])
        
        # 重新组合内容
        content = '\n'.join(lines)
        
        # 将Markdown转换为HTML
        html = markdown.markdown(content, extensions=['markdown.extensions.nl2br'])
        
        # 处理HTML内容
        processed_html = ""
        # 使用简单的正则表达式分割HTML
        parts = re.split(r'(<[^>]+>|[^<>]+)', html)
        
        for part in parts:
            if not part:  # 跳过空字符串
                continue
            
            if part.startswith('<') and part.endswith('>'):
                # HTML标签，直接添加
                processed_html += part
            else:
                # 文本内容，处理它
                processed_html += self.process_text(part)
        
        # 添加段落缩进（只对普通段落，不对列表项内的段落）
        def add_indent(match):
            full_tag = match.group(0)
            tag = match.group(1)
            content = match.group(2)
            
            # 如果是普通段落且不在列表项内（通过检查前面的HTML来判断）
            if tag == 'p' and not re.search(r'<li[^>]*>(?:(?!</li>).)*$', processed_html[:match.start()], re.DOTALL):
                indent = '<div class="hanzi-group"><div class="pinyin"></div><div class="hanzi"></div></div>' * 2
                return f'<p class="paragraph-with-indent">{indent}{content}</p>'
            return full_tag
        
        # 查找所有段落标签并添加缩进
        processed_html = re.sub(r'<(p)>(.*?)</\1>', add_indent, processed_html)
        
        return processed_html

    def generate_html(self, markdown_content: str) -> str:
        """生成处理后的HTML片段"""
        processed_html = self.process_markdown(markdown_content)
        return processed_html

# 创建PinyinMarker实例
marker = PinyinMarker()

def index(request):
    result_html = None
    input_text = ""
    
    if request.method == 'POST':
        input_text = request.POST.get('input_text', '')
        if input_text:
            result_html = marker.generate_html(input_text)
    
    return render(request, 'pinyinit/index.html', {
        'result_html': result_html,
        'input_text': input_text
    })
