$(document).ready(function() {
    const sourceText = $("#source-text").text().trim();
    let startTime = null;
    let correctChars = 0;
    let incorrectChars = 0;
    let currentPosition = 0;
    
    // 处理拼音显示
    function processPinyinText() {
        if (sourceText.length > 0) {
            // 发送AJAX请求处理拼音
            fetch(processPinyinUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: sourceText
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 更新拼音内容容器
                    $("#pinyin-content-container").html(data.html);
                    
                    // 为每个汉字添加数据索引
                    $(".hanzi-group .hanzi").each(function(index) {
                        $(this).attr('data-index', index);
                        $(this).addClass('char-to-type');
                    });
                    
                    // 设置拼音显示状态
                    const showPinyin = $("#show-pinyin").is(":checked");
                    togglePinyinDisplay(showPinyin);
                } else {
                    $("#pinyin-content-container").html('<div class="alert alert-danger">处理拼音时出错，请重试。</div>');
                }
            })
            .catch(error => {
                console.error('拼音处理错误:', error);
                $("#pinyin-content-container").html('<div class="alert alert-danger">拼音处理发生错误，请刷新页面重试。</div>');
            });
        } else {
            $("#pinyin-content-container").html('<div class="alert alert-warning">没有文本内容可处理。</div>');
        }
    }
    
    // 切换拼音显示
    function togglePinyinDisplay(show) {
        if (show) {
            $(".hanzi-group .pinyin").show();
        } else {
            $(".hanzi-group .pinyin").hide();
        }
    }
    
    // 更新拼音显示的可见性
    $("#show-pinyin").change(function() {
        const showPinyin = $(this).is(":checked");
        togglePinyinDisplay(showPinyin);
    });
    
    // 初始化拼音
    processPinyinText();
    
    // 监听输入，实时更新界面颜色
    $("#typing-input").on('input', function() {
        const currentInput = $(this).val();
        const normalizedSourceText = sourceText.replace(/\r\n/g, '\n');
        const normalizedInput = currentInput.replace(/\r\n/g, '\n');
        
        // 重置所有字符的样式
        $(".char-to-type").removeClass("correct-char error-char current-char");
        
        correctChars = 0;
        incorrectChars = 0;
        
        // 更新字符状态
        for (let i = 0; i < normalizedInput.length; i++) {
            if (i < normalizedSourceText.length) {
                const $char = $(`.hanzi-group .hanzi[data-index="${i}"]`);
                if (normalizedInput[i] === normalizedSourceText[i]) {
                    $char.addClass("correct-char");
                    correctChars++;
                } else {
                    $char.addClass("error-char");
                    incorrectChars++;
                }
            }
        }
        
        // 当前打字位置
        currentPosition = normalizedInput.length;
        if (currentPosition < normalizedSourceText.length) {
            $(`.hanzi-group .hanzi[data-index="${currentPosition}"]`).addClass("current-char");
        }
        
        // 如果完成了全部文本，启用完成按钮
        if (normalizedInput.length >= normalizedSourceText.length) {
            $("#finish-btn").prop('disabled', false);
        } else {
            $("#finish-btn").prop('disabled', true);
        }
    });
    
    // 重置按钮
    $("#reset-btn").click(function() {
        $("#typing-input").val('');
        correctChars = 0;
        incorrectChars = 0;
        currentPosition = 0;
        
        // 重置所有字符的样式
        $(".char-to-type").removeClass("correct-char error-char current-char");
        
        $("#finish-btn").prop('disabled', true);
    });
    
    // 完成按钮
    $("#finish-btn").click(function() {
        const totalTyped = correctChars + incorrectChars;
        const accuracy = totalTyped > 0 ? Math.round((correctChars / totalTyped) * 100) : 100;
        
        alert("恭喜你完成打字练习！\n\n准确率: " + accuracy + "%");
    });
}); 