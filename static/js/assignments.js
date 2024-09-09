$(document).ready(function() {
    var totalQuestions = $('.question').length;
    var currentQuestion = 1;

    function updateProgressBar() {
        var progress = (currentQuestion / totalQuestions) * 100;
        $('#progress-bar').css('width', progress + '%').attr('aria-valuenow', progress).text(Math.round(progress) + '%');
    }

    $('.submit-answer').on('click', function() {
        var questionId = $(this).data('question-id');
        var answer = $('input[name="question_' + questionId + '"]:checked').val() || $('textarea[name="question_' + questionId + '"]').val();
        
        if (!answer) {
            alert('请提供答案后再继续。');
            return;
        }
        
        $.ajax({
            url: '/assignments/submit_answer/',
            method: 'POST',
            data: {
                question_id: questionId,
                answer: answer,
                csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').val()
            },
            success: function(response) {
                if (response.status === 'success') {
                    var currentQuestionDiv = $('.question[data-question-id="' + questionId + '"]');
                    var nextQuestionDiv = currentQuestionDiv.next('.question');
                    
                    currentQuestionDiv.fadeOut(300, function() {
                        if (nextQuestionDiv.length) {
                            nextQuestionDiv.fadeIn(300);
                            currentQuestion++;
                            updateProgressBar();
                        } else {
                            $('#question-container').fadeOut(300, function() {
                                $('#assignment-complete').fadeIn(300);
                            });
                        }
                    });
                } else {
                    alert('提交答案时出错。请重试。');
                }
            },
            error: function() {
                alert('提交答案时出错。请重试。');
            }
        });
    });

    updateProgressBar();

    // 添加语音功能
    $('.speak-button').on('click', function(e) {
        e.preventDefault();
        const text = $(this).data('text');
        speakText(text, this);
    });

    function speakText(text, button) {
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
                const audio = new Audio(URL.createObjectURL(data));
                audio.play();
            },
            error: function(jqXHR, textStatus, errorThrown) {
                console.error("Error in text-to-speech:", textStatus, errorThrown);
                alert("语音合成失败，请稍后再试。");
            }
        });
    }
});
