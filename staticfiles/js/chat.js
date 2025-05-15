$(document).ready(function() {
    var chatBox = $('#chat-box');
    var messageInput = $('#message');
    var submitButton = $('#chat-form button[type="submit"]');

    function scrollToBottom() {
        chatBox.scrollTop(chatBox[0].scrollHeight);
    }

    let currentAudio = null;
    let currentButton = null;

    function speakMessage(text, button) {
        // 如果有正在播放的音频，停止它
        if (currentAudio) {
            currentAudio.pause();
            $(currentButton).removeClass('speaking');
        }

        // 如果点击的是当前正在播放的按钮，只需停止播放
        if (button === currentButton) {
            currentAudio = null;
            currentButton = null;
            return;
        }

        // 设置新的当前按钮
        currentButton = button;

        // 重置所有按钮状态
        $('.speak-button').removeClass('speaking requesting');

        // 设置当前按钮状态
        $(button).addClass('requesting');

        $.ajax({
            url: '/chatbots/tts/',
            method: 'POST',
            data: {
                text: text,
                csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').val()
            },
            xhrFields: {
                responseType: 'blob'
            },
            success: function(data) {
                $(button).removeClass('requesting').addClass('speaking');
                currentAudio = new Audio(URL.createObjectURL(data));
                currentAudio.play();
                currentAudio.onended = function() {
                    $(button).removeClass('speaking');
                    currentAudio = null;
                    currentButton = null;
                };
            },
            error: function(jqXHR, textStatus, errorThrown) {
                $(button).removeClass('requesting speaking');
                console.error("Error in text-to-speech:", textStatus, errorThrown);
                alert("语音合成失败，请稍后再试。");
                currentButton = null;
            }
        });
    }

    // 使用事件委托来处理speak按钮的点击
    $(document).on('click', '.speak-button', function(e) {
        e.preventDefault();
        const messageText = $(this).closest('.message').find('.message-text').text().trim();
        if (messageText) {
            speakMessage(messageText, this);
        } else {
            console.error("Empty message text");
        }
    });

    function addMessage(sender, content, isAI = false) {
        var messageClass = isAI ? 'ai' : 'user';
        var messageHtml = '<div class="message ' + messageClass + '">' +
            '<span class="message-text">' + content + '</span>';
        
        if (isAI) {
            messageHtml += '<button class="btn btn-sm btn-outline-secondary ml-2 speak-button">' +
                '<i class="fas fa-volume-up"></i>' +
                '<span class="status-dot"></span></button>';
        }
        
        messageHtml += '</div>';

        var messageElement = $(messageHtml);
        chatBox.append(messageElement);
        scrollToBottom();
    }

    $('#chat-form').on('submit', function(event) {
        event.preventDefault();
        
        var message = messageInput.val().trim();
        if (!message) return;

        messageInput.prop('disabled', true);
        submitButton.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Sending...');

        addMessage('You', message);
        messageInput.val('');

        var placeholderElement = $('<div>')
            .addClass('message ai placeholder')
            .html('<span>Thinking...</span>');
        chatBox.append(placeholderElement);
        scrollToBottom();

        $.ajax({
            url: window.location.href,
            type: 'POST',
            data: {
                message: message,
                csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').val()
            },
            success: function(response) {
                placeholderElement.remove();
                addMessage('AI', response.response, true);
            },
            error: function() {
                placeholderElement.remove();
                addMessage('System', 'Oops, something went wrong. Please try again later.', true);
            },
            complete: function() {
                messageInput.prop('disabled', false).focus();
                submitButton.prop('disabled', false).text('Send');
                scrollToBottom();
            }
        });
    });

    scrollToBottom();
});
