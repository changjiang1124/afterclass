$(document).ready(function() {
    $('#speak-button').on('click', function() {
        var storyContent = $('.story-content').text();
        var csrftoken = $('input[name=csrfmiddlewaretoken]').val();
        $.ajax({
            url: '/tts/',
            method: 'POST',
            data: {
                text: storyContent,
            },
            headers: {
                'X-CSRFToken': csrftoken
            },
            xhrFields: {
                responseType: 'blob'
            },
            success: function(data) {
                var audio = new Audio(URL.createObjectURL(data));
                audio.play();
            },
            error: function() {
                alert('Failed to generate speech. Please try again.');
            }
        });
    });
});