(function () {
    const config = window.speakPracticeConfig;
    if (!config) {
        return;
    }

    const STORAGE_KEYS = {
        autoPlay: 'speak_practice_auto_play_ai_audio',
        pinyinVisible: 'speak_practice_pinyin_visible',
    };

    const state = {
        mode: 'voice',
        mediaRecorder: null,
        mediaStream: null,
        chunks: [],
        isRecording: false,
        currentAudioBase64: '',
        currentTranslationAudio: '',
        currentTranslationPinyin: '',
        currentTranslationText: '',
        confirmationEnglish: '',
        isEditingTranscript: false,
        recorderStartAt: null,
        recorderTimer: null,
        hasAttemptedInitialAutoplay: false,
        autoPlayAiAudio: loadPreference(STORAGE_KEYS.autoPlay, true),
    };

    const el = {
        chatBox: document.getElementById('chat-box'),
        statusIndicator: document.getElementById('status-indicator'),
        statusIcon: document.getElementById('status-icon'),
        statusText: document.getElementById('status-text'),
        statusProgress: document.getElementById('status-progress'),
        voiceStage: document.getElementById('voice-stage'),
        voiceStagePill: document.getElementById('voice-stage-pill'),
        voiceStageStatus: document.getElementById('voice-stage-status'),
        voiceStageHint: document.getElementById('voice-stage-hint'),
        voiceStageFooter: document.getElementById('voice-stage-footer-text'),
        voiceTimer: document.getElementById('recording-timer-inline'),
        autoPlayToggle: document.getElementById('auto-play-toggle'),
        waveformBars: Array.from(document.querySelectorAll('.voice-wave-bar')),
        voiceModeBtn: document.getElementById('voice-mode-btn'),
        chineseModeBtn: document.getElementById('chinese-mode-btn'),
        englishModeBtn: document.getElementById('english-mode-btn'),
        voiceInputArea: document.getElementById('voice-input-area'),
        chineseInputArea: document.getElementById('chinese-input-area'),
        englishInputArea: document.getElementById('english-input-area'),
        recordBtn: document.getElementById('record-btn'),
        stopBtn: document.getElementById('stop-btn'),
        chineseInput: document.getElementById('chinese-text-input'),
        englishInput: document.getElementById('english-text-input'),
        sendChineseBtn: document.getElementById('send-chinese-btn'),
        translateBtn: document.getElementById('translate-btn'),
        inputArea: document.getElementById('input-area'),
        confirmationArea: document.getElementById('confirmation-area'),
        transcribedText: document.getElementById('transcribed-text'),
        transcribedEditor: document.getElementById('transcribed-text-editor'),
        englishTranslation: document.getElementById('english-translation'),
        confirmSendBtn: document.getElementById('confirm-send-btn'),
        rerecordBtn: document.getElementById('rerecord-btn'),
        editTextBtn: document.getElementById('edit-text-btn'),
        editActions: document.getElementById('edit-actions'),
        saveEditBtn: document.getElementById('save-edit-btn'),
        cancelEditBtn: document.getElementById('cancel-edit-btn'),
        retranslateBtn: document.getElementById('retranslate-btn'),
        translationArea: document.getElementById('translation-confirmation-area'),
        originalEnglishText: document.getElementById('original-english-text'),
        chineseTranslationText: document.getElementById('chinese-translation-text'),
        confirmTranslationSendBtn: document.getElementById('confirm-translation-send-btn'),
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
    };

    class WaveformController {
        constructor(bars, audioElement) {
            this.bars = bars;
            this.audioElement = audioElement;
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

        async bindAudioPlayback() {
            this.cleanupSource();
            this.startMockAnimation();
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

    const waveform = new WaveformController(el.waveformBars, el.ttsAudio);

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
        el.voiceStage.classList.remove('is-idle', 'is-listening', 'is-processing', 'is-speaking', 'is-ready');
        el.voiceStage.classList.add(`is-${stateName}`);
        el.voiceStageStatus.textContent = status;
        el.voiceStageHint.textContent = hint;
        el.voiceStageFooter.textContent = footer;

        const pillMap = {
            idle: ['fa-headphones', 'AI opens first'],
            ready: ['fa-circle-play', 'Your turn next'],
            listening: ['fa-microphone-lines', 'Listening now'],
            processing: ['fa-wand-magic-sparkles', 'Transcribing'],
            speaking: ['fa-volume-high', 'AI speaking'],
        };

        const [icon, label] = pillMap[stateName] || pillMap.idle;
        el.voiceStagePill.innerHTML = `<i class="fas ${icon}"></i><span>${label}</span>`;
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

        if (mode === 'chinese') {
            el.chineseInput.focus();
        } else if (mode === 'english') {
            el.englishInput.focus();
        }
    }

    function appendMessage(sender, payload) {
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
        scrollToBottom();
    }

    function hideAllConfirmations() {
        el.confirmationArea.style.display = 'none';
        el.translationArea.style.display = 'none';
        el.inputArea.style.display = 'flex';
        state.isEditingTranscript = false;
        el.transcribedEditor.style.display = 'none';
        el.transcribedText.style.display = 'inline';
        el.editActions.style.display = 'none';
    }

    function showVoiceConfirmation(chineseText, englishText) {
        hideAllConfirmations();
        el.transcribedText.textContent = chineseText;
        el.englishTranslation.textContent = englishText;
        el.confirmationArea.style.display = 'block';
        el.inputArea.style.display = 'none';
        setStage('ready', 'Review your transcript, then send it.', 'Best practice: make one short spoken turn, confirm the transcript, then continue.', 'Edit the transcript if the recognition missed a word.');
        scrollToBottom();
    }

    function showTranslationConfirmation(originalEnglish, chineseText, ttsAudio, pinyin) {
        hideAllConfirmations();
        state.currentTranslationAudio = ttsAudio || '';
        state.currentTranslationPinyin = pinyin || '';
        state.currentTranslationText = chineseText || '';
        state.confirmationEnglish = originalEnglish || '';

        el.originalEnglishText.textContent = originalEnglish;
        el.chineseTranslationText.textContent = chineseText;
        el.translationArea.style.display = 'block';
        el.inputArea.style.display = 'none';
        updatePinyinVisibility(loadPreference(STORAGE_KEYS.pinyinVisible, true));

        if (pinyin) {
            el.pinyinSection.style.display = 'block';
            el.pinyinText.textContent = pinyin;
        } else {
            el.pinyinSection.style.display = 'none';
        }

        if (ttsAudio && state.autoPlayAiAudio) {
            playAudio(ttsAudio, { playbackRate: 1 });
        }

        setStage('ready', 'Translation ready.', 'Listen once, then send the Chinese line if it matches what you want to say.', 'Use slow playback if you want to shadow the pronunciation.');
        scrollToBottom();
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

    async function playAudio(base64Audio, options = {}) {
        if (!base64Audio) {
            return false;
        }

        const playbackRate = options.playbackRate || 1;
        el.ttsAudio.pause();
        el.ttsAudio.currentTime = 0;
        el.ttsAudio.src = `data:audio/mp3;base64,${base64Audio}`;
        el.ttsAudio.playbackRate = playbackRate;
        state.currentAudioBase64 = base64Audio;

        setStage('speaking', 'AI is speaking now.', 'Listen to the full line first. When the audio ends, answer with one idea at a time.', playbackRate < 1 ? 'Slow pronunciation playback is active.' : 'Natural-speed pronunciation is active.');
        waveform.startMockAnimation();
        try {
            await waveform.bindAudioPlayback();
        } catch (error) {
            waveform.startMockAnimation();
        }

        try {
            await el.ttsAudio.play();
            return true;
        } catch (error) {
            waveform.reset();
            setStage('ready', 'Tap replay to hear the line.', 'Your browser blocked autoplay. Use the replay button once to unlock audio.', 'Audio is ready but needs a user tap.');
            return false;
        }
    }

    function stopAudio() {
        el.ttsAudio.pause();
        el.ttsAudio.currentTime = 0;
        waveform.reset();
        setStage('ready', 'AI audio stopped.', 'You can replay the line, slow it down, or start speaking.', 'Ready for your next turn.');
    }

    function attachAudioLifecycle() {
        el.ttsAudio.addEventListener('ended', () => {
            waveform.reset();
            setStage('ready', 'Your turn to speak.', 'Tap the microphone and answer in one short turn. Short turns improve recognition and pacing.', 'The mic is ready when you are.');
            if (el.feedbackMessage) {
                el.feedbackMessage.innerHTML = '<i class="fas fa-check-circle"></i><span>Playback complete. Try repeating the line or answer naturally.</span>';
            }
        });

        el.ttsAudio.addEventListener('pause', () => {
            if (!el.ttsAudio.ended && el.ttsAudio.currentTime > 0) {
                waveform.reset();
            }
        });
    }

    async function ensureMicrophone() {
        if (state.mediaStream) {
            return state.mediaStream;
        }

        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
            },
        });
        state.mediaStream = stream;
        return stream;
    }

    function startRecorderTimer() {
        stopRecorderTimer();
        state.recorderStartAt = Date.now();
        state.recorderTimer = window.setInterval(() => {
            const seconds = Math.floor((Date.now() - state.recorderStartAt) / 1000);
            const mm = String(Math.floor(seconds / 60)).padStart(2, '0');
            const ss = String(seconds % 60).padStart(2, '0');
            el.voiceTimer.textContent = `${mm}:${ss}`;
        }, 200);
    }

    function stopRecorderTimer() {
        if (state.recorderTimer) {
            window.clearInterval(state.recorderTimer);
            state.recorderTimer = null;
        }
        el.voiceTimer.textContent = '00:00';
    }

    async function startRecording() {
        if (state.isRecording) {
            return;
        }

        try {
            stopAudio();
            const stream = await ensureMicrophone();
            const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm';

            state.chunks = [];
            state.mediaRecorder = new MediaRecorder(stream, { mimeType });
            state.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    state.chunks.push(event.data);
                }
            };
            state.mediaRecorder.onstop = async () => {
                state.isRecording = false;
                stopRecorderTimer();
                el.recordBtn.style.display = 'flex';
                el.stopBtn.style.display = 'none';
                const audioBlob = new Blob(state.chunks, { type: state.mediaRecorder.mimeType });
                state.chunks = [];
                waveform.reset();
                setStage('processing', 'Transcribing your speech...', 'Hold on while the system checks the Chinese transcript before sending.', 'Processing voice input.');
                showStatus('Transcribing your speech...', 'loading');
                await transcribeAudio(audioBlob);
            };

            await waveform.bindMicrophoneStream(stream);
            state.mediaRecorder.start();
            state.isRecording = true;
            el.recordBtn.style.display = 'none';
            el.stopBtn.style.display = 'flex';
            startRecorderTimer();
            waveform.startVisualizer();
            setStage('listening', 'Listening to your voice now.', 'Speak clearly in one sentence or one idea. Stop when you finish.', 'Short, clear turns improve recognition.');
            showStatus('Listening...', 'loading');
        } catch (error) {
            console.error(error);
            showStatus('Microphone access is required for voice practice.', 'error');
            setStage('ready', 'Microphone permission was blocked.', 'Allow mic access, then try again. You can still type in Chinese or English.', 'Voice input is waiting for permission.');
        }
    }

    function stopRecording() {
        if (state.mediaRecorder && state.isRecording) {
            state.mediaRecorder.stop();
        }
    }

    async function transcribeAudio(audioBlob) {
        try {
            const formData = new FormData();
            formData.append('audio', audioBlob, `recording-${Date.now()}.webm`);
            const response = await fetch(config.transcribeApiUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': config.csrfToken,
                },
                body: formData,
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Transcription failed');
            }
            hideStatus();
            showVoiceConfirmation(data.chinese_text, data.english_translation);
        } catch (error) {
            console.error(error);
            showStatus('Voice recognition failed. Please try again.', 'error');
            setStage('ready', 'Could not transcribe that turn.', 'Try a shorter sentence, reduce background noise, or use text input for this turn.', 'Voice practice is still available.');
        }
    }

    async function sendMessage(payload) {
        appendMessage('user', payload);
        hideAllConfirmations();
        state.currentTranslationAudio = '';
        state.currentTranslationText = '';
        state.currentTranslationPinyin = '';
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
            hideStatus();
            state.currentAudioBase64 = data.tts_audio || '';
            if (data.tts_audio && state.autoPlayAiAudio) {
                await playAudio(data.tts_audio);
            } else {
                setStage('ready', 'AI replied in text.', 'Read the reply, then use replay if you want to hear it or answer directly.', 'Audio auto-play is turned off.');
            }
        } catch (error) {
            console.error(error);
            showStatus('Failed to send the message. Please try again.', 'error');
            setStage('ready', 'Message sending failed.', 'Retry the same line or switch to text mode if the network is unstable.', 'Conversation state was not advanced.');
        }
    }

    async function translateEnglish() {
        const english = el.englishInput.value.trim();
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
            showTranslationConfirmation(english, data.chinese_text, data.tts_audio, data.pinyin);
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
            const response = await fetch(config.restartSessionApiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': config.csrfToken,
                },
                body: JSON.stringify({ session_id: Number(config.sessionId) }),
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Restart failed');
            }

            el.chatBox.innerHTML = '';
            appendMessage('ai', data.opening_message);
            hideStatus();
            state.currentAudioBase64 = data.tts_audio || '';

            if (data.tts_audio && state.autoPlayAiAudio) {
                await playAudio(data.tts_audio);
            } else {
                setStage('ready', 'Scene restarted.', 'The AI opening line is ready. Replay it if needed, then answer.', 'Fresh conversation started.');
            }
        } catch (error) {
            console.error(error);
            showStatus('Could not restart the conversation.', 'error');
        }
    }

    function toggleTranscriptEdit() {
        state.isEditingTranscript = !state.isEditingTranscript;
        el.transcribedEditor.style.display = state.isEditingTranscript ? 'block' : 'none';
        el.transcribedText.style.display = state.isEditingTranscript ? 'none' : 'inline';
        el.editActions.style.display = state.isEditingTranscript ? 'flex' : 'none';
        el.transcribedEditor.value = el.transcribedText.textContent;
        if (state.isEditingTranscript) {
            el.transcribedEditor.focus();
            autoResize(el.transcribedEditor);
        }
    }

    function saveTranscriptEdit() {
        const nextValue = el.transcribedEditor.value.trim();
        if (!nextValue) {
            return;
        }
        el.transcribedText.textContent = nextValue;
        toggleTranscriptEdit();
    }

    function cancelTranscriptEdit() {
        state.isEditingTranscript = false;
        el.transcribedEditor.style.display = 'none';
        el.transcribedText.style.display = 'inline';
        el.editActions.style.display = 'none';
    }

    async function replayCurrentAudio(playbackRate) {
        const base64Audio = state.currentTranslationAudio || state.currentAudioBase64;
        if (!base64Audio) {
            return;
        }
        await playAudio(base64Audio, { playbackRate });
    }

    function bindEvents() {
        el.autoPlayToggle.checked = state.autoPlayAiAudio;
        el.autoPlayToggle.addEventListener('change', (event) => {
            state.autoPlayAiAudio = event.target.checked;
            savePreference(STORAGE_KEYS.autoPlay, state.autoPlayAiAudio);
            setStage('ready', state.autoPlayAiAudio ? 'AI audio will auto-play.' : 'AI audio auto-play is off.', 'You can still replay every AI line manually.', state.autoPlayAiAudio ? 'Replies will speak automatically.' : 'Replies will stay silent until you press replay.');
        });

        el.voiceModeBtn.addEventListener('click', () => setMode('voice'));
        el.chineseModeBtn.addEventListener('click', () => setMode('chinese'));
        el.englishModeBtn.addEventListener('click', () => setMode('english'));

        [el.chineseInput, el.englishInput, el.transcribedEditor].forEach((textarea) => {
            if (textarea) {
                textarea.addEventListener('input', () => autoResize(textarea));
            }
        });

        el.recordBtn.addEventListener('click', startRecording);
        el.stopBtn.addEventListener('click', stopRecording);
        el.confirmSendBtn.addEventListener('click', () => sendMessage({
            chinese_text: el.transcribedText.textContent.trim(),
            english_translation: el.englishTranslation.textContent.trim(),
            input_method: 'voice',
        }));
        el.rerecordBtn.addEventListener('click', () => {
            hideAllConfirmations();
            setStage('ready', 'Ready for another recording.', 'Tap the microphone and try a shorter or clearer turn.', 'Voice input reset.');
        });
        el.editTextBtn.addEventListener('click', toggleTranscriptEdit);
        el.saveEditBtn.addEventListener('click', saveTranscriptEdit);
        el.cancelEditBtn.addEventListener('click', cancelTranscriptEdit);
        el.retranslateBtn.addEventListener('click', async () => {
            const text = el.transcribedEditor.value.trim();
            if (!text) {
                return;
            }
            showStatus('Refreshing the English gloss...', 'loading');
            try {
                const response = await fetch(config.translateChineseApiUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': config.csrfToken,
                    },
                    body: JSON.stringify({ chinese_text: text }),
                });
                const data = await response.json();
                if (!response.ok || !data.success) {
                    throw new Error(data.error || 'Re-translation failed');
                }
                el.transcribedText.textContent = text;
                el.englishTranslation.textContent = data.english_translation;
                cancelTranscriptEdit();
                hideStatus();
            } catch (error) {
                console.error(error);
                showStatus('Could not refresh the English gloss.', 'error');
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
            el.englishInput.value = '';
            autoResize(el.englishInput);
        });

        el.playTtsBtn.addEventListener('click', () => replayCurrentAudio(1));
        el.replayTtsBtn.addEventListener('click', () => replayCurrentAudio(1));
        el.slowTtsBtn.addEventListener('click', () => replayCurrentAudio(0.72));
        el.stopTtsBtn.addEventListener('click', stopAudio);
        el.togglePinyinBtn.addEventListener('click', () => {
            const currentlyVisible = loadPreference(STORAGE_KEYS.pinyinVisible, true);
            updatePinyinVisibility(!currentlyVisible);
        });

        el.restartBtn.addEventListener('click', restartConversation);
        el.changeTopicBtn.addEventListener('click', () => {
            if (window.confirm('Leave this conversation and choose a different scene?')) {
                window.location.href = config.sceneSelectionUrl;
            }
        });
    }

    async function attemptInitialAutoplay() {
        if (state.hasAttemptedInitialAutoplay || !config.initialAiAudio) {
            return;
        }
        state.hasAttemptedInitialAutoplay = true;
        state.currentAudioBase64 = config.initialAiAudio;
        if (state.autoPlayAiAudio) {
            await playAudio(config.initialAiAudio);
        } else {
            setStage('ready', 'AI greeting is ready.', 'Auto-play is off, so press replay if you want to hear the opening line.', 'The first AI line is already on screen.');
        }
    }

    function init() {
        bindEvents();
        attachAudioLifecycle();
        setMode('voice');
        hideAllConfirmations();
        scrollToBottom();
        waveform.reset();
        setStage('idle', 'AI is ready to start the scene.', 'Listen to the first line, then reply with one short spoken turn. This keeps the practice natural and easy to follow.', 'Voice-first practice works best with short back-and-forth turns.');
        if (el.feedbackMessage) {
            el.feedbackMessage.innerHTML = '<i class="fas fa-info-circle"></i><span>Replay the line, slow it down, or answer when you are ready.</span>';
        }

        window.setTimeout(() => {
            attemptInitialAutoplay();
        }, 450);
    }

    document.addEventListener('DOMContentLoaded', init);
})();
