$(document).ready(function() {
    $('#speak-button').on('click', function() {
        var storyContent = $('.story-content').text();
        var csrftoken = $('[name=csrfmiddlewaretoken]').val();
        $('#loading-indicator').show();
        $('#speak-button').prop('disabled', true);
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
                responseType: 'arraybuffer'
            },
            success: function(data) {
                var audio = new Audio(URL.createObjectURL(new Blob([data], {type: 'audio/mp3'})));
                audio.play();
            },
            error: function() {
                alert('Failed to generate speech. Please try again.');
            },
            complete: function() {
                $('#loading-indicator').hide();
                $('#speak-button').prop('disabled', false);
            }
        });
    });
});