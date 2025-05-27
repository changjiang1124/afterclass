$(document).ready(function() {
    let generatedTextId = null;
    const toastDuration = 3000; // 通知显示时间（毫秒）
    
    // 显示全局通知消息
    function showToast(message, type) {
        const toast = document.getElementById('global-toast');
        const toastContent = document.getElementById('global-toast-content');
        
        // 移除所有类型
        toast.classList.remove('success', 'error', 'warning');
        // 添加新类型
        toast.classList.add(type);
        
        // 添加适当的图标
        let icon = 'info-circle';
        if (type === 'success') icon = 'check-circle';
        if (type === 'error') icon = 'exclamation-circle';
        if (type === 'warning') icon = 'exclamation-triangle';
        
        // 设置内容
        toastContent.innerHTML = `<i class="fas fa-${icon}"></i> <span>${message}</span>`;
        
        // 显示通知
        toast.classList.add('visible');
        
        // 自动隐藏
        setTimeout(function() {
            toast.classList.remove('visible');
        }, toastDuration);
    }
    
    // 关闭通知按钮点击事件
    document.getElementById('global-toast-close').addEventListener('click', function() {
        document.getElementById('global-toast').classList.remove('visible');
    });
    
    // 删除记录
    function deleteRecord(recordId, element) {
        if (!confirm('Are you sure you want to delete this record?')) {
            return;
        }
        
        console.log('Deleting record:', recordId);
        
        // 获取需要操作的元素
        const deleteIcon = element.querySelector('.delete-record');
        
        // 显示删除中状态
        deleteIcon.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        deleteIcon.style.opacity = 1;
        
        // 获取CSRF令牌
        const csrfToken = getCsrfToken();
        if (!csrfToken) {
            console.error('CSRF token not found, aborting delete operation');
            showToast('Security token not found. Please refresh the page and try again.', 'error');
            deleteIcon.innerHTML = '<i class="fas fa-times"></i>';
            return;
        }
        
        // 使用原生fetch API而不是jQuery的ajax
        fetch(deleteRecordUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ record_id: recordId })
        })
        .then(response => response.json())
        .then(data => {
            console.log('Success response:', data);
            if (data && data.success) {
                // 成功删除，使用原生DOM操作移除元素
                console.log('Removing element from DOM');
                
                // 淡出效果
                element.style.transition = 'opacity 0.3s ease';
                element.style.opacity = '0';
                
                setTimeout(function() {
                    // 移除元素
                    if (element.parentNode) {
                        element.parentNode.removeChild(element);
                    }
                    
                    // 检查是否还有记录
                    const remainingItems = document.querySelectorAll("#history-content .history-item").length;
                    console.log('Remaining items:', remainingItems);
                    if (remainingItems === 0) {
                        document.getElementById("no-history-message").style.display = "block";
                        // make history-content display none
                        document.getElementById("history-content").style.display = "none";
                    }
                    
                    // 显示成功消息
                    showToast('Record deleted successfully', 'success');
                }, 300);
            } else {
                // 删除失败，显示错误消息
                console.error('Delete failed:', data ? data.error : 'Unknown error');
                showToast(data && data.error ? data.error : 'Failed to delete record', 'error');
                // 恢复删除图标
                deleteIcon.innerHTML = '<i class="fas fa-times"></i>';
            }
        })
        .catch(error => {
            console.error('Error details:', error);
            
            // 显示错误消息
            showToast('Error deleting record. Please try again later.', 'error');
            
            // 恢复删除图标
            deleteIcon.innerHTML = '<i class="fas fa-times"></i>';
        });
    }
    
    // 获取CSRF令牌
    function getCsrfToken() {
        console.log('Getting CSRF token');
        
        // 首先尝试从隐藏字段获取
        const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (csrfInput) {
            console.log('CSRF token found in form input');
            return csrfInput.value;
        }
        
        // 尝试从cookie获取
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        
        if (cookieValue) {
            console.log('CSRF token found in cookie');
            return cookieValue;
        }
        
        // 如果cookie中没有，尝试从meta标签获取
        const csrfTokenElement = document.querySelector('meta[name="csrf-token"]');
        if (csrfTokenElement) {
            console.log('CSRF token found in meta tag');
            return csrfTokenElement.getAttribute('content');
        }
        
        console.warn('CSRF token not found!');
        return '';
    }
    
    // 使用事件委托，为所有删除按钮添加点击事件处理程序
    document.addEventListener('click', function(e) {
        // 检查点击的是否是删除按钮
        if (e.target && (e.target.closest('.delete-record') || e.target.classList.contains('delete-record'))) {
            e.preventDefault();
            e.stopPropagation();
            
            // 找到删除按钮元素
            const deleteButton = e.target.closest('.delete-record') || e.target;
            const recordId = deleteButton.getAttribute('data-id');
            console.log('Delete button clicked for record ID:', recordId);
            
            // 找到最近的历史记录项
            const historyItem = deleteButton.closest('.history-item');
            if (!historyItem) {
                console.error('Cannot find parent .history-item element');
                return;
            }
            
            // 调用删除函数
            deleteRecord(recordId, historyItem);
        } 
        // 历史记录项点击事件
        else if (e.target && e.target.closest('.history-item') && !e.target.closest('.delete-record')) {
            const historyItem = e.target.closest('.history-item');
            const url = historyItem.getAttribute('data-url');
            if (url) {
                window.location.href = url;
            }
        }
    });
    
    // 格式化日期时间到本地时区
    function formatDateTime(isoDateTimeStr) {
        const date = new Date(isoDateTimeStr);
        return date.toLocaleDateString('en-AU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        });
    }
    
    // 加载历史记录
    function loadTypingHistory() {
        console.log('Loading typing history...');
        document.getElementById('history-content').innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm text-primary" role="status"><span class="sr-only">Loading...</span></div><p class="mt-2 text-muted">Loading history...</p></div>';
        
        fetch(typingHistoryUrl)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Network response was not ok: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('History data received:', data);
                if (data.success && data.history && data.history.length > 0) {
                    let historyHtml = '<div class="list-group">';
                    
                    data.history.forEach(record => {
                        // 设置徽章颜色和进度条颜色
                        let badgeClass = 'badge-secondary';
                        let progressClass = 'bg-secondary';
                        
                        if (record.is_completed) {
                            badgeClass = 'badge-success';
                            progressClass = 'bg-success';
                        } else if (record.completion > 0) {
                            badgeClass = 'badge-primary';
                            progressClass = 'bg-primary';
                        }
                        
                        // 格式化时间为本地时区
                        const localTime = formatDateTime(record.updated_at_iso);
                        
                        historyHtml += `
                            <div class="list-group-item history-item" data-url="${continuePracticeBaseUrl.replace('0', record.id)}">
                                <div class="d-flex w-100 justify-content-between align-items-center">
                                    <h6 class="mb-1 text-truncate" style="max-width: 70%;">${record.preview}</h6>
                                </div>
                                <div class="d-flex justify-content-between align-items-center mb-1">
                                    <small class="text-muted">${localTime}</small>
                                    <div class="badge-container">
                                        <span class="badge ${badgeClass}">${record.completion}%</span>
                                    </div>
                                </div>
                                <div class="progress">
                                    <div class="progress-bar ${progressClass}" role="progressbar" style="width: ${record.completion}%" 
                                         aria-valuenow="${record.completion}" aria-valuemin="0" aria-valuemax="100"></div>
                                </div>
                                <div class="delete-record" data-id="${record.id}" title="Delete record">
                                    <i class="fas fa-times"></i>
                                </div>
                            </div>
                        `;
                    });
                    
                    historyHtml += '</div>';
                    document.getElementById('history-content').innerHTML = historyHtml;
                    console.log('History loaded, items count:', data.history.length);
                    document.getElementById('no-history-message').style.display = 'none';
                    document.getElementById('history-content').style.display = 'block';
                } else {
                    // 显示无历史记录消息
                    console.log('No history records found');
                    document.getElementById('history-content').innerHTML = '';
                    document.getElementById('no-history-message').style.display = 'block';
                    document.getElementById('history-content').style.display = 'none';
                }
            })
            .catch(error => {
                console.error('Error loading history:', error);
                document.getElementById('history-content').innerHTML = '<div class="text-center text-muted py-3"><i class="fas fa-exclamation-circle"></i><p>Could not load history</p></div>';
                showToast('Failed to load history records. Please try again.', 'error');
            });
    }
    
    // 刷新历史记录按钮点击事件
    document.getElementById('refresh-history-btn').addEventListener('click', function() {
        loadTypingHistory();
    });
    
    // 页面加载时加载历史记录
    loadTypingHistory();
    
    // 加载主题建议
    function loadTopicSuggestions() {
        $("#topic-suggestions").html('<div class="spinner-border spinner-border-sm text-primary mx-auto" role="status"><span class="sr-only">Loading...</span></div>');
        
        fetch(topicSuggestionsUrl)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.topics && data.topics.length > 0) {
                    let topicsHtml = '';
                    data.topics.forEach(topic => {
                        topicsHtml += `<div class="topic-item">${topic}</div>`;
                    });
                    $("#topic-suggestions").html(topicsHtml);
                    
                    // 绑定主题点击事件
                    $(".topic-item").click(function() {
                        const topicText = $(this).text();
                        // 显示生成中状态
                        $(this).addClass('active-topic');
                        $(".topic-item").prop('disabled', true);
                        $("#confirm-generate-btn").prop('disabled', true)
                                                 .addClass('btn-generating')
                                                 .html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...');
                        
                        // 获取当前选中的文本长度
                        const length = $("input[name='textLength']:checked").val();
                        
                        // 直接发送请求生成内容
                        fetch(generateAiTextUrl, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                instruction: `Generate content about ${topicText}`,
                                length: length
                            })
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                $("#chinese-text").val(data.text);
                                generatedTextId = data.id;
                                // Clear translation when new text is generated
                                $(".translation-container").hide();
                                checkTextareaContent();
                                $("#generateModal").modal('hide');
                            } else {
                                // 显示错误信息
                                $("#instruction-feedback")
                                    .html(`<div class="alert alert-danger">${data.error}</div>`)
                                    .show();
                            }
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            $("#instruction-feedback")
                                .html('<div class="alert alert-danger">生成过程中出现错误，请重试</div>')
                                .show();
                        })
                        .finally(() => {
                            $(".topic-item").removeClass('active-topic');
                            $(".topic-item").prop('disabled', false);
                            $("#confirm-generate-btn").prop('disabled', false)
                                                     .removeClass('btn-generating')
                                                     .html('<i class="fas fa-wand-magic-sparkles mr-1"></i> Generate');
                        });
                    });
                } else {
                    $("#topic-suggestions").html('<div class="text-muted small">无法加载主题建议，请手动输入或刷新重试。</div>');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                $("#topic-suggestions").html('<div class="text-muted small">加载主题建议失败，请手动输入或刷新重试。</div>');
            });
    }
    
    // 刷新主题按钮点击事件
    $("#refresh-topics-btn").click(function() {
        loadTopicSuggestions();
    });
    
    // 模态框显示时加载主题建议
    $("#generateModal").on('shown.bs.modal', function() {
        loadTopicSuggestions();
    });
    
    // Check if textarea has content, decide whether to show "Start Practice" and "Translate" buttons
    function checkTextareaContent() {
        if ($("#chinese-text").val().trim().length > 0) {
            $("#start-practice-container").show();
            $("#translate-btn").show();
        } else {
            $("#start-practice-container").hide();
            $("#translate-btn").hide();
            $(".translation-container").hide();
        }
    }
    
    // Listen for text input changes
    $("#chinese-text").on('input', function() {
        checkTextareaContent();
        // 当用户手动修改文本内容时，重置generatedTextId
        generatedTextId = null;
    });
    
    // Translate button click event
    $("#translate-btn").click(function() {
        const text = $("#chinese-text").val().trim();
        
        if (text.length > 0) {
            // Show loading state
            $(this).prop('disabled', true)
                   .addClass('btn-translating')
                   .html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Translating...');
            $("#translation-content").html('<div class="text-center"><div class="spinner-border text-primary" role="status"><span class="sr-only">Loading...</span></div><p class="mt-2 text-muted">Translating...</p></div>');
            $(".translation-container").show();
            
            // Send AJAX request to translate text
            fetch(translateTextUrl, {
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
                    $("#translation-content").html(data.translation);
                } else {
                    // Show error message
                    $("#translation-content").html(`<div class="alert alert-danger">${data.error}</div>`);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                $("#translation-content").html('<div class="alert alert-danger">Translation process failed, please try again</div>');
            })
            .finally(() => {
                $("#translate-btn").prop('disabled', false)
                                  .removeClass('btn-translating')
                                  .html('<i class="fas fa-language mr-1"></i> Translate');
            });
        }
    });
    
    // Close translation button click event
    $("#close-translation-btn").click(function() {
        $(".translation-container").hide();
    });
    
    // Open generate text modal
    $("#generate-btn").click(function() {
        // Clear feedback and instruction input
        $("#instruction-input").val('');
        $("#instruction-feedback").hide().html('');
        
        $("#generateModal").modal('show');
    });
    
    // Confirm generate text button
    $("#confirm-generate-btn").click(function() {
        const instruction = $("#instruction-input").val().trim();
        const length = $("input[name='textLength']:checked").val();
        
        // Validate instruction not empty
        if (!instruction) {
            $("#instruction-feedback")
                .html('<div class="alert alert-warning">请输入生成指令</div>')
                .show();
            return;
        }
        
        // Show loading state
        $(this).prop('disabled', true)
               .addClass('btn-generating')
               .html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...');
        $("#instruction-feedback").hide().html('');
        
        // Send AJAX request to generate text
        fetch(generateAiTextUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                instruction: instruction,
                length: length
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                $("#chinese-text").val(data.text);
                generatedTextId = data.id;
                // Clear translation when new text is generated
                $(".translation-container").hide();
                checkTextareaContent();
                $("#generateModal").modal('hide');
            } else {
                // Show error message
                $("#instruction-feedback")
                    .html(`<div class="alert alert-danger">${data.error}</div>`)
                    .show();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            $("#instruction-feedback")
                .html('<div class="alert alert-danger">生成过程中出现错误，请重试</div>')
                .show();
        })
        .finally(() => {
            $("#confirm-generate-btn").prop('disabled', false)
                                     .removeClass('btn-generating')
                                     .html('<i class="fas fa-wand-magic-sparkles mr-1"></i> Generate');
        });
    });
    
    // Start practice button
    $("#start-practice-btn").click(function() {
        const text = $("#chinese-text").val().trim();
        if (text.length > 0) {
            // Build URL with text content
            let url = practiceUrl + '?';
            
            if (generatedTextId) {
                url += `text_id=${generatedTextId}`;
            } else {
                url += `text=${encodeURIComponent(text)}`;
            }
            
            window.location.href = url;
        } else {
            alert('Please enter or generate text first');
        }
    });
    
    // Check textarea on page load
    checkTextareaContent();
}); 