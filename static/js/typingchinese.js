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
    
    // 更新进度条
    function updateProgressBar(current, total) {
        const percentage = Math.min(100, Math.round((current / total) * 100));
        $("#typing-progress").css("width", percentage + "%");
        $("#typing-progress").attr("aria-valuenow", percentage);
        $("#typing-progress").text(percentage + "%");
        
        // 根据进度更新进度条颜色
        if (percentage < 30) {
            $("#typing-progress").removeClass("bg-warning bg-success").addClass("bg-info");
        } else if (percentage < 70) {
            $("#typing-progress").removeClass("bg-info bg-success").addClass("bg-warning");
        } else {
            $("#typing-progress").removeClass("bg-info bg-warning").addClass("bg-success");
        }
    }
    
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
        
        // 更新进度条
        updateProgressBar(currentPosition, normalizedSourceText.length);
        
        // 当输入结束时显示提示
        if (normalizedInput.length >= normalizedSourceText.length) {
            const totalTyped = correctChars + incorrectChars;
            const accuracy = totalTyped > 0 ? Math.round((correctChars / totalTyped) * 100) : 100;
            
            // 如果尚未显示成功提示，则显示
            if (!$("#completion-alert").length) {
                const alertHtml = `
                    <div id="completion-alert" class="alert alert-success alert-dismissible fade show mt-3" role="alert">
                        <strong>恭喜你完成打字练习!</strong> 准确率: ${accuracy}%
                        <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                            <span aria-hidden="true">&times;</span>
                        </button>
                    </div>
                `;
                $(".typing-container").append(alertHtml);
            }
        } else {
            // 如果还在输入中，移除已有的成功提示
            $("#completion-alert").remove();
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
        
        // 重置进度条
        updateProgressBar(0, sourceText.length);
        
        // 移除完成提示
        $("#completion-alert").remove();
    });
}); 