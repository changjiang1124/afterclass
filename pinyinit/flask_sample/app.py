from flask import Flask, render_template, request
import markdown
from pypinyin import pinyin, Style, lazy_pinyin
import re
from typing import List, Tuple
import argparse
from pathlib import Path
import jieba

app = Flask(__name__)

class PinyinMarker:
    def __init__(self):
        self.css_style = """
        <style>
            @import url('https://static.zeoseven.com/zsft/5/main/result.css');
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500&display=swap');
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC&display=swap');
            @import url('https://chinese-fonts-cdn.deno.dev/packages/ToneOZ-Pinyin-WenKai/dist/ToneOZ-Pinyin-WenKai-Bold/result.css');
            @import url('https://cdn.jsdelivr.net/npm/cn-fontsource-fz-kai-z-03-regular@1.0.1/font.min.css');

            body {
                font-family:  "FZKai-Z03", "ChillKai";
                font-weight: normal;
            }

            .container {
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            .hanzi-group {
                display: inline-block;
                text-align: center;
                width: 42px;
                margin: 0 2px;
                vertical-align: top;
            }
            .pinyin {
                font-size: 13px;
                height: 20px;
                color: #666;
                margin-top: 1em;
                font-family: 'Poppins', sans-serif;
            }
            .hanzi {
                font-size: 30px;
            }
            .punctuation {
                display: inline-block;
                width: 30px;
                margin: 0 2px;
                text-align: left;
                vertical-align: bottom;
            }
            h1, h2, h3, h4, h5, h6 {
                text-align: center;
                color: blue;
            }
            p {
                line-height: 3;
                margin: 20px 0;  /* 增加段落间距 */
            }
            p:not(h1 + p, h2 + p, h3 + p, h4 + p, h5 + p, h6 + p) {
                text-indent: 60px;  /* 两个汉字的宽度 */
            }
            .polyphonic-char .pinyin {
            }
            /* 确保列表项没有缩进 */
            li {
                text-indent: 0 !important;
            }
            li p {
                text-indent: 0 !important;
            }
            
             /* 使用自定义列表样式，隐藏默认标记 */
   ol {
       list-style-type: none;
       counter-reset: item;
       padding-left: 0;
   }
   ol > li {
       counter-increment: item;
       position: relative;
       padding-left: 2.5em;
   }
   ol > li:before {
       content: counter(item) ".";
       position: absolute;
       left: 0;
       top: 0;
       font-size: 30px;
       text-align: right;
       padding-right: 0.5em;
       padding-top: 1em;
   }
        </style>
        """
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
                polyphonic_class = ' polyphonic-char' if self.is_polyphonic(char) else ''
                
                result += f'<div class="hanzi-group{polyphonic_class}"><div class="pinyin">{py}</div><div class="hanzi">{char}</div></div>'
            else:
                if char.strip():
                    if re.match(r'[a-zA-Z0-9()-]', char):
                        result += f'<span style="vertical-align: bottom;font-size: 30px;">{char}</span>'
                    else:
                        result += f'<div class="hanzi-group"><div class="pinyin"></div><div class="hanzi"><span style="margin: 0 2px;">{char}</span></div></div>'
                        
                    # # 标点符号使用hanzi-group，但拼音部分为空
                    # if re.match(r'[\u3000-\u303f\uff00-\uffef]', char) or char in '""".,!?;:，。！？；：（）':
                    #     result += f'<div class="hanzi-group"><div class="pinyin"></div><div class="hanzi"><span style="margin: 0 2px;">{char}</span></div></div>'
                    # # 对于英文字母和数字，也使用hanzi-group格式，但字体大小与汉字一致
                    # elif re.match(r'[a-zA-Z0-9()-]', char):
                    #     result += f'<div class="hanzi-group"><div class="pinyin"></div><div class="hanzi"><span style="margin: 0 2px;">{char}</span></div></div>'
                    # else:
                    #     result += f'<span style="vertical-align: bottom;font-size: 30px;">{char}</span>'
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
        # 使用BeautifulSoup解析HTML会更可靠，但这里我们使用简单的正则表达式
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
                return f'<p>{indent}{content}</p>'
            return full_tag
        
        # 查找所有段落标签并添加缩进
        processed_html = re.sub(r'<(p)>(.*?)</\1>', add_indent, processed_html)
        
        return processed_html

    def generate_html(self, markdown_content: str) -> str:
        """生成完整的HTML文档"""
        processed_html = self.process_markdown(markdown_content)
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            {self.css_style}
        </head>
        <body>
            <div class="container">
                {processed_html}
            </div>
        </body>
        </html>
        """

# 创建PinyinMarker实例
marker = PinyinMarker()

@app.route('/', methods=['GET', 'POST'])
def index():
    result_html = None
    input_text = ""
    
    if request.method == 'POST':
        input_text = request.form.get('input_text', '')
        if input_text:
            result_html = marker.generate_html(input_text)
    
    return render_template('index.html', result_html=result_html, input_text=input_text)

if __name__ == '__main__':
    app.run(debug=True) 