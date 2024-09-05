$(document).ready(function() {
    var chatBox = $('#chat-box');
    var messageInput = $('#message');
    var submitButton = $('#chat-form button[type="submit"]');

    function scrollToBottom() {
        chatBox.scrollTop(chatBox[0].scrollHeight);
    }

    function speakMessage(text) {
        const utterance = new SpeechSynthesisUtterance(text);
        
        // 检测语言
        if (/[\u4e00-\u9fa5]/.test(text)) {
            utterance.lang = 'zh-CN'; // 中文
        } else {
            utterance.lang = 'en-US'; // 英文
        }
        
        // 设置语速和音调
        utterance.rate = 1.0; // 正常语速
        utterance.pitch = 1.0; // 正常音调
        
        // 获取可用的语音
        let voices = speechSynthesis.getVoices();
        
        // 选择合适的语音
        let voice = voices.find(voice => voice.lang === utterance.lang && voice.name.includes('Google'));
        if (voice) {
            utterance.voice = voice;
        }
        
        speechSynthesis.speak(utterance);
    }

    function addSpeakButton(messageElement) {
        const speakButton = $('<button>')
            .addClass('btn btn-sm btn-outline-secondary ml-2')
            .html('<i class="fas fa-volume-up"></i>')
            .click(function() {
                const messageText = messageElement.find('span.message-text').text();
                speakMessage(messageText);
            });
    }

    $(document).on('click', '.speak-button', function() {
        const messageText = $(this).siblings('.message-text').text();
        speakMessage(messageText);
    });

    function addMessage(sender, content, isAI = false) {
        var messageClass = isAI ? 'ai' : 'user';
        var senderName = isAI ? 'AI' : 'You';

        var messageElement = $('<div>')
            .addClass('message ' + messageClass)
            .html('<strong>' + senderName + ':</strong> <span class="message-text">' + content + '</span>');

        if (isAI) {
            addSpeakButton(messageElement);
        }

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
            .html('<strong>AI:</strong> <span>Thinking...</span>');
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
                $(".speak-button").off('click').on('click', function() {
                    const messageText = $(this).siblings('.message-text').text();
                    speakMessage(messageText);
                });
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

// 确保语音列表已加载
speechSynthesis.onvoiceschanged = () => {
    voices = speechSynthesis.getVoices();
};
