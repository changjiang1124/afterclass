// --- AudioProcessor Class ---
class AudioProcessor {
    constructor(options = {}) {
        this.maxFileSize = options.maxFileSize || 10 * 1024 * 1024; // 10MB 默认最大文件大小
        this.targetSampleRate = options.targetSampleRate || 16000; // 16kHz 目标采样率
        this.compressionQuality = options.compressionQuality || 0.8; // 压缩质量
    }
    
    /**
     * 处理音频Blob，进行格式转换和压缩 (Process audio blob with format conversion and compression)
     */
    async processAudioBlob(audioBlob) {
        try {
            // 检查文件大小 (Check file size)
            if (audioBlob.size > this.maxFileSize) {
                throw new Error(`Audio file too large: ${(audioBlob.size / 1024 / 1024).toFixed(2)}MB. Maximum allowed: ${(this.maxFileSize / 1024 / 1024).toFixed(2)}MB`);
            }
            
            // 如果浏览器支持，尝试压缩音频 (Try to compress audio if browser supports it)
            const processedBlob = await this.compressAudio(audioBlob);
            
            return {
                blob: processedBlob,
                size: processedBlob.size,
                type: processedBlob.type,
                duration: await this.getAudioDuration(processedBlob)
            };
            
        } catch (error) {
            console.warn('Audio processing failed, using original blob:', error);
            // 如果处理失败，返回原始blob (If processing fails, return original blob)
            return {
                blob: audioBlob,
                size: audioBlob.size,
                type: audioBlob.type,
                duration: await this.getAudioDuration(audioBlob)
            };
        }
    }
    
    /**
     * 压缩音频文件 (Compress audio file)
     */
    async compressAudio(audioBlob) {
        // 对于WebM格式，直接返回（已经是压缩格式）
        if (audioBlob.type.includes('webm')) {
            return audioBlob;
        }
        
        // 对于其他格式，尝试转换为WebM
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const arrayBuffer = await audioBlob.arrayBuffer();
            const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
            
            // 降采样到目标采样率 (Downsample to target sample rate)
            const resampledBuffer = await this.resampleAudioBuffer(audioBuffer, this.targetSampleRate);
            
            // 转换回Blob (Convert back to Blob)
            const compressedBlob = await this.audioBufferToBlob(resampledBuffer);
            
            audioContext.close();
            return compressedBlob;
            
        } catch (error) {
            console.warn('Audio compression failed:', error);
            return audioBlob;
        }
    }
    
    /**
     * 重采样音频缓冲区 (Resample audio buffer)
     */
    async resampleAudioBuffer(audioBuffer, targetSampleRate) {
        if (audioBuffer.sampleRate === targetSampleRate) {
            return audioBuffer;
        }
        
        const offlineContext = new OfflineAudioContext(
            audioBuffer.numberOfChannels,
            audioBuffer.duration * targetSampleRate,
            targetSampleRate
        );
        
        const source = offlineContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(offlineContext.destination);
        source.start();
        
        return await offlineContext.startRendering();
    }
    
    /**
     * 将音频缓冲区转换为Blob (Convert audio buffer to blob)
     */
    async audioBufferToBlob(audioBuffer) {
        // 这是一个简化的实现，实际项目中可能需要更复杂的编码
        const numberOfChannels = audioBuffer.numberOfChannels;
        const length = audioBuffer.length * numberOfChannels * 2; // 16-bit samples
        const buffer = new ArrayBuffer(44 + length);
        const view = new DataView(buffer);
        
        // WAV header
        const writeString = (offset, string) => {
            for (let i = 0; i < string.length; i++) {
                view.setUint8(offset + i, string.charCodeAt(i));
            }
        };
        
        writeString(0, 'RIFF');
        view.setUint32(4, 36 + length, true);
        writeString(8, 'WAVE');
        writeString(12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, numberOfChannels, true);
        view.setUint32(24, audioBuffer.sampleRate, true);
        view.setUint32(28, audioBuffer.sampleRate * numberOfChannels * 2, true);
        view.setUint16(32, numberOfChannels * 2, true);
        view.setUint16(34, 16, true);
        writeString(36, 'data');
        view.setUint32(40, length, true);
        
        // Convert audio data
        let offset = 44;
        for (let i = 0; i < audioBuffer.length; i++) {
            for (let channel = 0; channel < numberOfChannels; channel++) {
                const sample = Math.max(-1, Math.min(1, audioBuffer.getChannelData(channel)[i]));
                view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
                offset += 2;
            }
        }
        
        return new Blob([buffer], { type: 'audio/wav' });
    }
    
    /**
     * 获取音频时长 (Get audio duration)
     */
    async getAudioDuration(audioBlob) {
        return new Promise((resolve) => {
            const audio = new Audio();
            audio.addEventListener('loadedmetadata', () => {
                resolve(audio.duration || 0);
            });
            audio.addEventListener('error', () => {
                resolve(0);
            });
            audio.src = URL.createObjectURL(audioBlob);
        });
    }
    
    /**
     * 创建FormData用于上传 (Create FormData for upload)
     */
    createFormData(processedAudio, additionalData = {}) {
        const formData = new FormData();
        
        // 添加音频文件 (Add audio file)
        const filename = `recording_${Date.now()}.${this.getFileExtension(processedAudio.type)}`;
        formData.append('audio', processedAudio.blob, filename);
        
        // 添加元数据 (Add metadata)
        formData.append('duration', processedAudio.duration.toString());
        formData.append('size', processedAudio.size.toString());
        formData.append('type', processedAudio.type);
        
        // 添加额外数据 (Add additional data)
        Object.keys(additionalData).forEach(key => {
            formData.append(key, additionalData[key]);
        });
        
        return formData;
    }
    
    /**
     * 获取文件扩展名 (Get file extension)
     */
    getFileExtension(mimeType) {
        const extensions = {
            'audio/webm': 'webm',
            'audio/mp4': 'm4a',
            'audio/ogg': 'ogg',
            'audio/wav': 'wav'
        };
        return extensions[mimeType] || 'webm';
    }
    
    /**
     * 验证音频文件 (Validate audio file)
     */
    validateAudioFile(audioBlob) {
        const errors = [];
        
        // 检查文件大小 (Check file size)
        if (audioBlob.size === 0) {
            errors.push('Audio file is empty');
        }
        
        if (audioBlob.size > this.maxFileSize) {
            errors.push(`File too large: ${(audioBlob.size / 1024 / 1024).toFixed(2)}MB`);
        }
        
        // 检查MIME类型 (Check MIME type)
        const supportedTypes = ['audio/webm', 'audio/mp4', 'audio/ogg', 'audio/wav'];
        if (!supportedTypes.some(type => audioBlob.type.includes(type.split('/')[1]))) {
            errors.push(`Unsupported audio format: ${audioBlob.type}`);
        }
        
        return {
            isValid: errors.length === 0,
            errors: errors
        };
    }
}

// --- VoiceRecorder Class ---
class VoiceRecorder {
    constructor(options = {}) {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.stream = null;
        this.recordingStartTime = null;
        
        // 回调函数 (Callback functions)
        this.onRecordingStart = options.onRecordingStart || (() => {});
        this.onRecordingStop = options.onRecordingStop || (() => {});
        this.onError = options.onError || ((error) => console.error('VoiceRecorder Error:', error));
        this.onDataAvailable = options.onDataAvailable || (() => {});
        
        // 配置选项 (Configuration options)
        this.mimeType = this.getSupportedMimeType();
        this.maxRecordingTime = options.maxRecordingTime || 60000; // 60秒最大录制时间
        this.recordingTimer = null;
    }
    
    /**
     * 获取支持的音频MIME类型 (Get supported audio MIME type)
     */
    getSupportedMimeType() {
        const types = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/mp4',
            'audio/ogg;codecs=opus'
        ];
        
        for (const type of types) {
            if (MediaRecorder.isTypeSupported(type)) {
                return type;
            }
        }
        
        return 'audio/webm'; // 默认回退类型
    }
    
    /**
     * 检查浏览器是否支持录音功能 (Check if browser supports recording)
     */
    static isSupported() {
        return !!(navigator.mediaDevices && 
                 navigator.mediaDevices.getUserMedia && 
                 window.MediaRecorder);
    }
    
    /**
     * 请求麦克风权限并开始录音 (Request microphone permission and start recording)
     */
    async startRecording() {
        if (this.isRecording) {
            this.onError(new Error('Recording is already in progress'));
            return false;
        }
        
        if (!VoiceRecorder.isSupported()) {
            this.onError(new Error('Voice recording is not supported in this browser'));
            return false;
        }
        
        try {
            // 请求麦克风权限 (Request microphone permission)
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            
            // 创建MediaRecorder实例 (Create MediaRecorder instance)
            this.mediaRecorder = new MediaRecorder(this.stream, {
                mimeType: this.mimeType
            });
            
            // 重置音频数据 (Reset audio data)
            this.audioChunks = [];
            this.recordingStartTime = Date.now();
            
            // 设置事件监听器 (Set up event listeners)
            this.mediaRecorder.addEventListener('dataavailable', (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                    this.onDataAvailable(event.data);
                }
            });
            
            this.mediaRecorder.addEventListener('stop', () => {
                this.handleRecordingStop();
            });
            
            this.mediaRecorder.addEventListener('error', (event) => {
                this.onError(new Error(`MediaRecorder error: ${event.error}`));
                this.cleanup();
            });
            
            // 开始录音 (Start recording)
            this.mediaRecorder.start(100); // 每100ms收集一次数据
            this.isRecording = true;
            
            // 设置最大录制时间定时器 (Set maximum recording time timer)
            this.recordingTimer = setTimeout(() => {
                if (this.isRecording) {
                    this.stopRecording();
                }
            }, this.maxRecordingTime);
            
            this.onRecordingStart();
            return true;
            
        } catch (error) {
            this.onError(error);
            this.cleanup();
            return false;
        }
    }
    
    /**
     * 停止录音 (Stop recording)
     */
    stopRecording() {
        if (!this.isRecording || !this.mediaRecorder) {
            return false;
        }
        
        try {
            this.mediaRecorder.stop();
            this.isRecording = false;
            
            // 清除定时器 (Clear timer)
            if (this.recordingTimer) {
                clearTimeout(this.recordingTimer);
                this.recordingTimer = null;
            }
            
            return true;
        } catch (error) {
            this.onError(error);
            this.cleanup();
            return false;
        }
    }
    
    /**
     * 处理录音停止事件 (Handle recording stop event)
     */
    handleRecordingStop() {
        const recordingDuration = this.recordingStartTime ? 
            (Date.now() - this.recordingStartTime) / 1000 : 0;
            
        const audioBlob = this.getAudioBlob();
        
        this.cleanup();
        this.onRecordingStop(audioBlob, recordingDuration);
    }
    
    /**
     * 获取录制的音频Blob (Get recorded audio blob)
     */
    getAudioBlob() {
        if (this.audioChunks.length === 0) {
            return null;
        }
        
        return new Blob(this.audioChunks, { 
            type: this.mimeType 
        });
    }
    
    /**
     * 获取录制时长（秒） (Get recording duration in seconds)
     */
    getRecordingDuration() {
        return this.recordingStartTime ? 
            (Date.now() - this.recordingStartTime) / 1000 : 0;
    }
    
    /**
     * 清理资源 (Cleanup resources)
     */
    cleanup() {
        // 停止所有音频轨道 (Stop all audio tracks)
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        // 清除定时器 (Clear timer)
        if (this.recordingTimer) {
            clearTimeout(this.recordingTimer);
            this.recordingTimer = null;
        }
        
        // 重置状态 (Reset state)
        this.mediaRecorder = null;
        this.isRecording = false;
        this.recordingStartTime = null;
    }
    
    /**
     * 销毁录音器实例 (Destroy recorder instance)
     */
    destroy() {
        if (this.isRecording) {
            this.stopRecording();
        }
        this.cleanup();
    }
}

function initializeChat(sessionId, chatApiUrl, transcribeApiUrl, translateApiUrl, translateChineseApiUrl, csrfToken) {
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
    
    // Text Editing Controls
    const editTextBtn = document.getElementById('edit-text-btn');
    const transcribedTextEditor = document.getElementById('transcribed-text-editor');
    const editActions = document.getElementById('edit-actions');
    const saveEditBtn = document.getElementById('save-edit-btn');
    const cancelEditBtn = document.getElementById('cancel-edit-btn');
    const retranslateBtn = document.getElementById('retranslate-btn');

    // Audio element for TTS
    const ttsAudio = document.getElementById('tts-audio');

    // 录音计时器相关变量 (Recording timer related variables)
    let recordingTimer = null;
    let recordingStartTime = null;
    
    // 创建音频处理器实例 (Create audio processor instance)
    const audioProcessor = new AudioProcessor({
        maxFileSize: 10 * 1024 * 1024, // 10MB
        targetSampleRate: 16000, // 16kHz for better speech recognition
        compressionQuality: 0.8
    });
    
    // 创建语音录制器实例 (Create voice recorder instance)
    const voiceRecorder = new VoiceRecorder({
        onRecordingStart: () => {
            recordBtn.classList.add('recording');
            recordBtn.style.display = 'none';
            stopBtn.style.display = 'flex';
            
            // 启动录音计时器 (Start recording timer)
            startRecordingTimer();
            showRecordingStatus('Listening...');
        },
        onRecordingStop: (audioBlob, duration) => {
            recordBtn.classList.remove('recording');
            stopBtn.style.display = 'none';
            recordBtn.style.display = 'flex';
            
            // 停止录音计时器 (Stop recording timer)
            stopRecordingTimer();
            
            if (audioBlob && audioBlob.size > 0) {
                showProcessingStatus('Processing audio...');
                transcribeAudio(audioBlob);
            } else {
                showErrorStatus('No audio recorded. Please try again.');
                setTimeout(() => hideStatus(), 2000);
            }
        },
        onError: (error) => {
            console.error('Voice recording error:', error);
            recordBtn.classList.remove('recording');
            stopBtn.style.display = 'none';
            recordBtn.style.display = 'flex';
            
            // 停止录音计时器 (Stop recording timer)
            stopRecordingTimer();
            hideStatus();
            
            let errorMessage = 'Recording failed. ';
            if (error.message.includes('Permission denied')) {
                errorMessage += 'Please allow microphone access and try again.';
            } else if (error.message.includes('not supported')) {
                errorMessage += 'Voice recording is not supported in this browser.';
            } else {
                errorMessage += 'Please try again.';
            }
            
            alert(errorMessage);
        }
    });

    // --- Event Listeners ---
    recordBtn.addEventListener('click', startRecording);
    stopBtn.addEventListener('click', stopRecording);
    confirmSendBtn.addEventListener('click', sendTranscribedMessage);
    rerecordBtn.addEventListener('click', handleRerecordRequest);
    
    // Text editing event listeners
    editTextBtn.addEventListener('click', toggleTextEditing);
    saveEditBtn.addEventListener('click', saveTextEdit);
    cancelEditBtn.addEventListener('click', cancelTextEdit);
    retranslateBtn.addEventListener('click', retranslateEditedText);
    sendTextBtn.addEventListener('click', sendTypedMessage);
    
    // Handle Enter key in text input
    textInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendTypedMessage();
        }
    });
    
    // Handle keyboard shortcuts for confirmation interface
    document.addEventListener('keydown', function(e) {
        // 只在确认界面显示时处理快捷键 (Only handle shortcuts when confirmation interface is visible)
        if (confirmationArea.style.display === 'block') {
            // 如果正在编辑文本，处理编辑相关快捷键 (Handle editing shortcuts if in text editing mode)
            if (isEditingText) {
                if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    if (!saveEditBtn.disabled) {
                        saveTextEdit();
                    }
                } else if (e.key === 'Escape') {
                    e.preventDefault();
                    cancelTextEdit();
                }
            } else {
                // 处理常规确认界面快捷键 (Handle regular confirmation shortcuts)
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    if (!confirmSendBtn.disabled) {
                        sendTranscribedMessage();
                    }
                } else if (e.key === 'Escape') {
                    e.preventDefault();
                    if (!rerecordBtn.disabled) {
                        handleRerecordRequest();
                    }
                } else if (e.key === 'r' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    if (!rerecordBtn.disabled) {
                        handleRerecordRequest();
                    }
                } else if (e.key === 'e' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    if (editTextBtn && !editTextBtn.disabled) {
                        toggleTextEditing();
                    }
                }
            }
        }
    });
    
    // Handle text editor specific events
    if (transcribedTextEditor) {
        transcribedTextEditor.addEventListener('input', function() {
            // 实时文本验证 (Real-time text validation)
            const text = this.value;
            const charCount = text.length;
            
            // 更新字符计数显示 (Update character count display)
            let charCountDisplay = document.getElementById('char-count-display');
            if (!charCountDisplay) {
                charCountDisplay = document.createElement('div');
                charCountDisplay.id = 'char-count-display';
                charCountDisplay.style.cssText = `
                    font-size: 0.75rem;
                    color: #6b7280;
                    text-align: right;
                    margin-top: 0.5rem;
                `;
                this.parentNode.appendChild(charCountDisplay);
            }
            
            charCountDisplay.textContent = `${charCount}/500 characters`;
            
            // 如果超过限制，显示警告 (Show warning if over limit)
            if (charCount > 500) {
                charCountDisplay.style.color = '#ef4444';
                this.style.borderColor = '#ef4444';
                saveEditBtn.disabled = true;
            } else {
                charCountDisplay.style.color = '#6b7280';
                this.style.borderColor = '#3b82f6';
                saveEditBtn.disabled = false;
            }
        });
    }

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
        
        // 重置状态图标 (Reset status icon)
        const statusIcon = document.getElementById('status-icon');
        statusIcon.className = 'fas fa-circle-notch fa-spin';
        statusIcon.style.marginRight = '0.5rem';
    }
    
    function showRecordingStatus(message) {
        statusText.textContent = message;
        statusIndicator.style.display = 'block';
        
        // 显示录音图标 (Show recording icon)
        const statusIcon = document.getElementById('status-icon');
        statusIcon.className = 'fas fa-microphone';
        statusIcon.style.marginRight = '0.5rem';
        statusIcon.style.color = '#ef4444';
        
        // 显示录音计时器 (Show recording timer)
        const recordingTimerEl = document.getElementById('recording-timer');
        recordingTimerEl.style.display = 'block';
        
        // 禁用文本输入和发送按钮 (Disable text input and send button)
        textInput.disabled = true;
        sendTextBtn.disabled = true;
    }
    
    function showProcessingStatus(message) {
        statusText.textContent = message;
        statusIndicator.style.display = 'block';
        
        // 显示处理图标 (Show processing icon)
        const statusIcon = document.getElementById('status-icon');
        statusIcon.className = 'fas fa-cog fa-spin';
        statusIcon.style.marginRight = '0.5rem';
        statusIcon.style.color = '#3b82f6';
        
        // 隐藏录音计时器 (Hide recording timer)
        const recordingTimerEl = document.getElementById('recording-timer');
        recordingTimerEl.style.display = 'none';
        
        // 禁用所有输入控件 (Disable all input controls)
        textInput.disabled = true;
        recordBtn.disabled = true;
        sendTextBtn.disabled = true;
    }
    
    function showErrorStatus(message) {
        statusText.textContent = message;
        statusIndicator.style.display = 'block';
        
        // 显示错误图标 (Show error icon)
        const statusIcon = document.getElementById('status-icon');
        statusIcon.className = 'fas fa-exclamation-triangle';
        statusIcon.style.marginRight = '0.5rem';
        statusIcon.style.color = '#ef4444';
        
        // 隐藏录音计时器 (Hide recording timer)
        const recordingTimerEl = document.getElementById('recording-timer');
        recordingTimerEl.style.display = 'none';
    }

    function hideStatus() {
        statusIndicator.style.display = 'none';
        
        // 隐藏录音计时器 (Hide recording timer)
        const recordingTimerEl = document.getElementById('recording-timer');
        recordingTimerEl.style.display = 'none';
        
        // 重新启用所有输入控件 (Re-enable all input controls)
        textInput.disabled = false;
        recordBtn.disabled = false;
        sendTextBtn.disabled = false;
    }
    
    // --- Recording Timer Functions ---
    function startRecordingTimer() {
        recordingStartTime = Date.now();
        recordingTimer = setInterval(updateRecordingTimer, 100);
        updateRecordingTimer(); // 立即更新一次
    }
    
    function stopRecordingTimer() {
        if (recordingTimer) {
            clearInterval(recordingTimer);
            recordingTimer = null;
        }
        recordingStartTime = null;
    }
    
    function updateRecordingTimer() {
        if (!recordingStartTime) return;
        
        const elapsed = (Date.now() - recordingStartTime) / 1000;
        const minutes = Math.floor(elapsed / 60);
        const seconds = Math.floor(elapsed % 60);
        
        const timerDisplay = document.getElementById('timer-display');
        if (timerDisplay) {
            timerDisplay.textContent = 
                `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }
        
        // 如果录音时间过长，显示警告 (Show warning if recording too long)
        if (elapsed > 50) { // 50秒警告，60秒自动停止
            timerDisplay.style.color = '#f59e0b';
            statusText.textContent = 'Recording will stop soon...';
        }
    }

    // 存储当前确认数据 (Store current confirmation data)
    let currentConfirmationData = null;
    let isEditingText = false;
    let originalTranscribedText = '';
    
    function showConfirmation(transcribed, english) {
        return showConfirmationWithValidation(transcribed, english, null);
    }
    
    function showConfirmationWithValidation(transcribed, english, apiData = null) {
        // 验证输入参数 (Validate input parameters)
        if (!transcribed || !english) {
            console.error('Invalid confirmation data:', { transcribed, english });
            showErrorStatus('Invalid transcription data received. Please try again.');
            setTimeout(() => resetInputState(), 2000);
            return false;
        }
        
        // 验证文本长度 (Validate text length)
        if (transcribed.length > 500) {
            console.warn('Transcribed text is very long:', transcribed.length);
            showErrorStatus('Transcribed text is too long. Please record a shorter message.');
            setTimeout(() => resetInputState(), 3000);
            return false;
        }
        
        // 存储确认数据用于后续处理 (Store confirmation data for later processing)
        currentConfirmationData = {
            transcribed: transcribed,
            english: english,
            timestamp: Date.now(),
            apiData: apiData
        };
        
        // 更新确认界面内容 (Update confirmation interface content)
        transcribedTextElem.textContent = transcribed;
        englishTranslationElem.textContent = english;
        
        // 添加动画效果显示确认界面 (Show confirmation interface with animation)
        confirmationArea.style.display = 'block';
        confirmationArea.style.opacity = '0';
        confirmationArea.style.transform = 'translateY(20px)';
        
        // 隐藏输入区域 (Hide input area)
        inputArea.style.display = 'none';
        
        // 触发动画 (Trigger animation)
        setTimeout(() => {
            confirmationArea.style.transition = 'all 0.4s ease-out';
            confirmationArea.style.opacity = '1';
            confirmationArea.style.transform = 'translateY(0)';
        }, 50);
        
        // 聚焦到确认发送按钮 (Focus on confirm send button)
        setTimeout(() => {
            confirmSendBtn.focus();
        }, 400);
        
        // 滚动到底部以确保确认界面可见 (Scroll to bottom to ensure confirmation interface is visible)
        setTimeout(() => {
            scrollToBottom();
        }, 200);
        
        console.log('Confirmation interface shown:', { transcribed, english, apiData });
        return true;
    }

    function hideConfirmation() {
        // 添加动画效果隐藏确认界面 (Hide confirmation interface with animation)
        confirmationArea.style.transition = 'all 0.3s ease-in';
        confirmationArea.style.opacity = '0';
        confirmationArea.style.transform = 'translateY(-10px)';
        
        setTimeout(() => {
            confirmationArea.style.display = 'none';
            inputArea.style.display = 'flex';
            
            // 重置动画属性 (Reset animation properties)
            confirmationArea.style.transition = '';
            confirmationArea.style.opacity = '';
            confirmationArea.style.transform = '';
            
            // 聚焦到文本输入框 (Focus on text input)
            textInput.focus();
        }, 300);
        
        console.log('Confirmation interface hidden');
    }

    function resetInputState() {
        hideStatus();
        hideConfirmation();
        recordBtn.classList.remove('recording');
        
        // 停止录音计时器 (Stop recording timer)
        stopRecordingTimer();
        
        // 确保录音器已停止 (Ensure recorder is stopped)
        if (voiceRecorder.isRecording) {
            voiceRecorder.stopRecording();
        }
        
        // 重置按钮显示状态 (Reset button display state)
        stopBtn.style.display = 'none';
        recordBtn.style.display = 'flex';
        
        // 重置确认按钮状态 (Reset confirmation button state)
        confirmSendBtn.disabled = false;
        rerecordBtn.disabled = false;
        confirmSendBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Send Message';
        rerecordBtn.innerHTML = '<i class="fas fa-microphone"></i> Re-record';
        
        // Clear text input
        textInput.value = '';
        textInput.style.height = 'auto';
        
        // 聚焦到文本输入框 (Focus on text input)
        setTimeout(() => {
            textInput.focus();
        }, 100);
        
        // 重置文本编辑状态 (Reset text editing state)
        isEditingText = false;
        originalTranscribedText = '';
        if (editTextBtn) {
            editTextBtn.classList.remove('active');
            editTextBtn.innerHTML = '<i class="fas fa-edit"></i>';
        }
        if (editActions) {
            editActions.style.display = 'none';
        }
        if (transcribedTextEditor) {
            transcribedTextEditor.style.display = 'none';
        }
        if (transcribedTextElem) {
            transcribedTextElem.style.display = 'inline';
        }
        
        console.log('Input state reset');
    }
    
    // --- Text Editing Functions ---
    function toggleTextEditing() {
        if (isEditingText) {
            cancelTextEdit();
        } else {
            startTextEditing();
        }
    }
    
    function startTextEditing() {
        if (!currentConfirmationData) {
            console.error('No confirmation data available for editing');
            return;
        }
        
        isEditingText = true;
        originalTranscribedText = transcribedTextElem.textContent;
        
        // 更新编辑按钮状态 (Update edit button state)
        editTextBtn.classList.add('active');
        editTextBtn.innerHTML = '<i class="fas fa-times"></i>';
        editTextBtn.title = 'Cancel editing';
        
        // 显示文本编辑器 (Show text editor)
        transcribedTextEditor.value = originalTranscribedText;
        transcribedTextEditor.style.display = 'block';
        transcribedTextElem.style.display = 'none';
        
        // 显示编辑操作按钮 (Show edit action buttons)
        editActions.style.display = 'flex';
        
        // 聚焦到编辑器 (Focus on editor)
        setTimeout(() => {
            transcribedTextEditor.focus();
            transcribedTextEditor.select();
        }, 100);
        
        // 禁用确认和重录按钮 (Disable confirm and re-record buttons)
        confirmSendBtn.disabled = true;
        rerecordBtn.disabled = true;
        
        console.log('Text editing started');
    }
    
    function saveTextEdit() {
        const editedText = transcribedTextEditor.value.trim();
        
        // 验证编辑后的文本 (Validate edited text)
        if (!editedText) {
            showErrorStatus('Text cannot be empty. Please enter some text.');
            setTimeout(() => hideStatus(), 2000);
            return;
        }
        
        if (editedText.length > 500) {
            showErrorStatus('Text is too long. Please keep it under 500 characters.');
            setTimeout(() => hideStatus(), 2000);
            return;
        }
        
        // 添加保存动画 (Add save animation)
        saveEditBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
        saveEditBtn.disabled = true;
        
        // 更新显示的文本 (Update displayed text)
        transcribedTextElem.textContent = editedText;
        
        // 更新确认数据 (Update confirmation data)
        if (currentConfirmationData) {
            currentConfirmationData.transcribed = editedText;
            currentConfirmationData.edited = true;
            currentConfirmationData.originalText = originalTranscribedText;
        }
        
        // 结束编辑模式 (End editing mode)
        setTimeout(() => {
            endTextEditing();
            console.log('Text edit saved:', { original: originalTranscribedText, edited: editedText });
        }, 500);
    }
    
    function cancelTextEdit() {
        // 恢复原始文本 (Restore original text)
        transcribedTextEditor.value = originalTranscribedText;
        
        endTextEditing();
        console.log('Text edit cancelled');
    }
    
    function endTextEditing() {
        isEditingText = false;
        
        // 重置编辑按钮状态 (Reset edit button state)
        editTextBtn.classList.remove('active');
        editTextBtn.innerHTML = '<i class="fas fa-edit"></i>';
        editTextBtn.title = 'Edit transcribed text';
        
        // 隐藏文本编辑器 (Hide text editor)
        transcribedTextEditor.style.display = 'none';
        transcribedTextElem.style.display = 'inline';
        
        // 隐藏编辑操作按钮 (Hide edit action buttons)
        editActions.style.display = 'none';
        
        // 重新启用确认和重录按钮 (Re-enable confirm and re-record buttons)
        confirmSendBtn.disabled = false;
        rerecordBtn.disabled = false;
        
        // 重置保存按钮状态 (Reset save button state)
        saveEditBtn.innerHTML = '<i class="fas fa-check"></i> Save Changes';
        saveEditBtn.disabled = false;
    }
    
    async function retranslateEditedText() {
        const editedText = transcribedTextEditor.value.trim();
        
        if (!editedText) {
            showErrorStatus('Please enter some text to translate.');
            setTimeout(() => hideStatus(), 2000);
            return;
        }
        
        // 添加重新翻译动画 (Add re-translate animation)
        retranslateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Translating...';
        retranslateBtn.disabled = true;
        
        try {
            showProcessingStatus('Re-translating text...');
            
            // 调用翻译API (Call translation API)
            const response = await fetch(translateChineseApiUrl, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json', 
                    'X-CSRFToken': csrfToken 
                },
                body: JSON.stringify({ 
                    chinese_text: editedText 
                }),
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'Re-translation failed.');
            }
            
            // 更新英文翻译 (Update English translation)
            englishTranslationElem.textContent = data.english_translation;
            
            // 更新确认数据 (Update confirmation data)
            if (currentConfirmationData) {
                currentConfirmationData.english = data.english_translation;
                currentConfirmationData.retranslated = true;
            }
            
            hideStatus();
            console.log('Text re-translated successfully:', { 
                chinese: editedText, 
                english: data.english_translation 
            });
            
        } catch (error) {
            console.error('Re-translation Error:', error);
            showErrorStatus('Re-translation failed. Please try again.');
            setTimeout(() => hideStatus(), 3000);
        } finally {
            // 重置重新翻译按钮状态 (Reset re-translate button state)
            retranslateBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Re-translate';
            retranslateBtn.disabled = false;
        }
    }
    
    function handleRerecordRequest() {
        // 添加视觉反馈 (Add visual feedback)
        rerecordBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Preparing...';
        rerecordBtn.disabled = true;
        confirmSendBtn.disabled = true;
        
        console.log('Re-record requested', {
            previousData: currentConfirmationData
        });
        
        // 清除当前确认数据 (Clear current confirmation data)
        currentConfirmationData = null;
        
        // 短暂延迟后重置状态并准备新录音 (Reset state after brief delay and prepare for new recording)
        setTimeout(() => {
            resetInputState();
            
            // 提示用户可以开始新录音 (Hint user can start new recording)
            showStatus('Ready to record. Click the microphone button to start.');
            setTimeout(() => {
                hideStatus();
            }, 2000);
        }, 500);
    }

    function scrollToBottom() {
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    // --- Recording Functions ---
    async function startRecording() {
        const success = await voiceRecorder.startRecording();
        if (!success) {
            // 错误处理已在VoiceRecorder的onError回调中处理
            console.log('Failed to start recording');
        }
    }

    function stopRecording() {
        const success = voiceRecorder.stopRecording();
        if (!success) {
            console.log('Failed to stop recording');
            hideStatus();
        }
    }

    // --- Upload Helper Functions ---
    function uploadWithProgress(url, formData, csrfToken, onProgress) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            
            // 设置上传进度监听器 (Set upload progress listener)
            xhr.upload.addEventListener('progress', (event) => {
                if (event.lengthComputable) {
                    const progress = (event.loaded / event.total) * 100;
                    onProgress(progress);
                }
            });
            
            // 设置响应处理器 (Set response handler)
            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve(response);
                    } catch (error) {
                        reject(new Error('Invalid JSON response'));
                    }
                } else {
                    reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
                }
            });
            
            // 设置错误处理器 (Set error handler)
            xhr.addEventListener('error', () => {
                reject(new Error('Network error occurred'));
            });
            
            xhr.addEventListener('timeout', () => {
                reject(new Error('Request timeout'));
            });
            
            // 配置请求 (Configure request)
            xhr.open('POST', url);
            xhr.setRequestHeader('X-CSRFToken', csrfToken);
            xhr.timeout = 30000; // 30秒超时
            
            // 发送请求 (Send request)
            xhr.send(formData);
        });
    }
    
    // --- Audio Processing ---
    async function transcribeAudio(audioBlob, retryCount = 0) {
        const maxRetries = 2;
        
        try {
            showProcessingStatus('Processing audio...');
            
            // 验证音频文件 (Validate audio file)
            const validation = audioProcessor.validateAudioFile(audioBlob);
            if (!validation.isValid) {
                throw new Error(`Audio validation failed: ${validation.errors.join(', ')}`);
            }
            
            // 处理音频文件 (Process audio file)
            const processedAudio = await audioProcessor.processAudioBlob(audioBlob);
            
            // 显示文件信息 (Show file info)
            console.log(`Processed audio: ${(processedAudio.size / 1024).toFixed(2)}KB, ${processedAudio.duration.toFixed(2)}s, ${processedAudio.type}`);
            
            // 创建FormData用于上传 (Create FormData for upload)
            const formData = audioProcessor.createFormData(processedAudio, {
                session_id: sessionId
            });

            // 使用XMLHttpRequest以支持上传进度 (Use XMLHttpRequest for upload progress support)
            const data = await uploadWithProgress(transcribeApiUrl, formData, csrfToken, (progress) => {
                if (progress < 100) {
                    showProcessingStatus(`Uploading audio... ${Math.round(progress)}%`);
                } else {
                    showProcessingStatus('Transcribing audio...');
                }
            });
            
            if (!data.success) {
                throw new Error(data.error || 'Transcription failed.');
            }
            
            hideStatus();
            
            // 集成确认流程到聊天逻辑 (Integrate confirmation flow into chat logic)
            showConfirmationWithValidation(data.chinese_text, data.english_translation, data);

        } catch (error) {
            console.error('Transcription Error:', error);
            
            // 如果是网络错误且还有重试次数，则重试 (Retry if network error and retries available)
            if ((error.message.includes('network') || error.message.includes('timeout')) && retryCount < maxRetries) {
                console.log(`Retrying transcription... (${retryCount + 1}/${maxRetries})`);
                showProcessingStatus(`Retrying... (${retryCount + 1}/${maxRetries})`);
                
                // 等待1秒后重试 (Wait 1 second before retry)
                setTimeout(() => {
                    transcribeAudio(audioBlob, retryCount + 1);
                }, 1000);
                return;
            }
            
            // 显示用户友好的错误信息 (Show user-friendly error message)
            let errorMessage = 'Transcription failed. ';
            if (error.message.includes('too large')) {
                errorMessage = 'Audio file is too large. Please record a shorter message.';
            } else if (error.message.includes('empty')) {
                errorMessage = 'No audio was recorded. Please try again.';
            } else if (error.message.includes('format')) {
                errorMessage = 'Audio format not supported. Please try again.';
            } else if (error.message.includes('network') || error.message.includes('HTTP') || error.message.includes('timeout')) {
                errorMessage = 'Network error. Please check your connection and try again.';
            } else {
                errorMessage += 'Please try again.';
            }
            
            showErrorStatus(errorMessage);
            setTimeout(() => resetInputState(), 3000);
        }
    }

    // --- Message Sending ---
    function sendTranscribedMessage() {
        const message = transcribedTextElem.textContent.trim();
        
        // 验证消息内容 (Validate message content)
        if (!message) {
            console.error('No transcribed message to send');
            showErrorStatus('No message to send. Please try recording again.');
            setTimeout(() => resetInputState(), 2000);
            return;
        }
        
        // 验证确认数据 (Validate confirmation data)
        if (!currentConfirmationData) {
            console.error('No confirmation data available');
            showErrorStatus('Confirmation data missing. Please try again.');
            setTimeout(() => resetInputState(), 2000);
            return;
        }
        
        // 禁用确认按钮防止重复点击 (Disable confirm button to prevent double-clicking)
        confirmSendBtn.disabled = true;
        rerecordBtn.disabled = true;
        
        // 添加视觉反馈 (Add visual feedback)
        confirmSendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
        
        console.log('Sending transcribed message:', {
            message,
            confirmationData: currentConfirmationData
        });
        
        // 创建消息对象包含额外信息 (Create message object with additional info)
        const messageData = {
            text: message,
            inputMethod: 'voice',
            englishTranslation: currentConfirmationData.english,
            timestamp: currentConfirmationData.timestamp
        };
        
        // 发送消息 (Send message)
        sendMessageWithMetadata(messageData);
        hideConfirmation();
        
        // 清除确认数据 (Clear confirmation data)
        currentConfirmationData = null;
        
        // 重置按钮状态 (Reset button state)
        setTimeout(() => {
            confirmSendBtn.disabled = false;
            rerecordBtn.disabled = false;
            confirmSendBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Send Message';
        }, 1000);
    }

    async function sendTypedMessage() {
        const text = textInput.value.trim();
        if (!text) return;

        showProcessingStatus('Translating text...');
        
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
            
            // 发送翻译后的消息 (Send translated message)
            const messageData = {
                text: data.chinese_text,
                inputMethod: 'translation',
                englishTranslation: text, // 原始英文作为翻译
                timestamp: Date.now()
            };
            
            sendMessageWithMetadata(messageData);
            textInput.value = '';
            textInput.style.height = 'auto';

        } catch (error) {
            console.error('Translation Error:', error);
            alert(`Translation Error: ${error.message}`);
            resetInputState();
        }
    }

    async function sendMessage(message) {
        return sendMessageWithMetadata({ text: message, inputMethod: 'text' });
    }
    
    async function sendMessageWithMetadata(messageData) {
        const message = messageData.text;
        const inputMethod = messageData.inputMethod || 'text';
        
        // Add user message to chat immediately
        appendMessage('user', { 
            chinese_text: message,
            input_method: inputMethod,
            english_translation: messageData.englishTranslation
        });
        
        showProcessingStatus('AI is thinking...');

        try {
            // 准备发送数据 (Prepare data to send)
            const requestData = { 
                message: message, 
                session_id: sessionId,
                input_method: inputMethod
            };
            
            // 如果有英文翻译，包含在请求中 (Include English translation if available)
            if (messageData.englishTranslation) {
                requestData.english_translation = messageData.englishTranslation;
            }
            
            const response = await fetch(chatApiUrl, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json', 
                    'X-CSRFToken': csrfToken 
                },
                body: JSON.stringify(requestData),
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
                
                console.log('Message sent successfully:', {
                    message,
                    inputMethod,
                    hasTranslation: !!messageData.englishTranslation
                });
            }, 500);

        } catch (error) {
            console.error('Chat Error:', error);
            
            // 显示用户友好的错误信息 (Show user-friendly error message)
            let errorMessage = 'Failed to send message. ';
            if (error.message.includes('network') || error.message.includes('HTTP')) {
                errorMessage += 'Please check your connection and try again.';
            } else {
                errorMessage += 'Please try again.';
            }
            
            showErrorStatus(errorMessage);
            setTimeout(() => resetInputState(), 3000);
        } finally {
            // 只有在没有错误时才重置状态 (Only reset state if no error)
            if (!document.getElementById('status-indicator').style.display.includes('block')) {
                resetInputState();
            }
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
        
        // 根据输入方法显示不同图标 (Show different icons based on input method)
        let avatarIcon = sender === 'ai' ? 'robot' : 'user';
        if (sender === 'user' && content.input_method === 'voice') {
            avatarIcon = 'microphone';
            avatar.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
        } else if (sender === 'user' && content.input_method === 'translation') {
            avatarIcon = 'language';
            avatar.style.background = 'linear-gradient(135deg, #8b5cf6, #7c3aed)';
        }
        
        avatar.innerHTML = `<i class="fas fa-${avatarIcon}"></i>`;

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
            let userMessageHtml = `<div class="chinese-text">${content.chinese_text}</div>`;
            
            // 如果有英文翻译，显示它 (Show English translation if available)
            if (content.english_translation) {
                userMessageHtml += `
                    <hr class="pinyin-divider">
                    <div class="pinyin-text" style="font-style: italic; color: rgba(255, 255, 255, 0.7);">
                        English: ${content.english_translation}
                    </div>
                `;
            }
            
            // 添加输入方法指示器 (Add input method indicator)
            if (content.input_method && content.input_method !== 'text') {
                const methodLabel = content.input_method === 'voice' ? 'Voice' : 'Translation';
                userMessageHtml += `
                    <div style="margin-top: 0.5rem; font-size: 0.75rem; opacity: 0.8;">
                        <i class="fas fa-${content.input_method === 'voice' ? 'microphone' : 'language'}" style="margin-right: 0.25rem;"></i>
                        ${methodLabel}
                    </div>
                `;
            }
            
            messageContent.innerHTML = userMessageHtml;
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
        
        console.log('Message appended:', { sender, content });
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
        
        // 检查浏览器是否支持语音录制 (Check if browser supports voice recording)
        if (!VoiceRecorder.isSupported()) {
            recordBtn.style.display = 'none';
            console.warn('Voice recording not supported in this browser');
        }
        
        console.log('Chat initialized successfully');
    }
    
    // 页面卸载时清理资源 (Cleanup resources when page unloads)
    window.addEventListener('beforeunload', () => {
        if (voiceRecorder) {
            voiceRecorder.destroy();
        }
    });

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
            <button onclick="window.location.href='/speak/'" style="
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
