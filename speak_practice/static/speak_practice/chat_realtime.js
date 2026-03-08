(function () {
    const config = window.speakPracticeConfig;
    if (!config) {
        return;
    }

    const STORAGE_KEYS = {
        autoPlay: 'speak_practice_auto_play_ai_audio',
        pinyinVisible: 'speak_practice_pinyin_visible',
    };

    const REALTIME_CALLS_API_URL = 'https://api.openai.com/v1/realtime/calls';
    const realtimeSupported = Boolean(window.RTCPeerConnection && navigator.mediaDevices?.getUserMedia);

    const state = {
        mode: 'voice',
        autoPlayAiAudio: true,
        currentAudioBase64: '',
        currentTranslationAudio: '',
        currentTranslationText: '',
        currentTranslationPinyin: '',
        currentSuggestedReplyAudio: '',
        confirmationEnglish: '',
        manualMute: false,
        currentStage: 'idle',
        suggestionRequestId: 0,
        sessionHasMessages: Array.isArray(config.conversationHistory) && config.conversationHistory.length > 0,
        hasRequestedOpeningTurn: false,
        realtime: {
            supported: realtimeSupported,
            connecting: false,
            connected: false,
            peerConnection: null,
            dataChannel: null,
            mediaStream: null,
            remoteAudio: null,
            micEnabled: false,
            pendingItemKeys: new Set(),
            persistedItemKeys: new Set(),
            assistantTranscriptBuffer: '',
            assistantLastRenderKey: '',
            openingRetryCount: 0,
            openingWatchdogId: null,
        },
    };

    const el = {
        chatBox: document.getElementById('chat-box'),
        statusIndicator: document.getElementById('status-indicator'),
        statusIcon: document.getElementById('status-icon'),
        statusText: document.getElementById('status-text'),
        statusProgress: document.getElementById('status-progress'),
        connectionText: document.getElementById('connection-text'),
        voiceStage: document.getElementById('voice-stage'),
        voiceStagePill: document.getElementById('voice-stage-pill'),
        voiceStageStatus: document.getElementById('voice-stage-status'),
        voiceStageHint: document.getElementById('voice-stage-hint'),
        voiceStageFooter: document.getElementById('voice-stage-footer-text'),
        turnFocusLabel: document.getElementById('turn-focus-label'),
        turnFocusTitle: document.getElementById('turn-focus-title'),
        turnFocusCopy: document.getElementById('turn-focus-copy'),
        voiceTimer: document.getElementById('recording-timer-inline'),
        autoPlayToggle: document.getElementById('auto-play-toggle'),
        waveformBars: Array.from(document.querySelectorAll('.voice-wave-bar')),
        startLiveSessionBtn: document.getElementById('start-live-session-btn'),
        reconnectLiveSessionBtn: document.getElementById('reconnect-live-session-btn'),
        voiceModeBtn: document.getElementById('voice-mode-btn'),
        chineseModeBtn: document.getElementById('chinese-mode-btn'),
        englishModeBtn: document.getElementById('english-mode-btn'),
        voiceInputArea: document.getElementById('voice-input-area'),
        chineseInputArea: document.getElementById('chinese-input-area'),
        englishInputArea: document.getElementById('english-input-area'),
        textFallbackShell: document.getElementById('text-fallback-shell'),
        recordBtn: document.getElementById('record-btn'),
        stopBtn: document.getElementById('stop-btn'),
        voiceAnswerCard: document.getElementById('voice-answer-card'),
        voiceAnswerLabel: document.getElementById('voice-answer-label'),
        voiceAnswerTitle: document.getElementById('voice-answer-title'),
        voiceAnswerDescription: document.getElementById('voice-answer-description'),
        chineseInput: document.getElementById('chinese-text-input'),
        englishInput: document.getElementById('english-text-input'),
        sendChineseBtn: document.getElementById('send-chinese-btn'),
        translateBtn: document.getElementById('translate-btn'),
        inputArea: document.getElementById('input-area'),
        confirmationArea: document.getElementById('confirmation-area'),
        translationArea: document.getElementById('translation-confirmation-area'),
        originalEnglishText: document.getElementById('original-english-text'),
        chineseTranslationText: document.getElementById('chinese-translation-text'),
        editTranslationBtn: document.getElementById('edit-translation-btn'),
        chineseTranslationEditor: document.getElementById('chinese-translation-editor'),
        translationEditActions: document.getElementById('translation-edit-actions'),
        saveTranslationEditBtn: document.getElementById('save-translation-edit-btn'),
        cancelTranslationEditBtn: document.getElementById('cancel-translation-edit-btn'),
        confirmTranslationSendBtn: document.getElementById('confirm-translation-send-btn'),
        retranslateTranslationBtn: document.getElementById('retranslate-translation-btn'),
        playTtsBtn: document.getElementById('play-tts-btn'),
        replayTtsBtn: document.getElementById('replay-tts-btn'),
        slowTtsBtn: document.getElementById('slow-tts-btn'),
        stopTtsBtn: document.getElementById('stop-tts-btn'),
        pinyinSection: document.getElementById('pinyin-section'),
        pinyinDisplay: document.getElementById('pinyin-display'),
        pinyinText: document.getElementById('pinyin-text'),
        togglePinyinBtn: document.getElementById('toggle-pinyin-btn'),
        ttsAudio: document.getElementById('tts-audio'),
        feedbackMessage: document.getElementById('feedback-message'),
        restartBtn: document.getElementById('restart-conversation-btn'),
        changeTopicBtn: document.getElementById('change-topic-btn'),
        userLiveCaption: document.getElementById('user-live-caption'),
        replySuggestionText: document.getElementById('reply-suggestion-text'),
        replySuggestionPinyin: document.getElementById('reply-suggestion-pinyin'),
        replySuggestionTip: document.getElementById('reply-suggestion-tip'),
        replySuggestionCard: document.getElementById('reply-suggestion-card'),
        teachReplyBtn: document.getElementById('teach-reply-btn'),
        playSuggestionBtn: document.getElementById('play-suggestion-btn'),
    };

    class WaveformController {
        constructor(bars) {
            this.bars = bars;
            this.audioContext = null;
            this.analyser = null;
            this.source = null;
            this.dataArray = null;
            this.animationId = null;
            this.mockAnimationId = null;
        }

        async ensureContext() {
            if (!this.audioContext) {
                const AudioContextClass = window.AudioContext || window.webkitAudioContext;
                if (!AudioContextClass) {
                    return false;
                }
                this.audioContext = new AudioContextClass();
            }

            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }

            return true;
        }

        async bindMicrophoneStream(stream) {
            const ok = await this.ensureContext();
            if (!ok) {
                this.startMockAnimation();
                return;
            }

            this.cleanupSource();
            this.source = this.audioContext.createMediaStreamSource(stream);
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 64;
            this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
            this.source.connect(this.analyser);
            this.startVisualizer();
        }

        startVisualizer() {
            this.stopMockAnimation();
            cancelAnimationFrame(this.animationId);

            const frame = () => {
                if (!this.analyser || !this.dataArray) {
                    return;
                }

                this.analyser.getByteFrequencyData(this.dataArray);
                const bucketSize = Math.max(1, Math.floor(this.dataArray.length / this.bars.length));

                this.bars.forEach((bar, index) => {
                    const start = index * bucketSize;
                    let sum = 0;
                    for (let i = 0; i < bucketSize; i += 1) {
                        sum += this.dataArray[start + i] || 0;
                    }
                    const average = sum / bucketSize / 255;
                    const scale = Math.max(0.18, average * 1.8);
                    bar.style.setProperty('--bar-scale', scale.toFixed(3));
                });

                this.animationId = requestAnimationFrame(frame);
            };

            frame();
        }

        startMockAnimation() {
            if (this.mockAnimationId) {
                return;
            }

            const tick = () => {
                this.bars.forEach((bar, index) => {
                    const wave = 0.2 + Math.abs(Math.sin((Date.now() / 220) + index)) * 0.9;
                    bar.style.setProperty('--bar-scale', wave.toFixed(3));
                });
                this.mockAnimationId = requestAnimationFrame(tick);
            };

            tick();
        }

        stopMockAnimation() {
            cancelAnimationFrame(this.mockAnimationId);
            this.mockAnimationId = null;
        }

        reset() {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
            this.stopMockAnimation();
            this.bars.forEach((bar, index) => {
                const base = 0.18 + ((index % 4) * 0.04);
                bar.style.setProperty('--bar-scale', base.toFixed(3));
            });
        }

        cleanupSource() {
            if (this.source) {
                try {
                    this.source.disconnect();
                } catch (error) {
                    console.warn('Failed to disconnect audio source', error);
                }
            }
            this.source = null;
            this.analyser = null;
            this.dataArray = null;
        }
    }

    const waveform = new WaveformController(el.waveformBars);

    function loadPreference(key, fallback) {
        try {
            const raw = localStorage.getItem(key);
            return raw === null ? fallback : JSON.parse(raw);
        } catch (error) {
            return fallback;
        }
    }

    function savePreference(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            console.warn('Failed to store preference', key, error);
        }
    }

    function escapeHtml(value) {
        return String(value || '')
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#39;');
    }

    function autoResize(textarea) {
        if (!textarea) {
            return;
        }

        textarea.style.height = 'auto';
        textarea.style.height = `${Math.min(textarea.scrollHeight, 140)}px`;
        textarea.style.overflowY = textarea.scrollHeight > 140 ? 'auto' : 'hidden';
    }

    function scrollToBottom() {
        el.chatBox.scrollTop = el.chatBox.scrollHeight;
    }

    function ensureEmptyState() {
        if (!el.chatBox || document.getElementById('chat-empty-state')) {
            return;
        }

        const emptyState = document.createElement('div');
        emptyState.id = 'chat-empty-state';
        emptyState.className = 'chat-empty-state';
        emptyState.innerHTML = `
            <div class="chat-empty-icon"><i class="fas fa-headset"></i></div>
            <h5>AI will start the scene</h5>
            <p>Press <strong>Start Conversation</strong>. The AI opens first, then you answer when you are ready.</p>
        `;
        el.chatBox.appendChild(emptyState);
    }

    function removeEmptyState() {
        const emptyState = document.getElementById('chat-empty-state');
        if (emptyState) {
            emptyState.remove();
        }
    }

    function showStatus(message, tone = 'info') {
        if (!el.statusIndicator) {
            return;
        }

        const iconMap = {
            info: 'fa-circle-info',
            loading: 'fa-circle-notch fa-spin',
            success: 'fa-check-circle',
            error: 'fa-triangle-exclamation',
        };

        el.statusIndicator.style.display = 'flex';
        el.statusText.textContent = message;
        el.statusIcon.className = `status-icon fas ${iconMap[tone] || iconMap.info}`;
        el.statusIndicator.dataset.tone = tone;
        if (el.statusProgress) {
            el.statusProgress.style.width = tone === 'loading' ? '72%' : '100%';
        }
    }

    function hideStatus() {
        if (el.statusIndicator) {
            el.statusIndicator.style.display = 'none';
        }
    }

    function setStage(stateName, status, hint, footer) {
        state.currentStage = stateName;
        el.voiceStage.classList.remove('is-idle', 'is-listening', 'is-processing', 'is-speaking', 'is-ready');
        el.voiceStage.classList.add(`is-${stateName}`);
        el.voiceStageStatus.textContent = status;
        el.voiceStageHint.textContent = hint;
        el.voiceStageFooter.textContent = footer;

        const pillMap = {
            idle: ['fa-plug', 'Tap to connect'],
            ready: ['fa-circle-play', 'Your turn next'],
            listening: ['fa-microphone-lines', 'Listening now'],
            processing: ['fa-wand-magic-sparkles', 'Processing'],
            speaking: ['fa-volume-high', 'AI speaking'],
        };

        const [icon, label] = pillMap[stateName] || pillMap.idle;
        el.voiceStagePill.innerHTML = `<i class="fas ${icon}"></i><span>${label}</span>`;
        syncTurnFocus();
        syncVoiceActionButton();
    }

    function updateConnectionStatus(label) {
        if (el.connectionText) {
            el.connectionText.textContent = label;
        }
    }

    function setMode(mode) {
        state.mode = mode;
        const mapping = {
            voice: [el.voiceInputArea, el.voiceModeBtn],
            chinese: [el.chineseInputArea, el.chineseModeBtn],
            english: [el.englishInputArea, el.englishModeBtn],
        };

        [el.voiceInputArea, el.chineseInputArea, el.englishInputArea].forEach((node) => node.classList.remove('active'));
        [el.voiceModeBtn, el.chineseModeBtn, el.englishModeBtn].forEach((node) => node.classList.remove('active'));

        const [area, button] = mapping[mode];
        area.classList.add('active');
        button.classList.add('active');

        if (el.textFallbackShell) {
            el.textFallbackShell.open = mode !== 'voice';
        }

        if (mode !== 'voice' && state.realtime.connected) {
            state.manualMute = true;
            setMicEnabled(false);
        }

        if (mode === 'chinese') {
            el.chineseInput.focus();
        } else if (mode === 'english') {
            el.englishInput.focus();
        }

        syncTurnFocus();
        syncVoiceActionButton();
    }

    function syncTurnFocus() {
        if (!el.turnFocusLabel || !el.turnFocusTitle || !el.turnFocusCopy) {
            return;
        }

        let icon = 'fa-circle-play';
        let label = 'Next step';
        let title = 'Press Start Conversation';
        let copy = 'The AI will ask the first question before you speak.';

        if (!state.realtime.connected) {
            icon = 'fa-bolt';
            label = 'Step 1';
            title = 'Start conversation';
            copy = 'Connect once and let the AI open the scene first.';
        } else if (state.realtime.micEnabled || state.currentStage === 'listening') {
            icon = 'fa-microphone-lines';
            label = 'It is your turn';
            title = 'Speak now';
            copy = 'Say one short Chinese reply, then tap Stop talking when you finish.';
        } else if (state.currentStage === 'processing') {
            icon = 'fa-wand-magic-sparkles';
            label = 'Please wait';
            title = 'AI is replying';
            copy = 'Hold for a moment while your turn is processed and the next reply is generated.';
        } else if (state.currentStage === 'speaking') {
            icon = 'fa-volume-high';
            label = 'Listen first';
            title = 'AI is speaking';
            copy = 'Listen to the full line before starting your next answer.';
        } else if (state.currentStage === 'ready') {
            icon = 'fa-microphone-alt';
            label = 'It is your turn';
            title = "It's your turn";
            copy = 'Tap Start speaking when you are ready. If you need help, tap Teach me what to say.';
        }

        el.turnFocusLabel.innerHTML = `<i class="fas ${icon}"></i><span>${label}</span>`;
        el.turnFocusTitle.textContent = title;
        el.turnFocusCopy.textContent = copy;

        if (el.voiceAnswerLabel) {
            el.voiceAnswerLabel.innerHTML = `<i class="fas ${icon}"></i><span>${label}</span>`;
        }
        if (el.voiceAnswerTitle) {
            el.voiceAnswerTitle.textContent = title;
        }
        if (el.voiceAnswerDescription) {
            el.voiceAnswerDescription.textContent = copy;
        }
        syncTeachReplyButton();
    }

    function syncVoiceActionButton() {
        if (!el.recordBtn || !el.stopBtn) {
            return;
        }

        if (el.voiceAnswerCard) {
            if (!state.realtime.connected) {
                el.voiceAnswerCard.style.setProperty('display', 'none', 'important');
            } else {
                el.voiceAnswerCard.style.removeProperty('display');
            }
        }

        const recordIcon = el.recordBtn.querySelector('i');
        const recordLabel = el.recordBtn.querySelector('span');
        const stopLabel = el.stopBtn.querySelector('span');

        el.recordBtn.classList.remove('is-waiting');
        el.recordBtn.disabled = state.realtime.connecting;
        el.stopBtn.disabled = state.realtime.connecting;

        if (state.realtime.micEnabled) {
            el.recordBtn.hidden = true;
            el.stopBtn.hidden = false;
            if (stopLabel) {
                stopLabel.textContent = 'Stop talking';
            }
            return;
        }

        el.stopBtn.hidden = true;
        el.recordBtn.hidden = false;

        if (!state.realtime.connected) {
            if (recordIcon) {
                recordIcon.className = 'fas fa-bolt';
            }
            if (recordLabel) {
                recordLabel.textContent = 'Start conversation';
            }
            el.recordBtn.title = 'Start conversation';
            return;
        }

        if (state.currentStage === 'processing' || state.currentStage === 'speaking') {
            if (recordIcon) {
                recordIcon.className = 'fas fa-hourglass-half';
            }
            if (recordLabel) {
                recordLabel.textContent = 'Wait for AI';
            }
            el.recordBtn.title = 'Wait for the AI to finish';
            el.recordBtn.disabled = true;
            el.recordBtn.classList.add('is-waiting');
            return;
        }

        if (recordIcon) {
            recordIcon.className = 'fas fa-microphone';
        }
        if (recordLabel) {
            recordLabel.textContent = 'Start speaking';
        }
        el.recordBtn.title = 'Start speaking';
    }

    function syncTeachReplyButton() {
        if (!el.teachReplyBtn) {
            return;
        }

        const latestAiTexts = el.chatBox?.querySelectorAll('.chat-message.ai .chinese-text');
        const hasAssistantLine = latestAiTexts && latestAiTexts.length > 0 &&
            Boolean(latestAiTexts[latestAiTexts.length - 1].textContent.trim());

        const canTeach = state.realtime.connected
            && !state.realtime.micEnabled
            && state.currentStage === 'ready'
            && hasAssistantLine;

        el.teachReplyBtn.disabled = !canTeach;
    }

    function appendMessage(sender, payload) {
        removeEmptyState();
        const wrapper = document.createElement('div');
        wrapper.className = `chat-message ${sender}`;

        const avatar = document.createElement('div');
        avatar.className = `message-avatar ${sender}`;
        avatar.innerHTML = `<i class="fas fa-${sender === 'ai' ? 'robot' : 'user'}"></i>`;

        const content = document.createElement('div');
        content.className = 'message-content';

        if (sender === 'ai') {
            content.innerHTML = `
                <div class="chinese-text">${escapeHtml(payload.chinese)}</div>
                <hr class="pinyin-divider">
                <div class="pinyin-text">${escapeHtml(payload.pinyin || '')}</div>
            `;
        } else {
            content.innerHTML = `<div class="chinese-text">${escapeHtml(payload.chinese_text)}</div>`;
        }

        if (sender === 'user') {
            wrapper.append(content, avatar);
        } else {
            wrapper.append(avatar, content);
        }

        el.chatBox.appendChild(wrapper);
        state.sessionHasMessages = true;
        scrollToBottom();
    }

    function hideAllConfirmations() {
        el.confirmationArea.style.display = 'none';
        el.translationArea.style.display = 'none';
        el.inputArea.style.display = 'block';
    }

    function updatePinyinVisibility(visible) {
        savePreference(STORAGE_KEYS.pinyinVisible, visible);
        if (el.pinyinDisplay) {
            el.pinyinDisplay.style.display = visible ? 'block' : 'none';
        }
        if (el.togglePinyinBtn) {
            el.togglePinyinBtn.innerHTML = `<i class="fas ${visible ? 'fa-eye-slash' : 'fa-eye'}"></i>`;
        }
    }

    async function playFallbackAudio(base64Audio, options = {}) {
        const forcePlayback = Boolean(options.forcePlayback);
        const rememberAsCurrent = options.rememberAsCurrent !== false;
        if (!base64Audio || (!forcePlayback && !state.autoPlayAiAudio)) {
            return false;
        }

        const playbackRate = options.playbackRate || 1;
        el.ttsAudio.pause();
        el.ttsAudio.currentTime = 0;
        el.ttsAudio.srcObject = null;
        el.ttsAudio.src = `data:audio/mp3;base64,${base64Audio}`;
        el.ttsAudio.playbackRate = playbackRate;
        if (rememberAsCurrent) {
            state.currentAudioBase64 = base64Audio;
        }

        setStage(
            'speaking',
            options.statusTitle || 'AI is speaking now.',
            options.statusHint || 'Listen to the reply first, then answer when it finishes.',
            options.statusFooter || (playbackRate < 1 ? 'Slow playback is active.' : 'Natural-speed playback is active.'),
        );
        waveform.startMockAnimation();

        try {
            await el.ttsAudio.play();
            return true;
        } catch (error) {
            waveform.reset();
            setStage('ready', 'Tap replay to hear the line.', 'Your browser blocked autoplay. Use replay once to unlock audio.', 'Audio is ready but needs a tap.');
            return false;
        }
    }

    function stopFallbackAudio() {
        el.ttsAudio.pause();
        el.ttsAudio.currentTime = 0;
        waveform.reset();
    }

    function attachFallbackAudioLifecycle() {
        el.ttsAudio.addEventListener('ended', () => {
            waveform.reset();
            if (state.realtime.connected && state.mode === 'voice') {
                setMicEnabled(false);
                setStage('ready', "It's your turn.", 'Tap Start speaking when you are ready. When you finish, tap Stop talking. If you need help, tap Teach me what to say.', 'Waiting for your answer.');
            } else {
                setStage('ready', 'Audio finished.', 'You can replay the line or answer now.', 'Waiting for your next turn.');
            }
        });

        el.ttsAudio.addEventListener('pause', () => {
            if (!el.ttsAudio.ended && el.ttsAudio.currentTime > 0) {
                waveform.reset();
            }
        });
    }

    function syncRealtimeButtons() {
        const busy = state.realtime.connecting;
        el.startLiveSessionBtn.disabled = busy;
        el.reconnectLiveSessionBtn.disabled = busy;
        el.recordBtn.disabled = busy;
        el.stopBtn.disabled = busy;
        el.startLiveSessionBtn.hidden = state.realtime.connected;
        el.reconnectLiveSessionBtn.hidden = true;
        syncVoiceActionButton();
    }

    function isRealtimeChannelOpen() {
        return state.realtime.connected
            && state.realtime.dataChannel
            && state.realtime.dataChannel.readyState === 'open';
    }

    function setCaption(node, text, placeholder, options = {}) {
        if (!node) {
            return;
        }

        const content = String(text || '').trim();
        const isEmpty = !content;
        node.textContent = isEmpty ? placeholder : content;
        node.classList.toggle('is-empty', isEmpty);
        node.classList.toggle('is-partial', Boolean(options.partial && !isEmpty));
    }

    function updateAssistantCaption(text, options = {}) {
        // AI subtitle UI was removed at user request.
        // We still log or hold the text in state if logic needs it elsewhere.
    }

    function updateUserCaption(text) {
        setCaption(
            el.userLiveCaption,
            text,
            'Your speech transcript will appear here after each turn.',
        );
    }

    function resetReplySuggestion(message, options = {}) {
        if (options.invalidatePending) {
            state.suggestionRequestId += 1;
        }
        state.currentSuggestedReplyAudio = '';
        if (el.replySuggestionCard) {
            el.replySuggestionCard.hidden = !options.keepVisible;
        }
        if (el.replySuggestionText) {
            el.replySuggestionText.textContent = message || 'After the AI finishes, a short reply you can say next will appear here.';
            el.replySuggestionText.classList.add('is-empty');
        }
        if (el.replySuggestionPinyin) {
            el.replySuggestionPinyin.textContent = '';
        }
        if (el.replySuggestionTip) {
            el.replySuggestionTip.textContent = '';
        }
        if (el.playSuggestionBtn) {
            el.playSuggestionBtn.disabled = true;
        }
    }

    function renderReplySuggestion({ chinese = '', pinyin = '', tip = '', audio = '' } = {}) {
        state.currentSuggestedReplyAudio = audio || '';
        if (el.replySuggestionCard) {
            el.replySuggestionCard.hidden = false;
        }
        if (el.replySuggestionText) {
            const hasText = Boolean(String(chinese || '').trim());
            el.replySuggestionText.textContent = hasText
                ? chinese
                : 'After the AI finishes, a short reply you can say next will appear here.';
            el.replySuggestionText.classList.toggle('is-empty', !hasText);
        }
        if (el.replySuggestionPinyin) {
            el.replySuggestionPinyin.textContent = pinyin || '';
        }
        if (el.replySuggestionTip) {
            el.replySuggestionTip.textContent = tip ? `Tip: ${tip}` : '';
        }
        if (el.playSuggestionBtn) {
            el.playSuggestionBtn.disabled = !audio;
        }
    }

    async function fetchReplySuggestion(latestAiLine) {
        if (!config.replySuggestionApiUrl || !latestAiLine) {
            return;
        }

        const requestId = state.suggestionRequestId + 1;
        state.suggestionRequestId = requestId;
        resetReplySuggestion('Thinking of a short reply you could say next...', { keepVisible: true });

        try {
            const response = await fetch(config.replySuggestionApiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': config.csrfToken,
                },
                body: JSON.stringify({
                    session_id: Number(config.sessionId),
                    latest_ai_line: latestAiLine,
                }),
            });
            const data = await response.json();
            if (requestId !== state.suggestionRequestId) {
                return;
            }

            if (!response.ok || !data.success || !data.suggestion?.chinese) {
                resetReplySuggestion('No suggestion yet. You can still answer in your own words.');
                return;
            }

            renderReplySuggestion({
                chinese: data.suggestion.chinese,
                pinyin: data.suggestion.pinyin || '',
                tip: data.suggestion.tip || '',
                audio: data.tts_audio || '',
            });
        } catch (error) {
            console.error(error);
            if (requestId === state.suggestionRequestId) {
                resetReplySuggestion('Suggestion unavailable right now. You can still answer naturally.');
            }
        }
    }

    function clearOpeningWatchdog() {
        if (state.realtime.openingWatchdogId) {
            window.clearTimeout(state.realtime.openingWatchdogId);
            state.realtime.openingWatchdogId = null;
        }
    }

    function scheduleOpeningWatchdog() {
        clearOpeningWatchdog();
        state.realtime.openingWatchdogId = window.setTimeout(() => {
            if (!isRealtimeChannelOpen() || state.realtime.assistantTranscriptBuffer.trim()) {
                return;
            }

            if (state.realtime.openingRetryCount >= 1) {
                setStage(
                    'processing',
                    'The AI opening is delayed.',
                    'The live session is connected, but the first reply has not started yet. Start the conversation again if it stays silent.',
                    'Waiting for the AI opening line.',
                );
                return;
            }

            state.realtime.openingRetryCount += 1;
            requestAssistantTurn('Start the scene now with one short, natural Chinese opening line.');
            setStage(
                'processing',
                'Retrying the AI opening.',
                'The first response did not start in time, so the opening prompt is being sent again.',
                'Retrying the opening line.',
            );
            scheduleOpeningWatchdog();
        }, 5000);
    }

    function resetLiveCaptions() {
        state.realtime.assistantTranscriptBuffer = '';
        state.realtime.assistantLastRenderKey = '';
        state.realtime.openingRetryCount = 0;
        clearOpeningWatchdog();
        updateAssistantCaption('');
        updateUserCaption('');
        resetReplySuggestion(undefined, { invalidatePending: true });
    }

    function getRealtimeClientSecret(tokenData) {
        return tokenData?.client_secret?.value || tokenData?.value || '';
    }

    function buildRealtimeItemKey(senderType, itemId, transcript) {
        return `${senderType}:${itemId || transcript.slice(0, 80)}`;
    }

    function clearRealtimePersistenceState() {
        state.realtime.pendingItemKeys.clear();
        state.realtime.persistedItemKeys.clear();
    }

    function describeRealtimeStartupError(error) {
        const message = (error && error.message ? error.message : '').trim();
        const lowered = message.toLowerCase();

        if (error?.name === 'NotAllowedError' || lowered.includes('permission')) {
            return 'Microphone permission was blocked. Allow microphone access for this site and try again.';
        }
        if (error?.name === 'NotFoundError') {
            return 'No microphone was found. Connect a microphone and retry the live session.';
        }
        if (lowered.includes('failed to initialize realtime session')) {
            return 'The server could not create a live OpenAI session. Refresh the page and try again.';
        }
        if (lowered.includes('handshake failed')) {
            return message;
        }
        if (lowered.includes('failed to fetch') || lowered.includes('networkerror') || lowered.includes('load failed')) {
            return 'The browser could not reach OpenAI Realtime. Check network access, VPN, proxy, or browser privacy extensions.';
        }

        return message || 'The live voice connection could not be started.';
    }

    function extractResponseTranscript(event) {
        const outputs = event?.response?.output;
        if (!Array.isArray(outputs)) {
            return '';
        }

        for (const item of outputs) {
            const contents = Array.isArray(item?.content) ? item.content : [];
            for (const part of contents) {
                const transcript = String(part?.transcript || part?.text || '').trim();
                if (transcript) {
                    return transcript;
                }
            }
        }

        return '';
    }

    async function ensureRealtimeMicrophone() {
        if (state.realtime.mediaStream) {
            return state.realtime.mediaStream;
        }

        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
            },
        });
        state.realtime.mediaStream = stream;
        await waveform.bindMicrophoneStream(stream);
        return stream;
    }

    function setMicEnabled(enabled) {
        const stream = state.realtime.mediaStream;
        if (stream) {
            stream.getAudioTracks().forEach((track) => {
                track.enabled = enabled;
            });
        }

        state.realtime.micEnabled = enabled;
        el.voiceTimer.textContent = enabled ? 'LIVE' : 'MUTED';
        syncTurnFocus();
        syncVoiceActionButton();
    }

    function closeRealtimeSession(options = {}) {
        const { stopTracks = false } = options;
        clearOpeningWatchdog();

        if (state.realtime.dataChannel) {
            try {
                state.realtime.dataChannel.close();
            } catch (error) {
                console.warn('Failed to close data channel', error);
            }
        }
        if (state.realtime.peerConnection) {
            try {
                state.realtime.peerConnection.close();
            } catch (error) {
                console.warn('Failed to close peer connection', error);
            }
        }
        if (state.realtime.remoteAudio) {
            state.realtime.remoteAudio.pause();
            state.realtime.remoteAudio.srcObject = null;
        }
        if (stopTracks && state.realtime.mediaStream) {
            state.realtime.mediaStream.getTracks().forEach((track) => track.stop());
            state.realtime.mediaStream = null;
        }

        state.realtime.peerConnection = null;
        state.realtime.dataChannel = null;
        state.realtime.connected = false;
        state.realtime.connecting = false;
        state.realtime.micEnabled = false;
        state.hasRequestedOpeningTurn = false;
        state.realtime.assistantTranscriptBuffer = '';
        state.realtime.assistantLastRenderKey = '';
        state.realtime.openingRetryCount = 0;
        setMicEnabled(false);
        waveform.reset();
        syncRealtimeButtons();
    }

    function sendRealtimeEvent(payload) {
        if (!isRealtimeChannelOpen()) {
            return false;
        }

        state.realtime.dataChannel.send(JSON.stringify(payload));
        return true;
    }

    function requestAssistantTurn(instructions) {
        const requestPayload = {
            type: 'response.create',
            response: {
                output_modalities: ['audio'],
            },
        };

        if (instructions) {
            requestPayload.response.instructions = instructions;
        }

        sendRealtimeEvent(requestPayload);
    }

    function commitUserAudioTurn() {
        if (!isRealtimeChannelOpen()) {
            return false;
        }
        sendRealtimeEvent({ type: 'input_audio_buffer.commit' });
        requestAssistantTurn();
        return true;
    }

    async function persistRealtimeMessage({ senderType, transcript, itemId, inputMethod = 'voice', englishTranslation = '' }) {
        const itemKey = buildRealtimeItemKey(senderType, itemId, transcript);
        if (state.realtime.persistedItemKeys.has(itemKey) || state.realtime.pendingItemKeys.has(itemKey)) {
            return null;
        }

        state.realtime.pendingItemKeys.add(itemKey);

        try {
            const response = await fetch(config.realtimeMessageApiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': config.csrfToken,
                },
                body: JSON.stringify({
                    session_id: Number(config.sessionId),
                    sender_type: senderType,
                    transcript,
                    item_id: itemId,
                    input_method: inputMethod,
                    english_translation: englishTranslation,
                }),
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Failed to save realtime message');
            }
            state.realtime.pendingItemKeys.delete(itemKey);
            state.realtime.persistedItemKeys.add(itemKey);
            return data;
        } catch (error) {
            state.realtime.pendingItemKeys.delete(itemKey);
            console.error(error);
            return null;
        }
    }

    function toggleTranslationEdit(open) {
        const shouldOpen = typeof open === 'boolean' ? open : el.chineseTranslationEditor.style.display === 'none';
        el.chineseTranslationText.style.display = shouldOpen ? 'none' : 'inline';
        el.chineseTranslationEditor.style.display = shouldOpen ? 'block' : 'none';
        el.translationEditActions.style.display = shouldOpen ? 'flex' : 'none';

        if (shouldOpen) {
            el.chineseTranslationEditor.value = state.currentTranslationText || el.chineseTranslationText.textContent.trim();
            autoResize(el.chineseTranslationEditor);
            el.chineseTranslationEditor.focus();
        }
    }

    function saveTranslationEdit() {
        const nextValue = el.chineseTranslationEditor.value.trim();
        if (!nextValue) {
            return;
        }

        state.currentTranslationText = nextValue;
        state.currentTranslationAudio = '';
        state.currentTranslationPinyin = '';
        el.chineseTranslationText.textContent = nextValue;
        el.pinyinSection.style.display = 'none';
        toggleTranslationEdit(false);
        setStage('ready', 'Edited Chinese saved.', 'The replay audio was cleared because the pronunciation changed. Send or re-translate when ready.', 'Edited translation is ready.');
    }

    function cancelTranslationEdit() {
        toggleTranslationEdit(false);
    }

    async function handleRealtimeUserTranscript(event) {
        const transcript = (event.transcript || '').trim();
        if (!transcript) {
            return;
        }

        resetReplySuggestion('Waiting for the next hint...', { invalidatePending: true });
        updateUserCaption(transcript);
        appendMessage('user', { chinese_text: transcript });
        scrollToBottom();
        await persistRealtimeMessage({
            senderType: 'user',
            transcript,
            itemId: event.item_id || '',
            inputMethod: 'voice',
        });
    }

    async function handleRealtimeAssistantTranscript(event) {
        const transcript = (event.transcript || state.realtime.assistantTranscriptBuffer || '').trim();
        if (!transcript) {
            return;
        }

        const renderKey = buildRealtimeItemKey('ai', event.item_id || '', transcript);
        if (state.realtime.assistantLastRenderKey === renderKey) {
            return;
        }

        state.realtime.assistantLastRenderKey = renderKey;
        state.realtime.assistantTranscriptBuffer = '';
        clearOpeningWatchdog();
        updateAssistantCaption(transcript);

        const persisted = await persistRealtimeMessage({
            senderType: 'ai',
            transcript,
            itemId: event.item_id || '',
        });
        const pinyin = persisted?.message?.pinyin || '';
        appendMessage('ai', { chinese: transcript, pinyin });
        resetReplySuggestion();
    }

    function handleRealtimeEvent(rawEvent) {
        let event;
        try {
            event = JSON.parse(rawEvent.data);
        } catch (error) {
            console.warn('Failed to parse realtime event', error);
            return;
        }

        switch (event.type) {
            case 'conversation.item.input_audio_transcription.completed':
                handleRealtimeUserTranscript(event);
                break;
            case 'response.output_audio_transcript.delta':
            case 'response.audio_transcript.delta':
            case 'response.text.delta': {
                const deltaText = String(event.delta || event.transcript || '').trim();
                if (deltaText) {
                    state.realtime.assistantTranscriptBuffer += deltaText;
                    updateAssistantCaption(state.realtime.assistantTranscriptBuffer, { partial: true });
                    clearOpeningWatchdog();
                }
                setMicEnabled(false);
                setStage('speaking', 'AI is speaking now.', 'Listen first, then answer after the turn ends.', 'Assistant audio is in progress.');
                waveform.startMockAnimation();
                break;
            }
            case 'response.output_audio_transcript.done':
            case 'response.audio_transcript.done':
            case 'response.text.done':
                handleRealtimeAssistantTranscript(event);
                break;
            case 'response.done':
                if (!state.realtime.assistantTranscriptBuffer.trim()) {
                    const responseTranscript = extractResponseTranscript(event);
                    if (responseTranscript) {
                        handleRealtimeAssistantTranscript({
                            transcript: responseTranscript,
                            item_id: event?.response?.output?.[0]?.id || '',
                        });
                    }
                }
                hideStatus();
                waveform.reset();
                clearOpeningWatchdog();
                if (state.mode === 'voice') {
                    setMicEnabled(false);
                    setStage('ready', "It's your turn.", 'Tap Start speaking when you are ready. When you finish, tap Stop talking. If you need help, tap Teach me what to say.', 'Waiting for your answer.');
                } else {
                    setMicEnabled(false);
                    setStage('ready', state.mode === 'voice' ? 'Mic is muted.' : 'Text mode is active.', state.mode === 'voice' ? 'Tap the microphone button when you want to answer.' : 'Use text input or switch back to voice mode to keep practicing aloud.', 'Live session is connected.');
                }
                break;
            case 'error':
                console.error('Realtime error event', event);
                hideStatus();
                setMicEnabled(false);
                clearOpeningWatchdog();
                setStage(
                    'ready',
                    'Live voice hit an error.',
                    event?.error?.message || 'Start the conversation again, or use text input while the connection recovers.',
                    'Realtime session needs attention.',
                );
                showStatus(event?.error?.message || 'Realtime voice error. Try starting the conversation again.', 'error');
                break;
            default:
                break;
        }
    }

    async function startLiveSession(options = {}) {
        const forceOpeningTurn = Boolean(options.forceOpeningTurn);
        if (!state.realtime.supported) {
            showStatus('Realtime voice is not supported in this browser.', 'error');
            setStage('ready', 'Browser support is missing.', 'Use a recent Chrome, Edge, or Safari version for live voice.', 'Text input is still available.');
            return;
        }
        if (state.realtime.connecting) {
            return;
        }

        showStatus('Connecting live voice...', 'loading');
        setStage('processing', 'Connecting to the live voice session.', 'Microphone permission and a secure realtime connection are required.', 'Setting up live conversation.');
        updateConnectionStatus('Connecting live voice...');
        syncRealtimeButtons();

        closeRealtimeSession({ stopTracks: true });
        state.realtime.connecting = true;
        clearRealtimePersistenceState();
        resetLiveCaptions();
        syncRealtimeButtons();

        try {
            const stream = await ensureRealtimeMicrophone();
            state.manualMute = false;

            const tokenResponse = await fetch(config.realtimeSessionApiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': config.csrfToken,
                },
                body: JSON.stringify({
                    session_id: Number(config.sessionId),
                }),
            });
            const tokenData = await tokenResponse.json();
            const clientSecret = getRealtimeClientSecret(tokenData);
            if (!tokenResponse.ok || !tokenData.success || !clientSecret) {
                throw new Error(tokenData.error || 'Failed to initialize realtime session');
            }

            const peerConnection = new RTCPeerConnection();
            const remoteAudio = new Audio();
            remoteAudio.autoplay = true;
            remoteAudio.playsInline = true;
            remoteAudio.muted = !state.autoPlayAiAudio;
            remoteAudio.addEventListener('playing', () => {
                clearOpeningWatchdog();
                setStage('speaking', 'AI is speaking now.', 'Listen to the full question first, then answer in one short turn.', 'Assistant audio is playing.');
                waveform.startMockAnimation();
            });
            remoteAudio.addEventListener('error', () => {
                showStatus('Live audio output hit an error. Start the conversation again.', 'error');
            });

            peerConnection.addEventListener('connectionstatechange', () => {
                if (['failed', 'disconnected', 'closed'].includes(peerConnection.connectionState)) {
                    state.realtime.connected = false;
                    setMicEnabled(false);
                    updateConnectionStatus('Live voice disconnected');
                    if (!state.realtime.connecting) {
                        showStatus('Live voice disconnected. Start the conversation again to continue.', 'error');
                    }
                }
            });

            peerConnection.ontrack = (event) => {
                const [remoteStream] = event.streams;
                if (remoteStream) {
                    remoteAudio.srcObject = remoteStream;
                    remoteAudio.play().catch(() => { });
                }
            };

            stream.getTracks().forEach((track) => {
                peerConnection.addTrack(track, stream);
            });

            const dataChannel = peerConnection.createDataChannel('oai-events');
            dataChannel.addEventListener('message', handleRealtimeEvent);
            dataChannel.addEventListener('open', () => {
                state.realtime.connected = true;
                state.realtime.connecting = false;
                state.realtime.dataChannel = dataChannel;
                state.realtime.peerConnection = peerConnection;
                state.realtime.remoteAudio = remoteAudio;
                sendRealtimeEvent({
                    type: 'session.update',
                    session: {
                        audio: {
                            input: {
                                turn_detection: null,
                            },
                        },
                    },
                });
                updateConnectionStatus('Live voice connected');
                hideStatus();
                waveform.reset();
                setMicEnabled(false);

                const shouldOpen = forceOpeningTurn || !state.sessionHasMessages;
                if (shouldOpen) {
                    state.hasRequestedOpeningTurn = true;
                    setStage('processing', 'AI is opening the scene.', 'The model is starting the conversation first.', 'Opening turn in progress.');
                    requestAssistantTurn('Start the scene now with one short, natural Chinese opening line.');
                    scheduleOpeningWatchdog();
                } else {
                    setStage('ready', 'Live voice is connected.', 'Tap Start speaking when you are ready. The AI will wait until you stop talking.', 'Live session is ready.');
                }
            });
            dataChannel.addEventListener('close', () => {
                state.realtime.connected = false;
                state.realtime.connecting = false;
                setMicEnabled(false);
                updateConnectionStatus('Live voice disconnected');
                syncRealtimeButtons();
            });

            const offer = await peerConnection.createOffer();
            await peerConnection.setLocalDescription(offer);

            const sdpResponse = await fetch(REALTIME_CALLS_API_URL, {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${clientSecret}`,
                    'Content-Type': 'application/sdp',
                },
                body: offer.sdp,
            });
            if (!sdpResponse.ok) {
                const detail = (await sdpResponse.text()).trim().slice(0, 180);
                throw new Error(`OpenAI realtime handshake failed (${sdpResponse.status})${detail ? `: ${detail}` : ''}`);
            }

            const answerSdp = await sdpResponse.text();
            await peerConnection.setRemoteDescription({
                type: 'answer',
                sdp: answerSdp,
            });
        } catch (error) {
            console.error(error);
            closeRealtimeSession({ stopTracks: true });
            const friendlyError = describeRealtimeStartupError(error);
            showStatus(friendlyError, 'error');
            setStage('ready', 'Live connection failed.', friendlyError, 'Realtime connection is offline.');
            updateConnectionStatus('Live voice offline');
        } finally {
            state.realtime.connecting = false;
            syncRealtimeButtons();
        }
    }

    async function sendMessage(payload) {
        hideAllConfirmations();
        state.currentTranslationAudio = '';
        state.currentTranslationText = '';
        state.currentTranslationPinyin = '';
        let renderedInRealtime = false;

        if (isRealtimeChannelOpen()) {
            appendMessage('user', payload);
            renderedInRealtime = true;
            resetReplySuggestion('Waiting for the next hint...', { invalidatePending: true });
            await persistRealtimeMessage({
                senderType: 'user',
                transcript: payload.chinese_text,
                itemId: `text-${Date.now()}`,
                inputMethod: payload.input_method || 'text',
                englishTranslation: payload.english_translation || '',
            });
            setMicEnabled(false);
            showStatus('AI is replying...', 'loading');
            setStage('processing', 'AI is preparing the next live reply.', 'Wait for the reply to finish before speaking again.', 'Sending text turn into live session.');

            const created = sendRealtimeEvent({
                type: 'conversation.item.create',
                item: {
                    type: 'message',
                    role: 'user',
                    content: [{
                        type: 'input_text',
                        text: payload.chinese_text,
                    }],
                },
            });
            if (created) {
                requestAssistantTurn();
                return;
            }

            if (renderedInRealtime) {
                el.chatBox.lastElementChild?.remove();
            }
        }

        appendMessage('user', payload);
        showStatus('AI is replying...', 'loading');
        setStage('processing', 'AI is preparing the next reply.', 'Wait for the full audio reply before starting your next turn.', 'Generating response.');

        try {
            const response = await fetch(config.chatApiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': config.csrfToken,
                },
                body: JSON.stringify({
                    message: payload.chinese_text,
                    session_id: Number(config.sessionId),
                    input_method: payload.input_method || 'text',
                    english_translation: payload.english_translation || '',
                }),
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || 'AI reply failed');
            }

            appendMessage('ai', data.ai_response);
            resetReplySuggestion();
            hideStatus();
            state.currentAudioBase64 = data.tts_audio || '';
            if (data.tts_audio && state.autoPlayAiAudio) {
                await playFallbackAudio(data.tts_audio);
            } else {
                setStage('ready', 'AI replied in text.', 'Read the reply, then speak or type your next turn.', 'Fallback text reply complete.');
            }
        } catch (error) {
            console.error(error);
            showStatus('Failed to send the message. Please try again.', 'error');
            setStage('ready', 'Message sending failed.', 'Retry the same line or switch modes if the network is unstable.', 'Conversation state was not advanced.');
        }
    }

    async function translateEnglish(overrideText) {
        const english = (overrideText || el.englishInput.value).trim();
        if (!english) {
            return;
        }

        showStatus('Translating your English into Chinese...', 'loading');
        setStage('processing', 'Building a Chinese line for you.', 'Use this mode when you know what you want to say but need help phrasing it.', 'Translation mode active.');

        try {
            const response = await fetch(config.translateApiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': config.csrfToken,
                },
                body: JSON.stringify({ text: english }),
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Translation failed');
            }

            hideStatus();
            toggleTranslationEdit(false);
            state.currentTranslationAudio = data.tts_audio || '';
            state.currentTranslationPinyin = data.pinyin || '';
            state.currentTranslationText = data.chinese_text || '';
            state.confirmationEnglish = english;
            el.originalEnglishText.textContent = english;
            el.chineseTranslationText.textContent = data.chinese_text;
            el.translationArea.style.display = 'block';
            el.inputArea.style.display = 'none';
            updatePinyinVisibility(loadPreference(STORAGE_KEYS.pinyinVisible, true));

            if (data.pinyin) {
                el.pinyinSection.style.display = 'block';
                el.pinyinText.textContent = data.pinyin;
            } else {
                el.pinyinSection.style.display = 'none';
            }

            if (data.tts_audio && state.autoPlayAiAudio) {
                await playFallbackAudio(data.tts_audio);
            } else {
                setStage('ready', 'Translation ready.', 'Review the Chinese line, then send it if it matches what you want to say.', 'Translation mode is waiting for confirmation.');
            }
        } catch (error) {
            console.error(error);
            showStatus('Translation failed. Please try again.', 'error');
            setStage('ready', 'Translation did not complete.', 'Edit the English text and retry, or switch to direct Chinese input.', 'Translation mode is still available.');
        }
    }

    async function restartConversation() {
        const confirmed = window.confirm('Restart this scene and clear the current conversation?');
        if (!confirmed) {
            return;
        }

        showStatus('Restarting the scene...', 'loading');
        try {
            const useRealtimeReset = state.realtime.supported;
            const response = await fetch(config.restartSessionApiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': config.csrfToken,
                },
                body: JSON.stringify({
                    session_id: Number(config.sessionId),
                    skip_opening_message: useRealtimeReset,
                }),
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Restart failed');
            }

            el.chatBox.innerHTML = '';
            ensureEmptyState();
            config.conversationHistory = [];
            clearRealtimePersistenceState();
            state.sessionHasMessages = false;
            hideAllConfirmations();
            stopFallbackAudio();

            if (useRealtimeReset) {
                closeRealtimeSession({ stopTracks: true });
                await startLiveSession({ forceOpeningTurn: true });
                return;
            }

            if (data.opening_message) {
                appendMessage('ai', data.opening_message);
                state.currentAudioBase64 = data.opening_message.tts_audio || '';
                hideStatus();
                if (data.opening_message.tts_audio && state.autoPlayAiAudio) {
                    await playFallbackAudio(data.opening_message.tts_audio);
                }
            }
        } catch (error) {
            console.error(error);
            showStatus('Could not restart the conversation.', 'error');
        }
    }

    async function replayCurrentAudio(playbackRate) {
        const base64Audio = state.currentTranslationAudio || state.currentAudioBase64;
        if (!base64Audio) {
            return;
        }
        await playFallbackAudio(base64Audio, { playbackRate, forcePlayback: true });
    }

    function bindEvents() {
        state.autoPlayAiAudio = true;
        savePreference(STORAGE_KEYS.autoPlay, true);
        el.autoPlayToggle.checked = state.autoPlayAiAudio;
        el.autoPlayToggle.addEventListener('change', (event) => {
            state.autoPlayAiAudio = event.target.checked;
            savePreference(STORAGE_KEYS.autoPlay, state.autoPlayAiAudio);
            if (state.realtime.remoteAudio) {
                state.realtime.remoteAudio.muted = !state.autoPlayAiAudio;
            }
            setStage('ready', state.autoPlayAiAudio ? 'AI audio will auto-play.' : 'AI audio auto-play is off.', 'You can still replay every AI line manually.', state.autoPlayAiAudio ? 'Replies will speak automatically.' : 'Replies will stay silent until you press replay.');
        });

        el.startLiveSessionBtn.addEventListener('click', () => startLiveSession({ forceOpeningTurn: !state.sessionHasMessages }));
        el.reconnectLiveSessionBtn.addEventListener('click', () => startLiveSession({ forceOpeningTurn: !state.sessionHasMessages }));

        el.voiceModeBtn.addEventListener('click', () => setMode('voice'));
        el.chineseModeBtn.addEventListener('click', () => setMode('chinese'));
        el.englishModeBtn.addEventListener('click', () => setMode('english'));

        [el.chineseInput, el.englishInput].forEach((textarea) => {
            if (textarea) {
                textarea.addEventListener('input', () => autoResize(textarea));
            }
        });

        el.recordBtn.addEventListener('click', async () => {
            if (!state.realtime.connected) {
                await startLiveSession({ forceOpeningTurn: !state.sessionHasMessages });
                return;
            }
            state.manualMute = false;
            sendRealtimeEvent({ type: 'input_audio_buffer.clear' });
            setMicEnabled(true);
            resetReplySuggestion('Waiting for the next hint...', { invalidatePending: true });
            setStage('listening', 'Speak now.', 'Say one short Chinese reply. Tap Stop talking when you are done.', 'Listening for your answer.');
        });

        el.stopBtn.addEventListener('click', () => {
            state.manualMute = true;
            setMicEnabled(false);
            setStage('processing', 'Processing your reply.', 'Please wait while the AI prepares the next line.', 'Sending your answer.');
            const committed = commitUserAudioTurn();
            if (!committed) {
                setStage('ready', 'Live voice is not connected.', 'Start the conversation again before trying another spoken turn.', 'Voice session is offline.');
            }
        });

        el.sendChineseBtn.addEventListener('click', () => {
            const chinese = el.chineseInput.value.trim();
            if (!chinese) {
                return;
            }
            sendMessage({ chinese_text: chinese, input_method: 'text' });
            el.chineseInput.value = '';
            autoResize(el.chineseInput);
        });
        el.chineseInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                el.sendChineseBtn.click();
            }
        });

        el.translateBtn.addEventListener('click', translateEnglish);
        el.englishInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                translateEnglish();
            }
        });

        el.confirmTranslationSendBtn.addEventListener('click', () => {
            sendMessage({
                chinese_text: state.currentTranslationText,
                english_translation: state.confirmationEnglish,
                input_method: 'translation',
            });
            el.translationArea.style.display = 'none';
            el.inputArea.style.display = 'block';
            el.englishInput.value = '';
            autoResize(el.englishInput);
        });
        el.editTranslationBtn.addEventListener('click', () => toggleTranslationEdit());
        el.saveTranslationEditBtn.addEventListener('click', saveTranslationEdit);
        el.cancelTranslationEditBtn.addEventListener('click', cancelTranslationEdit);
        el.retranslateTranslationBtn.addEventListener('click', () => translateEnglish(state.confirmationEnglish));

        el.playTtsBtn.addEventListener('click', () => replayCurrentAudio(1));
        el.replayTtsBtn.addEventListener('click', () => replayCurrentAudio(1));
        el.slowTtsBtn.addEventListener('click', () => replayCurrentAudio(0.72));
        el.stopTtsBtn.addEventListener('click', stopFallbackAudio);
        if (el.playSuggestionBtn) {
            el.playSuggestionBtn.addEventListener('click', async () => {
                if (!state.currentSuggestedReplyAudio) {
                    return;
                }
                await playFallbackAudio(state.currentSuggestedReplyAudio, {
                    forcePlayback: true,
                    rememberAsCurrent: false,
                    statusTitle: 'Playing the suggested reply.',
                    statusHint: 'Listen once, then repeat it or adapt it in your own words.',
                    statusFooter: 'Suggested reply audio is playing.',
                });
            });
        }
        if (el.teachReplyBtn) {
            el.teachReplyBtn.addEventListener('click', async () => {
                const latestAiTexts = el.chatBox?.querySelectorAll('.chat-message.ai .chinese-text');
                const latestAiLine = latestAiTexts && latestAiTexts.length > 0 ?
                    String(latestAiTexts[latestAiTexts.length - 1].textContent || '').trim() : '';

                if (!latestAiLine) {
                    return;
                }
                await fetchReplySuggestion(latestAiLine);
            });
        }
        el.togglePinyinBtn.addEventListener('click', () => {
            const currentlyVisible = loadPreference(STORAGE_KEYS.pinyinVisible, true);
            updatePinyinVisibility(!currentlyVisible);
        });

        el.restartBtn.addEventListener('click', restartConversation);
        el.changeTopicBtn.addEventListener('click', () => {
            if (window.confirm('Leave this conversation and choose a different scene?')) {
                closeRealtimeSession({ stopTracks: true });
                window.location.href = config.sceneSelectionUrl;
            }
        });

        window.addEventListener('beforeunload', () => {
            closeRealtimeSession({ stopTracks: true });
        });
    }

    function init() {
        bindEvents();
        attachFallbackAudioLifecycle();
        setMode('voice');
        hideAllConfirmations();
        scrollToBottom();
        waveform.reset();
        resetReplySuggestion();
        setMicEnabled(false);
        syncRealtimeButtons();
        updatePinyinVisibility(loadPreference(STORAGE_KEYS.pinyinVisible, true));

        if (!state.realtime.supported) {
            updateConnectionStatus('Live voice unsupported');
            setStage('ready', 'This browser cannot run live voice.', 'Use a modern browser for realtime speech. Text input still works here.', 'Fallback mode only.');
            return;
        }

        updateConnectionStatus('Live voice offline');
        setStage('idle', 'Start once, then let the AI speak first.', 'After the opening question, tap Start speaking when you want to answer, then tap Stop talking to send your turn.', 'Press "Start Conversation" to begin.');
        if (el.feedbackMessage) {
            el.feedbackMessage.innerHTML = '<i class="fas fa-info-circle"></i><span>The AI speaks first. After that, it waits quietly until you choose to answer.</span>';
        }
    }

    document.addEventListener('DOMContentLoaded', init);
})();
