#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PIL import Image, ImageDraw, ImageFont
import sys

def test_fonts():
    """测试字体加载和中文字符渲染"""
    print("Font Debug Test")
    print("=" * 50)
    
    # 测试字体路径
    font_paths = [
        '/usr/share/fonts/truetype/arphic/ukai.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
        '/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    ]
    
    working_fonts = []
    
    for font_path in font_paths:
        print(f"\nTesting font: {font_path}")
        if os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, 60)
                working_fonts.append((font_path, font))
                print(f"✓ Font loaded successfully")
                
                # 测试渲染中文字符
                img = Image.new('RGB', (300, 200), 'white')
                draw = ImageDraw.Draw(img)
                test_chars = "王伟"
                draw.text((50, 50), test_chars, font=font, fill='black')
                
                # 保存测试图片
                filename = f"test_font_{os.path.basename(font_path).replace('.ttc', '')}.png"
                img.save(filename)
                print(f"✓ Test image saved: {filename}")
                
            except Exception as e:
                print(f"✗ Failed to load font: {e}")
        else:
            print(f"✗ Font file not found")
    
    print(f"\n{len(working_fonts)} fonts are working")
    
    if working_fonts:
        # 创建综合测试图片
        print("\nCreating comprehensive test...")
        
        width, height = 800, 1200
        img = Image.new('RGB', (width, height), '#f0f0f0')
        draw = ImageDraw.Draw(img)
        
        # 使用第一个可用字体
        font_path, font_large = working_fonts[0]
        font_medium = ImageFont.truetype(font_path, 80)
        font_small = ImageFont.truetype(font_path, 50)
        
        print(f"Using font: {font_path}")
        
        # 测试垂直文字排列
        chinese_name = "王伟"
        char_list = list(chinese_name)
        char_height = 180
        start_y = 200
        name_x = width // 2 - 80
        
        # 绘制标题
        draw.text((50, 50), "Font Test - 字体测试", font=font_medium, fill='#000000')
        
        # 垂直绘制字符
        for i, char in enumerate(char_list):
            char_y = start_y + i * char_height
            draw.text((name_x, char_y), char, font=font_large, fill='#000000')
            print(f"Drawing '{char}' at ({name_x}, {char_y})")
        
        # 绘制拼音
        pinyin_parts = ["wáng", "wěi"]
        pinyin_x = name_x + 180
        for i, pinyin_part in enumerate(pinyin_parts):
            pinyin_y = start_y + i * char_height + 40
            draw.text((pinyin_x, pinyin_y), pinyin_part, font=font_small, fill='#333333')
        
        # 绘制含义
        meanings = ["king, surname", "great, mighty"]
        meaning_x = name_x - 280
        for i, meaning in enumerate(meanings):
            meaning_y = start_y + i * char_height + 40
            draw.text((meaning_x, meaning_y), meaning, font=font_small, fill='#444444')
        
        # 保存综合测试图片
        img.save('comprehensive_test.png')
        print("✓ Comprehensive test image saved: comprehensive_test.png")
        
        return True
    else:
        print("✗ No working fonts found!")
        return False

if __name__ == "__main__":
    success = test_fonts()
    sys.exit(0 if success else 1) 