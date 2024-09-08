$(document).ready(function() {
    var chatBox = $('#chat-box');
    var messageInput = $('#message');
    var submitButton = $('#chat-form button[type="submit"]');

    function scrollToBottom() {
        chatBox.scrollTop(chatBox[0].scrollHeight);
    }

    let currentAudio = null;

    function speakMessage(text, button) {
        if (currentAudio) {
            currentAudio.pause();
            $(currentAudio.dataset.button).removeClass('speaking requesting');
            if (currentAudio.dataset.buttonId === button.id) {
                currentAudio = null;
                return;
            }
        }

        // 确保文本不为空
        if (!text.trim()) {
            console.error("Empty text, cannot synthesize speech");
            return;
        }

        var voice = /[\u4e00-\u9fa5]/.test(text) ? 'shimmer' : 'alloy';
        
        $(button).addClass('requesting');
        
        $.ajax({
            url: '/chatbots/tts/',
            method: 'POST',
            data: {
                text: text,
                voice: voice,
                csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').val()
            },
            xhrFields: {
                responseType: 'blob'
            },
            success: function(data) {
                $(button).removeClass('requesting').addClass('speaking');
                currentAudio = new Audio(URL.createObjectURL(data));
                currentAudio.dataset.buttonId = button.id;
                currentAudio.dataset.button = button;
                currentAudio.play();
                currentAudio.onended = function() {
                    $(button).removeClass('speaking');
                    currentAudio = null;
                };
            },
            error: function(jqXHR, textStatus, errorThrown) {
                $(button).removeClass('requesting speaking');
                console.error("Error in text-to-speech:", textStatus, errorThrown);
                // 打印响应内容
                console.error("Response:", jqXHR.responseText);
            }
        });
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
        speakMessage(messageText, this);
    });

    function addMessage(sender, content, isAI = false) {
        var messageClass = isAI ? 'ai' : 'user';
        var senderName = isAI ? 'AI' : 'You';

        var messageElement = $('<div>')
            .addClass('message ' + messageClass)
            .html('</strong> <span class="message-text">' + content + '</span>');

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

function addAIResponse(response) {
    var uniqueId = 'speak-' + Date.now();
    var responseHtml = '<div class="message ai">' +
        '<span class="message-text"></span>' +
        '<button id="' + uniqueId + '" class="btn btn-sm btn-outline-secondary ml-2 speak-button">' +
        '<i class="fas fa-volume-up"></i>' +
        '<span class="status-dot"></span></button></div>';
    var $responseElement = $(responseHtml);
    chatBox.append($responseElement);
    scrollToBottom();
    
    // 模拟打字效果
    var $messageText = $responseElement.find('.message-text');
    var words = response.split(' ');
    var i = 0;
    var intervalId = setInterval(function() {
        if (i < words.length) {
            var $word = $('<span class="typed-word">').text(words[i] + ' ');
            $messageText.append($word);
            $word.animate({opacity: 1}, 100); // 淡入效果
            scrollToBottom();
            i++;
        } else {
            clearInterval(intervalId);
            $responseElement.find('.speak-button').fadeIn(300);
        }
    }, 50); // 调整这个数值可以改变"��字"速度

    // 添加语音功能
    $responseElement.find('.speak-button').click(function() {
        speakMessage(response, this);
    });
}
