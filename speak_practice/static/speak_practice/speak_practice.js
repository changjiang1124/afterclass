function initializeChat(sessionId, chatApiUrl, transcribeApiUrl, translateApiUrl, csrfToken) {
    // --- UI Elements ---
    const chatBox = document.getElementById('chat-box');
    const inputArea = document.getElementById('input-area');
    const confirmationArea = document.getElementById('confirmation-area');
    const statusIndicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    
    // Input Controls
    const textInput = document.getElementById('text-input');
    const recordBtn = document.getElementById('record-btn');
    const stopBtn = document.getElementById('stop-btn');
    const sendTextBtn = document.getElementById('send-text-btn');

    // Confirmation Controls
    const transcribedTextElem = document.getElementById('transcribed-text');
    const englishTranslationElem = document.getElementById('english-translation');
    const confirmSendBtn = document.getElementById('confirm-send-btn');
    const rerecordBtn = document.getElementById('rerecord-btn');

    // Audio element for TTS
    const ttsAudio = document.getElementById('tts-audio');

    let mediaRecorder;
    let audioChunks = [];
    let isRecording = false;

    // --- Event Listeners ---
    recordBtn.addEventListener('click', startRecording);
    stopBtn.addEventListener('click', stopRecording);
    confirmSendBtn.addEventListener('click', sendTranscribedMessage);
    rerecordBtn.addEventListener('click', resetInputState);
    sendTextBtn.addEventListener('click', sendTypedMessage);
    
    // Handle Enter key in text input
    textInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendTypedMessage();
        }
    });

    // Auto-resize textarea
    textInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        
        // Limit max height
        const maxHeight = 120;
        if (this.scrollHeight > maxHeight) {
            this.style.height = maxHeight + 'px';
            this.style.overflowY = 'auto';
        } else {
            this.style.overflowY = 'hidden';
        }
    });

    // --- UI State Management ---
    function showStatus(message) {
        statusText.textContent = message;
        statusIndicator.style.display = 'block';
    }

    function hideStatus() {
        statusIndicator.style.display = 'none';
    }

    function showConfirmation(transcribed, english) {
        transcribedTextElem.textContent = transcribed;
        englishTranslationElem.textContent = english;
        confirmationArea.style.display = 'block';
        inputArea.style.display = 'none';
    }

    function hideConfirmation() {
        confirmationArea.style.display = 'none';
        inputArea.style.display = 'flex';
    }

    function resetInputState() {
        hideStatus();
        hideConfirmation();
        recordBtn.classList.remove('recording');
        isRecording = false;
        
        // Clear text input
        textInput.value = '';
        textInput.style.height = 'auto';
    }

    function scrollToBottom() {
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    // --- Recording Functions ---
    async function startRecording() {
        if (isRecording) return;

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];
            
            mediaRecorder.addEventListener('dataavailable', e => audioChunks.push(e.data));
            mediaRecorder.addEventListener('stop', handleRecordingStop);
            
            mediaRecorder.start();
            isRecording = true;
            recordBtn.classList.add('recording');
            recordBtn.style.display = 'none';
            stopBtn.style.display = 'flex';
            showStatus('Listening...');
            
        } catch (err) {
            console.error("Error starting recording:", err);
            alert("Could not start recording. Please ensure microphone permissions are granted.");
        }
    }

    function stopRecording() {
        if (!isRecording || !mediaRecorder) return;
        
        mediaRecorder.stop();
        isRecording = false;
        recordBtn.classList.remove('recording');
        stopBtn.style.display = 'none';
        recordBtn.style.display = 'flex';
        showStatus('Processing audio...');
        
        // Stop all audio tracks
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }

    async function handleRecordingStop() {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        await transcribeAudio(audioBlob);
    }

    // --- Audio Processing ---
    async function transcribeAudio(audioBlob) {
        showStatus('Transcribing audio...');
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');

        try {
            const response = await fetch(transcribeApiUrl, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken },
                body: formData,
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'Transcription failed.');
            }
            
            hideStatus();
            showConfirmation(data.chinese_text, data.english_translation);

        } catch (error) {
            console.error('Transcription Error:', error);
            alert(`Transcription Error: ${error.message}`);
            resetInputState();
        }
    }

    // --- Message Sending ---
    function sendTranscribedMessage() {
        const message = transcribedTextElem.textContent;
        sendMessage(message);
        hideConfirmation();
    }

    async function sendTypedMessage() {
        const text = textInput.value.trim();
        if (!text) return;

        showStatus('Translating text...');
        
        try {
            const response = await fetch(translateApiUrl, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json', 
                    'X-CSRFToken': csrfToken 
                },
                body: JSON.stringify({ text }),
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'Translation failed.');
            }
            
            // Play TTS audio if available
            if (data.tts_audio) {
                playAudio(data.tts_audio);
            }
            
            sendMessage(data.chinese_text);
            textInput.value = '';
            textInput.style.height = 'auto';

        } catch (error) {
            console.error('Translation Error:', error);
            alert(`Translation Error: ${error.message}`);
            resetInputState();
        }
    }

    async function sendMessage(message) {
        // Add user message to chat immediately
        appendMessage('user', { chinese_text: message });
        showStatus('AI is thinking...');

        try {
            const response = await fetch(chatApiUrl, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json', 
                    'X-CSRFToken': csrfToken 
                },
                body: JSON.stringify({ 
                    message: message, 
                    session_id: sessionId 
                }),
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'Chat API failed.');
            }
            
            // Add AI response with delay for better UX
            setTimeout(() => {
                appendMessage('ai', data.ai_response);
                
                // Update token information display
                if (data.token_info) {
                    updateTokenDisplay(data.token_info);
                }
                
                // Play TTS audio if available
                if (data.tts_audio) {
                    playAudio(data.tts_audio);
                }
                
                // Show conversation end message if needed
                if (data.token_info && data.token_info.conversation_ended) {
                    showConversationEndMessage();
                }
            }, 500);

        } catch (error) {
            console.error('Chat Error:', error);
            alert(`Chat Error: ${error.message}`);
        } finally {
            resetInputState();
        }
    }

    // --- Message Display ---
    function appendMessage(sender, content) {
        const messageWrapper = document.createElement('div');
        messageWrapper.classList.add('chat-message', sender);
        messageWrapper.style.opacity = '0';

        // Create avatar
        const avatar = document.createElement('div');
        avatar.classList.add('message-avatar', sender);
        avatar.innerHTML = `<i class="fas fa-${sender === 'ai' ? 'robot' : 'user'}"></i>`;

        // Create message content
        const messageContent = document.createElement('div');
        messageContent.classList.add('message-content');

        if (sender === 'ai') {
            messageContent.innerHTML = `
                <div class="chinese-text">${content.chinese}</div>
                <hr class="pinyin-divider">
                <div class="pinyin-text">${content.pinyin}</div>
            `;
        } else {
            messageContent.innerHTML = `
                <div class="chinese-text">${content.chinese_text}</div>
            `;
        }

        // Append elements based on message type
        if (sender === 'user') {
            messageWrapper.appendChild(messageContent);
            messageWrapper.appendChild(avatar);
        } else {
            messageWrapper.appendChild(avatar);
            messageWrapper.appendChild(messageContent);
        }

        chatBox.appendChild(messageWrapper);

        // Trigger animation
        setTimeout(() => {
            messageWrapper.style.opacity = '1';
            messageWrapper.style.transform = 'translateX(0)';
        }, 50);

        // Auto-scroll to bottom
        scrollToBottom();
    }

    // --- Audio Playback ---
    function playAudio(base64Audio) {
        if (base64Audio && ttsAudio) {
            try {
                ttsAudio.src = 'data:audio/mp3;base64,' + base64Audio;
                ttsAudio.play().catch(error => {
                    console.error('Audio playback failed:', error);
                });
            } catch (error) {
                console.error('Audio setup failed:', error);
            }
        }
    }

    // --- Initialization ---
    function initialize() {
        // Scroll to bottom on load
        scrollToBottom();
        
        // Focus text input
        textInput.focus();
        
        // Hide status and confirmation areas initially
        hideStatus();
        hideConfirmation();
        
        console.log('Chat initialized successfully');
    }

    // Initialize chat
    initialize();
}

// Legacy support for the old initialization pattern
function initializeChat(config) {
    if (typeof config === 'object') {
        const { sessionId, chatApiUrl, transcribeApiUrl, translateApiUrl, csrfToken } = config;
        return initializeChat(sessionId, chatApiUrl, transcribeApiUrl, translateApiUrl, csrfToken);
    }
    // If called with individual parameters, use them directly
    return initializeChat(...arguments);
}

// --- Token Display Functions ---
function updateTokenDisplay(tokenInfo) {
    let tokenDisplay = document.getElementById('token-display');
    
    // Create token display element if it doesn't exist
    if (!tokenDisplay) {
        tokenDisplay = document.createElement('div');
        tokenDisplay.id = 'token-display';
        tokenDisplay.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(255, 255, 255, 0.95);
            border: 2px solid #e5e7eb;
            border-radius: 0.75rem;
            padding: 1rem;
            font-size: 0.875rem;
            z-index: 1000;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
            backdrop-filter: blur(10px);
            min-width: 200px;
        `;
        document.body.appendChild(tokenDisplay);
    }
    
    // Update display based on token percentage
    const percentage = tokenInfo.percentage_used;
    let bgColor = '#dcfce7'; // Green
    let textColor = '#166534';
    let borderColor = '#10b981';
    
    if (percentage >= 90) {
        bgColor = '#fee2e2'; // Red
        textColor = '#991b1b';
        borderColor = '#ef4444';
    } else if (percentage >= 80) {
        bgColor = '#fef3c7'; // Yellow
        textColor = '#92400e';
        borderColor = '#f59e0b';
    }
    
    tokenDisplay.style.background = bgColor;
    tokenDisplay.style.color = textColor;
    tokenDisplay.style.borderColor = borderColor;
    
    tokenDisplay.innerHTML = `
        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
            <i class="fas fa-chart-bar" style="color: ${textColor};"></i>
            <strong>Conversation Progress</strong>
        </div>
        <div style="margin-bottom: 0.5rem;">
            <div style="background: rgba(255, 255, 255, 0.7); border-radius: 0.5rem; height: 8px; overflow: hidden;">
                <div style="
                    width: ${percentage}%; 
                    height: 100%; 
                    background: ${borderColor}; 
                    transition: width 0.3s ease;
                "></div>
            </div>
        </div>
        <div style="font-size: 0.75rem;">
            ${tokenInfo.current_tokens.toLocaleString()} / ${tokenInfo.max_tokens.toLocaleString()} tokens (${percentage}%)
        </div>
        ${tokenInfo.approaching_limit ? '<div style="font-size: 0.75rem; margin-top: 0.5rem; font-weight: 600;"><i class="fas fa-exclamation-triangle" style="margin-right: 0.25rem;"></i>Approaching limit</div>' : ''}
    `;
    
    // Animate entrance
    tokenDisplay.style.opacity = '0';
    tokenDisplay.style.transform = 'translateY(-10px)';
    setTimeout(() => {
        tokenDisplay.style.transition = 'all 0.3s ease';
        tokenDisplay.style.opacity = '1';
        tokenDisplay.style.transform = 'translateY(0)';
    }, 100);
}

function showConversationEndMessage() {
    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(17, 24, 39, 0.7);
        backdrop-filter: blur(8px);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 2000;
        opacity: 0;
        transition: opacity 0.3s ease;
    `;
    
    // Create modal content
    const modal = document.createElement('div');
    modal.style.cssText = `
        background: #ffffff;
        border-radius: 1.5rem;
        padding: 3rem;
        max-width: 500px;
        width: 90%;
        text-align: center;
        box-shadow: 0 25px 50px -12px rgb(0 0 0 / 0.25);
        transform: scale(0.9) translateY(20px);
        transition: transform 0.3s ease;
    `;
    
    modal.innerHTML = `
        <div style="margin-bottom: 2rem;">
            <i class="fas fa-check-circle" style="font-size: 4rem; color: #10b981; margin-bottom: 1rem;"></i>
            <h2 style="margin: 0 0 1rem 0; font-size: 1.75rem; font-weight: 700; color: #111827;">
                Conversation Complete!
            </h2>
            <p style="margin: 0; color: #6b7280; font-size: 1.1rem; line-height: 1.6;">
                You've reached the token limit for this session. Great job practicing your Chinese! 
                Would you like to start a new conversation?
            </p>
        </div>
        <div style="display: flex; gap: 1rem; justify-content: center;">
            <button onclick="window.location.href='/speak_practice/'" style="
                background: linear-gradient(135deg, #3b82f6, #2563eb);
                color: white;
                border: none;
                padding: 0.75rem 1.5rem;
                border-radius: 0.75rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            ">
                <i class="fas fa-plus"></i>
                New Conversation
            </button>
            <button onclick="window.close()" style="
                background: #ffffff;
                color: #6b7280;
                border: 2px solid #d1d5db;
                padding: 0.75rem 1.5rem;
                border-radius: 0.75rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
            ">
                Close
            </button>
        </div>
    `;
    
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    
    // Animate entrance
    setTimeout(() => {
        overlay.style.opacity = '1';
        modal.style.transform = 'scale(1) translateY(0)';
    }, 100);
    
    // Disable input area
    const inputArea = document.getElementById('input-area');
    if (inputArea) {
        inputArea.style.pointerEvents = 'none';
        inputArea.style.opacity = '0.5';
    }
}
