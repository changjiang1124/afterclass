$(document).ready(function() {
    const sourceText = $("#source-text").text().trim();
    let startTime = null;
    let correctChars = 0;
    let incorrectChars = 0;
    let currentPosition = 0;
    let chineseCharIndices = []; // 存储中文字符的索引位置
    let displayedCharsMap = {}; // 存储显示的字符与原始文本索引的映射
    let isCompleted = false; // 是否完成练习
    let saveTimeout = null; // 保存进度的计时器
    const recordId = $("#record-id").val(); // 获取记录ID
    
    // 显示自动保存状态
    function showSaveStatus() {
        $(".autosave-status").fadeIn(300);
        setTimeout(() => {
            $(".autosave-status").fadeOut(500);
        }, 2000);
    }
    
    // 自动保存进度
    function saveProgress() {
        // 如果没有记录ID，则不保存
        if (!recordId) return;
        
        // 清除之前的计时器
        if (saveTimeout) {
            clearTimeout(saveTimeout);
        }
        
        // 设置新的计时器 (3秒后保存)
        saveTimeout = setTimeout(() => {
            const currentInput = $("#typing-input").val();
            
            // 获取显示的汉字总数
            const totalChineseChars = $(".hanzi-group .hanzi").filter(function() {
                return isChinese($(this).text().trim());
            }).length;
            
            // 确保正确字符不超过总字符数
            const safeCorrectChars = Math.min(correctChars, totalChineseChars);
            
            console.log(`Saving progress: correct=${safeCorrectChars}, total=${totalChineseChars}, completed=${isCompleted}`);
            
            fetch(saveProgressUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    record_id: recordId,
                    current_input: currentInput,
                    correct_chars: safeCorrectChars,
                    is_completed: isCompleted
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showSaveStatus();
                }
            })
            .catch(error => {
                console.error('保存进度错误:', error);
            });
        }, 3000);
    }
    
    // 保存在页面离开时
    $(window).on('beforeunload', function() {
        // 如果有记录ID并且输入框不为空，则立即保存
        if (recordId && $("#typing-input").val().trim().length > 0) {
            // 获取显示的汉字总数
            const totalChineseChars = $(".hanzi-group .hanzi").filter(function() {
                return isChinese($(this).text().trim());
            }).length;
            
            // 确保正确字符不超过总字符数
            const safeCorrectChars = Math.min(correctChars, totalChineseChars);
            
            navigator.sendBeacon(saveProgressUrl, JSON.stringify({
                record_id: recordId,
                current_input: $("#typing-input").val(),
                correct_chars: safeCorrectChars,
                is_completed: isCompleted
            }));
        }
    });
    
    // 检查字符是否为汉字（只检测汉字，忽略所有标点）
    function isChinese(char) {
        // 只检测基本汉字范围 \u4e00-\u9fa5
        return /[\u4e00-\u9fa5]/.test(char);
    }
    
    // 提取文本中的中文字符及其索引
    function extractChineseIndices(text) {
        const indices = [];
        for (let i = 0; i < text.length; i++) {
            if (isChinese(text[i])) {
                indices.push(i);
            }
        }
        return indices;
    }
    
    // 处理拼音显示
    function processPinyinText() {
        if (sourceText.length > 0) {
            // 获取中文字符索引
            chineseCharIndices = extractChineseIndices(sourceText);
            
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
                    
                    // 为每个汉字添加数据索引并创建显示字符与原始索引的映射
                    let displayIndex = 0;
                    $(".hanzi-group .hanzi").each(function() {
                        const text = $(this).text().trim();
                        if (isChinese(text)) {
                            $(this).attr('data-index', displayIndex);
                            $(this).addClass('char-to-type');
                            
                            // 在原始文本中查找这个字符
                            for (let i = 0; i < sourceText.length; i++) {
                                if (sourceText[i] === text && !Object.values(displayedCharsMap).includes(i)) {
                                    displayedCharsMap[displayIndex] = i;
                                    break;
                                }
                            }
                            displayIndex++;
                        }
                    });
                    
                    // 设置拼音显示状态
                    const showPinyin = $("#show-pinyin").is(":checked");
                    togglePinyinDisplay(showPinyin);
                    
                    // 如果有保存的输入内容，则恢复
                    const savedInput = $("#saved-input").val();
                    if (savedInput && savedInput.length > 0) {
                        $("#typing-input").val(savedInput);
                        // 触发input事件以更新UI
                        $("#typing-input").trigger('input');
                    }
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
    
    // 更新进度条 - 只计算汉字的进度
    function updateProgressBar(typedChineseCount, totalChineseChars) {
        const percentage = Math.min(100, Math.round((typedChineseCount / totalChineseChars) * 100));
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
        let typedChineseCount = 0;
        
        // 获取显示的汉字及其对应元素
        const displayedChars = [];
        const displayedElements = [];
        $(".hanzi-group .hanzi").each(function() {
            const text = $(this).text().trim();
            if (isChinese(text)) {
                displayedChars.push(text);
                displayedElements.push($(this));
            }
        });
        
        // 从输入中提取汉字
        let inputText = "";
        for (let i = 0; i < normalizedInput.length; i++) {
            if (isChinese(normalizedInput[i])) {
                inputText += normalizedInput[i];
            }
        }
        
        // 逐字符比较输入的汉字和显示的汉字
        for (let i = 0; i < Math.min(inputText.length, displayedChars.length); i++) {
            if (inputText[i] === displayedChars[i]) {
                displayedElements[i].addClass("correct-char");
                correctChars++;
            } else {
                displayedElements[i].addClass("error-char");
                incorrectChars++;
            }
            typedChineseCount++;
        }
        
        // 找到下一个要输入的汉字位置
        if (typedChineseCount < displayedChars.length) {
            displayedElements[typedChineseCount].addClass("current-char");
        }
        
        // 更新进度条 - 只计算汉字
        updateProgressBar(typedChineseCount, displayedChars.length);
        
        // 当输入所有汉字后显示提示
        if (typedChineseCount >= displayedChars.length) {
            const totalTyped = correctChars + incorrectChars;
            const accuracy = totalTyped > 0 ? Math.round((correctChars / totalTyped) * 100) : 100;
            isCompleted = true; // 标记为已完成
            
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
            isCompleted = false; // 标记为未完成
        }
        
        // 触发自动保存
        saveProgress();
    });
    
    // 重置按钮
    $("#reset-btn").click(function() {
        $("#typing-input").val('');
        correctChars = 0;
        incorrectChars = 0;
        currentPosition = 0;
        isCompleted = false;
        
        // 重置所有字符的样式
        $(".char-to-type").removeClass("correct-char error-char current-char");
        
        // 重置进度条 - 使用汉字数量
        const totalChineseChars = $(".hanzi-group .hanzi").length;
        updateProgressBar(0, totalChineseChars);
        
        // 移除完成提示
        $("#completion-alert").remove();
        
        // 保存重置状态
        saveProgress();
    });

    // Text-to-Speech功能
    let currentAudio = null; // 当前播放的音频对象
    let audioCache = {}; // 音频缓存对象

    // 生成缓存键
    function generateCacheKey(text) {
        // 使用简单的哈希函数生成缓存键
        let hash = 0;
        if (text.length === 0) return hash.toString();
        for (let i = 0; i < text.length; i++) {
            const char = text.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // 转换为32位整数
        }
        return hash.toString();
    }

    // 从本地存储加载音频缓存
    function loadAudioCache() {
        try {
            const cached = localStorage.getItem('tts_audio_cache');
            if (cached) {
                audioCache = JSON.parse(cached);
            }
        } catch (error) {
            console.error('Error loading audio cache:', error);
            audioCache = {};
        }
    }

    // 保存音频到本地存储
    function saveAudioToCache(cacheKey, audioData) {
        try {
            audioCache[cacheKey] = {
                data: audioData,
                timestamp: Date.now()
            };
            
            // 限制缓存大小，删除超过24小时的缓存或超过10个条目的旧缓存
            const maxAge = 24 * 60 * 60 * 1000; // 24小时
            const maxEntries = 10;
            const now = Date.now();
            
            // 删除过期的缓存
            Object.keys(audioCache).forEach(key => {
                if (now - audioCache[key].timestamp > maxAge) {
                    delete audioCache[key];
                }
            });
            
            // 如果缓存条目过多，删除最老的
            const entries = Object.entries(audioCache);
            if (entries.length > maxEntries) {
                entries.sort((a, b) => a[1].timestamp - b[1].timestamp);
                const toDelete = entries.slice(0, entries.length - maxEntries);
                toDelete.forEach(([key]) => delete audioCache[key]);
            }
            
            localStorage.setItem('tts_audio_cache', JSON.stringify(audioCache));
        } catch (error) {
            console.error('Error saving to cache:', error);
        }
    }

    // 从缓存获取音频
    function getAudioFromCache(cacheKey) {
        const cached = audioCache[cacheKey];
        if (cached) {
            const maxAge = 24 * 60 * 60 * 1000; // 24小时
            if (Date.now() - cached.timestamp < maxAge) {
                return cached.data;
            } else {
                // 删除过期缓存
                delete audioCache[cacheKey];
                try {
                    localStorage.setItem('tts_audio_cache', JSON.stringify(audioCache));
                } catch (error) {
                    console.error('Error updating cache:', error);
                }
            }
        }
        return null;
    }

    // 播放音频
    function playAudio(audioData) {
        try {
            // 停止当前播放的音频
            if (currentAudio) {
                currentAudio.pause();
                currentAudio = null;
            }

            // 创建Blob和音频URL
            const audioBlob = new Blob([new Uint8Array(atob(audioData).split('').map(char => char.charCodeAt(0)))], {
                type: 'audio/mpeg'
            });
            const audioUrl = URL.createObjectURL(audioBlob);
            
            // 创建新的音频对象并播放
            currentAudio = new Audio(audioUrl);
            
            currentAudio.onended = function() {
                URL.revokeObjectURL(audioUrl);
                currentAudio = null;
                updateTTSButton('ready');
            };
            
            currentAudio.onerror = function() {
                URL.revokeObjectURL(audioUrl);
                currentAudio = null;
                updateTTSButton('error');
                console.error('Error playing audio');
            };
            
            currentAudio.play().then(() => {
                updateTTSButton('playing');
            }).catch(error => {
                console.error('Error playing audio:', error);
                updateTTSButton('error');
            });
            
        } catch (error) {
            console.error('Error creating audio:', error);
            updateTTSButton('error');
        }
    }

    // 更新TTS按钮状态
    function updateTTSButton(state) {
        const button = $("#tts-btn");
        const icon = button.find("i");
        
        button.prop('disabled', false);
        $(".tts-status").hide();
        
        switch (state) {
            case 'loading':
                button.prop('disabled', true);
                icon.removeClass().addClass("fas fa-spinner fa-spin mr-1");
                button.find('.btn-text').text(' Generating...');
                $(".tts-status").show();
                break;
            case 'playing':
                icon.removeClass().addClass("fas fa-pause mr-1");
                button.find('.btn-text').text(' Playing...');
                break;
            case 'ready':
                icon.removeClass().addClass("fas fa-volume-up mr-1");
                button.find('.btn-text').text(' Listen');
                break;
            case 'error':
                icon.removeClass().addClass("fas fa-exclamation-triangle mr-1");
                button.find('.btn-text').text(' Error');
                setTimeout(() => updateTTSButton('ready'), 3000);
                break;
        }
    }

    // TTS按钮点击事件
    $("#tts-btn").click(function() {
        const text = sourceText.trim();
        
        if (!text) {
            alert('No text available for speech synthesis');
            return;
        }

        // 如果当前有音频在播放，则停止播放
        if (currentAudio && !currentAudio.paused) {
            currentAudio.pause();
            currentAudio = null;
            updateTTSButton('ready');
            return;
        }

        const cacheKey = generateCacheKey(text);
        const cachedAudio = getAudioFromCache(cacheKey);
        
        if (cachedAudio) {
            // 使用缓存的音频
            console.log('Using cached audio');
            playAudio(cachedAudio);
        } else {
            // 需要生成新的音频
            console.log('Generating new audio');
            updateTTSButton('loading');
            
            fetch(textToSpeechUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: text
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 保存到缓存
                    saveAudioToCache(cacheKey, data.audio_data);
                    // 播放音频
                    playAudio(data.audio_data);
                } else {
                    console.error('TTS Error:', data.error);
                    updateTTSButton('error');
                    alert('Failed to generate speech: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('TTS Request Error:', error);
                updateTTSButton('error');
                alert('Failed to generate speech. Please check your internet connection.');
            });
        }
    });

    // 初始化
    loadAudioCache();
    updateTTSButton('ready');

    // 更新按钮文本结构以支持动态更新
    $("#tts-btn").html('<i class="fas fa-volume-up mr-1"></i><span class="btn-text"> Listen</span>');
}); 