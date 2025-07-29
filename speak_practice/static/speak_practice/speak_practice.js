// --- UXEnhancer Class ---
class UXEnhancer {
    constructor(options = {}) {
        this.statusIndicator = options.statusIndicator;
        this.errorHandler = options.errorHandler;
        
        // 键盘快捷键配置 (Keyboard shortcuts configuration)
        this.shortcuts = {
            'ctrl+enter': 'sendMessage',
            'ctrl+r': 'startRecording',
            'escape': 'cancelOperation',
            'ctrl+z': 'undoLastAction',
            'f1': 'showHelp',
            'ctrl+shift+r': 'restartConversation'
        };
        
        // 操作历史 (Operation history)
        this.operationHistory = [];
        this.maxHistorySize = 10;
        
        // 帮助系统 (Help system)
        this.helpVisible = false;
        
        // 确认对话框 (Confirmation dialogs)
        this.confirmationCallbacks = new Map();
        
        // 回调函数 (Callback functions)
        this.onShortcut = options.onShortcut || (() => {});
        this.onUndo = options.onUndo || (() => {});
        this.onHelp = options.onHelp || (() => {});
        
        this.initializeKeyboardShortcuts();
        this.initializeTooltips();
        this.initializeHelpSystem();
    }
    
    /**
     * 初始化键盘快捷键 (Initialize keyboard shortcuts)
     */
    initializeKeyboardShortcuts() {
        document.addEventListener('keydown', (event) => {
            const shortcut = this.getShortcutString(event);
            const action = this.shortcuts[shortcut];
            
            if (action && this.canExecuteShortcut(action, event)) {
                event.preventDefault();
                this.executeShortcut(action, event);
            }
        });
        
        // 显示快捷键提示 (Show shortcut hints)
        this.createShortcutHints();
    }
    
    /**
     * 获取快捷键字符串 (Get shortcut string)
     */
    getShortcutString(event) {
        const parts = [];
        
        if (event.ctrlKey) parts.push('ctrl');
        if (event.shiftKey) parts.push('shift');
        if (event.altKey) parts.push('alt');
        if (event.metaKey) parts.push('meta');
        
        const key = event.key.toLowerCase();
        if (key !== 'control' && key !== 'shift' && key !== 'alt' && key !== 'meta') {
            parts.push(key);
        }
        
        return parts.join('+');
    }
    
    /**
     * 检查是否可以执行快捷键 (Check if shortcut can be executed)
     */
    canExecuteShortcut(action, event) {
        // 如果在输入框中，只允许特定快捷键 (Only allow specific shortcuts in input fields)
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
            return ['sendMessage', 'showHelp', 'escape'].includes(action);
        }
        
        // 如果有模态框打开，只允许关闭操作 (Only allow close operations if modal is open)
        if (this.helpVisible) {
            return action === 'showHelp' || action === 'escape';
        }
        
        return true;
    }
    
    /**
     * 执行快捷键操作 (Execute shortcut action)
     */
    executeShortcut(action, event) {
        console.log(`Executing shortcut: ${action}`);
        
        switch (action) {
            case 'sendMessage':
                this.triggerSendMessage();
                break;
            case 'startRecording':
                this.triggerStartRecording();
                break;
            case 'cancelOperation':
                this.triggerCancelOperation();
                break;
            case 'undoLastAction':
                this.triggerUndo();
                break;
            case 'showHelp':
                this.toggleHelp();
                break;
            case 'restartConversation':
                this.triggerRestartConversation();
                break;
        }
        
        this.onShortcut(action, event);
    }
    
    /**
     * 触发发送消息 (Trigger send message)
     */
    triggerSendMessage() {
        const textInput = document.getElementById('text-input');
        const sendButton = document.getElementById('send-text-btn');
        
        if (textInput && textInput.value.trim() && sendButton && !sendButton.disabled) {
            sendButton.click();
        }
    }
    
    /**
     * 触发开始录音 (Trigger start recording)
     */
    triggerStartRecording() {
        const recordButton = document.getElementById('record-btn');
        const stopButton = document.getElementById('stop-btn');
        
        if (recordButton && recordButton.style.display !== 'none' && !recordButton.disabled) {
            recordButton.click();
        } else if (stopButton && stopButton.style.display !== 'none' && !stopButton.disabled) {
            stopButton.click();
        }
    }
    
    /**
     * 触发取消操作 (Trigger cancel operation)
     */
    triggerCancelOperation() {
        // 关闭帮助 (Close help)
        if (this.helpVisible) {
            this.hideHelp();
            return;
        }
        
        // 取消确认界面 (Cancel confirmation)
        const confirmationArea = document.getElementById('confirmation-area');
        const rerecordButton = document.getElementById('rerecord-btn');
        
        if (confirmationArea && confirmationArea.style.display !== 'none' && rerecordButton) {
            rerecordButton.click();
        }
        
        // 停止录音 (Stop recording)
        const stopButton = document.getElementById('stop-btn');
        if (stopButton && stopButton.style.display !== 'none') {
            stopButton.click();
        }
    }
    
    /**
     * 触发撤销操作 (Trigger undo operation)
     */
    triggerUndo() {
        if (this.operationHistory.length > 0) {
            const lastOperation = this.operationHistory.pop();
            this.executeUndo(lastOperation);
        } else {
            if (this.statusIndicator) {
                this.statusIndicator.showInfo('No actions to undo');
            }
        }
    }
    
    /**
     * 触发重启对话 (Trigger restart conversation)
     */
    triggerRestartConversation() {
        this.showConfirmation(
            'Restart Conversation',
            'Are you sure you want to restart the conversation? All messages will be lost.',
            () => {
                const restartButton = document.getElementById('restart-conversation-btn');
                if (restartButton) {
                    restartButton.click();
                }
            }
        );
    }
    
    /**
     * 记录操作 (Record operation)
     */
    recordOperation(type, data) {
        this.operationHistory.push({
            type: type,
            data: data,
            timestamp: Date.now()
        });
        
        // 限制历史记录大小 (Limit history size)
        if (this.operationHistory.length > this.maxHistorySize) {
            this.operationHistory.shift();
        }
    }
    
    /**
     * 执行撤销 (Execute undo)
     */
    executeUndo(operation) {
        console.log('Undoing operation:', operation);
        
        switch (operation.type) {
            case 'message_sent':
                this.undoMessageSent(operation.data);
                break;
            case 'text_edited':
                this.undoTextEdit(operation.data);
                break;
            case 'recording_completed':
                this.undoRecording(operation.data);
                break;
        }
        
        this.onUndo(operation);
    }
    
    /**
     * 撤销发送消息 (Undo message sent)
     */
    undoMessageSent(data) {
        // 这里可以实现消息撤销逻辑 (Message undo logic can be implemented here)
        if (this.statusIndicator) {
            this.statusIndicator.showInfo('Message undo is not available in this version');
        }
    }
    
    /**
     * 撤销文本编辑 (Undo text edit)
     */
    undoTextEdit(data) {
        const textEditor = document.getElementById('transcribed-text-editor');
        if (textEditor && data.previousText) {
            textEditor.value = data.previousText;
        }
    }
    
    /**
     * 撤销录音 (Undo recording)
     */
    undoRecording(data) {
        // 重置到录音前状态 (Reset to pre-recording state)
        const confirmationArea = document.getElementById('confirmation-area');
        if (confirmationArea) {
            confirmationArea.style.display = 'none';
        }
    }
    
    /**
     * 显示确认对话框 (Show confirmation dialog)
     */
    showConfirmation(title, message, onConfirm, onCancel = null) {
        const confirmationId = `confirmation_${Date.now()}`;
        
        const overlay = document.createElement('div');
        overlay.className = 'confirmation-overlay';
        overlay.id = confirmationId;
        
        overlay.innerHTML = `
            <div class="confirmation-dialog">
                <div class="confirmation-header">
                    <h5>${title}</h5>
                </div>
                <div class="confirmation-body">
                    <p>${message}</p>
                </div>
                <div class="confirmation-actions">
                    <button class="btn-confirm-action" data-action="confirm">
                        <i class="fas fa-check"></i>
                        <span>Confirm</span>
                    </button>
                    <button class="btn-cancel-action" data-action="cancel">
                        <i class="fas fa-times"></i>
                        <span>Cancel</span>
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(overlay);
        
        // 添加事件监听器 (Add event listeners)
        const confirmButton = overlay.querySelector('.btn-confirm-action');
        const cancelButton = overlay.querySelector('.btn-cancel-action');
        
        confirmButton.addEventListener('click', () => {
            this.hideConfirmation(confirmationId);
            if (onConfirm) onConfirm();
        });
        
        cancelButton.addEventListener('click', () => {
            this.hideConfirmation(confirmationId);
            if (onCancel) onCancel();
        });
        
        // ESC键关闭 (Close with ESC key)
        const escapeHandler = (event) => {
            if (event.key === 'Escape') {
                this.hideConfirmation(confirmationId);
                if (onCancel) onCancel();
                document.removeEventListener('keydown', escapeHandler);
            }
        };
        document.addEventListener('keydown', escapeHandler);
        
        // 点击外部关闭 (Close when clicking outside)
        overlay.addEventListener('click', (event) => {
            if (event.target === overlay) {
                this.hideConfirmation(confirmationId);
                if (onCancel) onCancel();
            }
        });
        
        // 显示动画 (Show animation)
        requestAnimationFrame(() => {
            overlay.classList.add('visible');
        });
    }
    
    /**
     * 隐藏确认对话框 (Hide confirmation dialog)
     */
    hideConfirmation(confirmationId) {
        const overlay = document.getElementById(confirmationId);
        if (overlay) {
            overlay.classList.remove('visible');
            setTimeout(() => {
                if (overlay.parentNode) {
                    overlay.parentNode.removeChild(overlay);
                }
            }, 300);
        }
    }
    
    /**
     * 初始化工具提示 (Initialize tooltips)
     */
    initializeTooltips() {
        // 为按钮添加工具提示 (Add tooltips to buttons)
        const tooltipElements = [
            { selector: '#record-btn', text: 'Start recording (Ctrl+R)' },
            { selector: '#stop-btn', text: 'Stop recording (Ctrl+R)' },
            { selector: '#send-text-btn', text: 'Send message (Ctrl+Enter)' },
            { selector: '#restart-conversation-btn', text: 'Restart conversation (Ctrl+Shift+R)' },
            { selector: '#change-topic-btn', text: 'Change topic' }
        ];
        
        tooltipElements.forEach(({ selector, text }) => {
            const element = document.querySelector(selector);
            if (element) {
                element.title = text;
                element.setAttribute('data-tooltip', text);
            }
        });
    }
    
    /**
     * 初始化帮助系统 (Initialize help system)
     */
    initializeHelpSystem() {
        // 创建帮助按钮 (Create help button)
        this.createHelpButton();
    }
    
    /**
     * 创建帮助按钮 (Create help button)
     */
    createHelpButton() {
        const helpButton = document.createElement('button');
        helpButton.id = 'help-button';
        helpButton.className = 'help-button';
        helpButton.innerHTML = '<i class="fas fa-question-circle"></i>';
        helpButton.title = 'Show help (F1)';
        
        helpButton.addEventListener('click', () => {
            this.toggleHelp();
        });
        
        // 添加到页面 (Add to page)
        const chatContainer = document.querySelector('.chat-container');
        if (chatContainer) {
            chatContainer.appendChild(helpButton);
        }
    }
    
    /**
     * 切换帮助显示 (Toggle help display)
     */
    toggleHelp() {
        if (this.helpVisible) {
            this.hideHelp();
        } else {
            this.showHelp();
        }
    }
    
    /**
     * 显示帮助 (Show help)
     */
    showHelp() {
        if (this.helpVisible) return;
        
        const helpOverlay = document.createElement('div');
        helpOverlay.id = 'help-overlay';
        helpOverlay.className = 'help-overlay';
        
        helpOverlay.innerHTML = `
            <div class="help-dialog">
                <div class="help-header">
                    <h4>Help & Keyboard Shortcuts</h4>
                    <button class="help-close-btn">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="help-content">
                    <div class="help-section">
                        <h5>Voice Recording</h5>
                        <ul>
                            <li>Click the microphone button to start recording</li>
                            <li>Speak clearly in Chinese</li>
                            <li>Click stop when finished</li>
                            <li>Review and edit the transcription if needed</li>
                        </ul>
                    </div>
                    
                    <div class="help-section">
                        <h5>Text Input</h5>
                        <ul>
                            <li>Type your message in the text box</li>
                            <li>Press Ctrl+Enter to send</li>
                            <li>Use English input mode for translation help</li>
                        </ul>
                    </div>
                    
                    <div class="help-section">
                        <h5>Keyboard Shortcuts</h5>
                        <div class="shortcuts-grid">
                            <div class="shortcut-item">
                                <kbd>Ctrl+Enter</kbd>
                                <span>Send message</span>
                            </div>
                            <div class="shortcut-item">
                                <kbd>Ctrl+R</kbd>
                                <span>Start/Stop recording</span>
                            </div>
                            <div class="shortcut-item">
                                <kbd>Escape</kbd>
                                <span>Cancel operation</span>
                            </div>
                            <div class="shortcut-item">
                                <kbd>Ctrl+Z</kbd>
                                <span>Undo last action</span>
                            </div>
                            <div class="shortcut-item">
                                <kbd>F1</kbd>
                                <span>Show/Hide help</span>
                            </div>
                            <div class="shortcut-item">
                                <kbd>Ctrl+Shift+R</kbd>
                                <span>Restart conversation</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="help-section">
                        <h5>Tips</h5>
                        <ul>
                            <li>Speak slowly and clearly for better recognition</li>
                            <li>Use the edit feature to correct transcription errors</li>
                            <li>Try the English input mode if you're stuck</li>
                            <li>Listen to AI responses to improve pronunciation</li>
                        </ul>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(helpOverlay);
        
        // 添加事件监听器 (Add event listeners)
        const closeButton = helpOverlay.querySelector('.help-close-btn');
        closeButton.addEventListener('click', () => {
            this.hideHelp();
        });
        
        // ESC键关闭 (Close with ESC key)
        const escapeHandler = (event) => {
            if (event.key === 'Escape') {
                this.hideHelp();
                document.removeEventListener('keydown', escapeHandler);
            }
        };
        document.addEventListener('keydown', escapeHandler);
        
        // 点击外部关闭 (Close when clicking outside)
        helpOverlay.addEventListener('click', (event) => {
            if (event.target === helpOverlay) {
                this.hideHelp();
            }
        });
        
        this.helpVisible = true;
        
        // 显示动画 (Show animation)
        requestAnimationFrame(() => {
            helpOverlay.classList.add('visible');
        });
        
        this.onHelp(true);
    }
    
    /**
     * 隐藏帮助 (Hide help)
     */
    hideHelp() {
        const helpOverlay = document.getElementById('help-overlay');
        if (helpOverlay) {
            helpOverlay.classList.remove('visible');
            setTimeout(() => {
                if (helpOverlay.parentNode) {
                    helpOverlay.parentNode.removeChild(helpOverlay);
                }
            }, 300);
        }
        
        this.helpVisible = false;
        this.onHelp(false);
    }
    
    /**
     * 创建快捷键提示 (Create shortcut hints)
     */
    createShortcutHints() {
        const hintsContainer = document.createElement('div');
        hintsContainer.id = 'shortcut-hints';
        hintsContainer.className = 'shortcut-hints';
        
        hintsContainer.innerHTML = `
            <div class="hint-item">
                <kbd>Ctrl+Enter</kbd> Send
            </div>
            <div class="hint-item">
                <kbd>Ctrl+R</kbd> Record
            </div>
            <div class="hint-item">
                <kbd>F1</kbd> Help
            </div>
        `;
        
        // 添加到聊天容器 (Add to chat container)
        const chatFooter = document.querySelector('.chat-footer');
        if (chatFooter) {
            chatFooter.appendChild(hintsContainer);
        }
    }
    
    /**
     * 销毁UX增强器 (Destroy UX enhancer)
     */
    destroy() {
        this.hideHelp();
        this.operationHistory = [];
        this.confirmationCallbacks.clear();
        
        // 移除帮助按钮 (Remove help button)
        const helpButton = document.getElementById('help-button');
        if (helpButton && helpButton.parentNode) {
            helpButton.parentNode.removeChild(helpButton);
        }
        
        // 移除快捷键提示 (Remove shortcut hints)
        const hintsContainer = document.getElementById('shortcut-hints');
        if (hintsContainer && hintsContainer.parentNode) {
            hintsContainer.parentNode.removeChild(hintsContainer);
        }
    }
}

// --- ErrorHandler Class ---
class ErrorHandler {
    constructor(options = {}) {
        this.statusIndicator = options.statusIndicator;
        this.maxRetries = options.maxRetries || 3;
        this.retryDelay = options.retryDelay || 1000; // 1 second base delay
        this.retryMultiplier = options.retryMultiplier || 2; // Exponential backoff
        
        // 错误类型配置 (Error type configurations)
        this.errorTypes = {
            network: {
                message: 'Network connection failed. Please check your internet connection.',
                retryable: true,
                autoRetry: true
            },
            api: {
                message: 'Service temporarily unavailable. Please try again.',
                retryable: true,
                autoRetry: false
            },
            audio_validation: {
                message: 'Invalid audio file. Please record again.',
                retryable: false,
                autoRetry: false
            },
            transcription_timeout: {
                message: 'Speech recognition timed out. Please try again.',
                retryable: true,
                autoRetry: false
            },
            tts_quota_exceeded: {
                message: 'Voice synthesis service temporarily unavailable.',
                retryable: false,
                autoRetry: false
            },
            microphone_permission: {
                message: 'Microphone access denied. Please allow microphone access and try again.',
                retryable: false,
                autoRetry: false
            },
            browser_not_supported: {
                message: 'Voice recording is not supported in this browser.',
                retryable: false,
                autoRetry: false
            },
            file_too_large: {
                message: 'Audio file is too large. Please record a shorter message.',
                retryable: false,
                autoRetry: false
            }
        };
        
        // 重试状态 (Retry state)
        this.retryAttempts = new Map();
        this.activeRetries = new Set();
        
        // 回调函数 (Callback functions)
        this.onError = options.onError || (() => {});
        this.onRetry = options.onRetry || (() => {});
        this.onRetrySuccess = options.onRetrySuccess || (() => {});
        this.onRetryFailed = options.onRetryFailed || (() => {});
        
        // 网络状态监控 (Network status monitoring)
        this.isOnline = navigator.onLine;
        this.initializeNetworkMonitoring();
    }
    
    /**
     * 初始化网络状态监控 (Initialize network status monitoring)
     */
    initializeNetworkMonitoring() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.showConnectionStatus('online');
            console.log('Network connection restored');
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.showConnectionStatus('offline');
            console.log('Network connection lost');
        });
    }
    
    /**
     * 处理错误 (Handle error)
     */
    async handleError(error, context = {}) {
        const errorType = this.identifyErrorType(error);
        const errorConfig = this.errorTypes[errorType] || this.errorTypes.api;
        
        console.error(`Error handled: ${errorType}`, error, context);
        
        // 触发错误回调 (Trigger error callback)
        this.onError(error, errorType, context);
        
        // 检查是否可以重试 (Check if retryable)
        if (errorConfig.retryable && this.canRetry(context.operationId)) {
            if (errorConfig.autoRetry) {
                return await this.autoRetry(context);
            } else {
                this.showRetryOption(context, errorConfig.message);
                return false;
            }
        } else {
            this.showError(errorConfig.message, { retryable: false });
            return false;
        }
    }
    
    /**
     * 识别错误类型 (Identify error type)
     */
    identifyErrorType(error) {
        if (!this.isOnline) {
            return 'network';
        }
        
        if (error.name === 'NetworkError' || error.message.includes('fetch')) {
            return 'network';
        }
        
        if (error.message.includes('Permission denied')) {
            return 'microphone_permission';
        }
        
        if (error.message.includes('not supported')) {
            return 'browser_not_supported';
        }
        
        if (error.message.includes('too large')) {
            return 'file_too_large';
        }
        
        if (error.message.includes('timeout')) {
            return 'transcription_timeout';
        }
        
        if (error.message.includes('quota') || error.message.includes('limit')) {
            return 'tts_quota_exceeded';
        }
        
        if (error.message.includes('audio') && error.message.includes('validation')) {
            return 'audio_validation';
        }
        
        // 检查HTTP状态码 (Check HTTP status codes)
        if (error.status) {
            if (error.status >= 500) {
                return 'api';
            }
            if (error.status === 429) {
                return 'tts_quota_exceeded';
            }
            if (error.status === 408) {
                return 'transcription_timeout';
            }
        }
        
        return 'api';
    }
    
    /**
     * 检查是否可以重试 (Check if can retry)
     */
    canRetry(operationId) {
        if (!operationId) return false;
        
        const attempts = this.retryAttempts.get(operationId) || 0;
        return attempts < this.maxRetries;
    }
    
    /**
     * 自动重试 (Auto retry)
     */
    async autoRetry(context) {
        const { operationId, retryFunction } = context;
        
        if (!operationId || !retryFunction) {
            console.error('Auto retry failed: missing operationId or retryFunction');
            return false;
        }
        
        const attempts = this.retryAttempts.get(operationId) || 0;
        const delay = this.retryDelay * Math.pow(this.retryMultiplier, attempts);
        
        this.retryAttempts.set(operationId, attempts + 1);
        this.activeRetries.add(operationId);
        
        // 显示重试状态 (Show retry status)
        if (this.statusIndicator) {
            this.statusIndicator.showInfo(`Retrying... (${attempts + 1}/${this.maxRetries})`, {
                autoHide: false
            });
        }
        
        // 触发重试回调 (Trigger retry callback)
        this.onRetry(operationId, attempts + 1);
        
        try {
            // 等待延迟 (Wait for delay)
            await this.delay(delay);
            
            // 执行重试 (Execute retry)
            const result = await retryFunction();
            
            // 重试成功 (Retry successful)
            this.retryAttempts.delete(operationId);
            this.activeRetries.delete(operationId);
            
            if (this.statusIndicator) {
                this.statusIndicator.showSuccess('Operation completed successfully');
            }
            
            this.onRetrySuccess(operationId, attempts + 1);
            return result;
            
        } catch (retryError) {
            this.activeRetries.delete(operationId);
            
            // 检查是否还能继续重试 (Check if can continue retrying)
            if (this.canRetry(operationId)) {
                return await this.autoRetry(context);
            } else {
                // 重试失败 (Retry failed)
                this.retryAttempts.delete(operationId);
                
                if (this.statusIndicator) {
                    this.statusIndicator.showError('Operation failed after multiple attempts');
                }
                
                this.onRetryFailed(operationId, attempts + 1);
                return false;
            }
        }
    }
    
    /**
     * 显示重试选项 (Show retry option)
     */
    showRetryOption(context, message) {
        const { operationId, retryFunction } = context;
        
        if (this.statusIndicator) {
            this.statusIndicator.hide();
        }
        
        // 创建重试界面 (Create retry interface)
        this.createRetryInterface(message, async () => {
            if (retryFunction) {
                try {
                    const result = await retryFunction();
                    this.hideRetryInterface();
                    
                    if (this.statusIndicator) {
                        this.statusIndicator.showSuccess('Operation completed successfully');
                    }
                    
                    return result;
                } catch (error) {
                    await this.handleError(error, context);
                }
            }
        });
    }
    
    /**
     * 创建重试界面 (Create retry interface)
     */
    createRetryInterface(message, retryCallback) {
        // 移除现有的重试界面 (Remove existing retry interface)
        this.hideRetryInterface();
        
        const retryContainer = document.createElement('div');
        retryContainer.id = 'retry-container';
        retryContainer.className = 'retry-container';
        
        retryContainer.innerHTML = `
            <div class="retry-message">${message}</div>
            <button id="retry-button" class="retry-button">
                <i class="fas fa-redo"></i>
                <span>Try Again</span>
            </button>
        `;
        
        // 添加到页面 (Add to page)
        const chatContainer = document.querySelector('.chat-container') || document.body;
        chatContainer.appendChild(retryContainer);
        
        // 添加事件监听器 (Add event listener)
        const retryButton = retryContainer.querySelector('#retry-button');
        retryButton.addEventListener('click', async () => {
            retryButton.classList.add('btn-loading');
            retryButton.disabled = true;
            
            try {
                await retryCallback();
            } finally {
                retryButton.classList.remove('btn-loading');
                retryButton.disabled = false;
            }
        });
    }
    
    /**
     * 隐藏重试界面 (Hide retry interface)
     */
    hideRetryInterface() {
        const retryContainer = document.getElementById('retry-container');
        if (retryContainer) {
            retryContainer.remove();
        }
    }
    
    /**
     * 显示错误信息 (Show error message)
     */
    showError(message, options = {}) {
        if (this.statusIndicator) {
            this.statusIndicator.showError(message, options);
        }
        
        // 如果不可重试，显示详细错误信息 (If not retryable, show detailed error)
        if (!options.retryable) {
            this.createErrorMessage(message);
        }
    }
    
    /**
     * 创建错误消息 (Create error message)
     */
    createErrorMessage(message) {
        const errorContainer = document.createElement('div');
        errorContainer.className = 'error-message';
        
        errorContainer.innerHTML = `
            <i class="fas fa-exclamation-triangle error-icon"></i>
            <div class="error-text">${message}</div>
        `;
        
        // 添加到聊天框 (Add to chat box)
        const chatBox = document.getElementById('chat-box');
        if (chatBox) {
            chatBox.appendChild(errorContainer);
            chatBox.scrollTop = chatBox.scrollHeight;
            
            // 自动移除错误消息 (Auto remove error message)
            setTimeout(() => {
                if (errorContainer.parentNode) {
                    errorContainer.remove();
                }
            }, 10000);
        }
    }
    
    /**
     * 显示连接状态 (Show connection status)
     */
    showConnectionStatus(status) {
        const connectionStatus = document.getElementById('connection-status');
        if (!connectionStatus) return;
        
        connectionStatus.className = `connection-status ${status}`;
        
        const indicator = connectionStatus.querySelector('.connection-indicator');
        const text = connectionStatus.querySelector('.connection-text');
        
        if (status === 'online') {
            text.textContent = 'Online';
            indicator.classList.remove('pulse');
            connectionStatus.classList.add('visible');
            
            // 3秒后隐藏 (Hide after 3 seconds)
            setTimeout(() => {
                connectionStatus.classList.remove('visible');
            }, 3000);
        } else {
            text.textContent = 'Offline';
            indicator.classList.add('pulse');
            connectionStatus.classList.add('visible');
        }
    }
    
    /**
     * 延迟函数 (Delay function)
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    /**
     * 重置重试计数 (Reset retry count)
     */
    resetRetryCount(operationId) {
        this.retryAttempts.delete(operationId);
        this.activeRetries.delete(operationId);
    }
    
    /**
     * 获取重试状态 (Get retry status)
     */
    getRetryStatus(operationId) {
        return {
            attempts: this.retryAttempts.get(operationId) || 0,
            isRetrying: this.activeRetries.has(operationId),
            canRetry: this.canRetry(operationId)
        };
    }
    
    /**
     * 销毁错误处理器 (Destroy error handler)
     */
    destroy() {
        this.hideRetryInterface();
        this.retryAttempts.clear();
        this.activeRetries.clear();
        
        window.removeEventListener('online', this.handleOnline);
        window.removeEventListener('offline', this.handleOffline);
    }
}

// --- StatusIndicator Class ---
class StatusIndicator {
    constructor(options = {}) {
        this.container = options.container || document.getElementById('status-indicator');
        this.textElement = options.textElement || document.getElementById('status-text');
        this.iconElement = options.iconElement || document.getElementById('status-icon');
        this.progressElement = options.progressElement || document.getElementById('status-progress');
        
        // 状态配置 (Status configurations)
        this.statusConfig = {
            loading: {
                icon: 'fas fa-spinner fa-spin',
                className: 'status-loading',
                showProgress: false
            },
            success: {
                icon: 'fas fa-check-circle',
                className: 'status-success',
                showProgress: false
            },
            error: {
                icon: 'fas fa-exclamation-triangle',
                className: 'status-error',
                showProgress: false
            },
            warning: {
                icon: 'fas fa-exclamation-circle',
                className: 'status-warning',
                showProgress: false
            },
            info: {
                icon: 'fas fa-info-circle',
                className: 'status-info',
                showProgress: false
            },
            recording: {
                icon: 'fas fa-microphone',
                className: 'status-recording',
                showProgress: true
            },
            processing: {
                icon: 'fas fa-cog fa-spin',
                className: 'status-processing',
                showProgress: true
            },
            playing: {
                icon: 'fas fa-volume-up',
                className: 'status-playing',
                showProgress: true
            }
        };
        
        // 当前状态 (Current state)
        this.currentStatus = null;
        this.isVisible = false;
        this.hideTimeout = null;
        this.progressValue = 0;
        
        // 回调函数 (Callback functions)
        this.onShow = options.onShow || (() => {});
        this.onHide = options.onHide || (() => {});
        this.onStatusChange = options.onStatusChange || (() => {});
        
        this.initializeElements();
    }
    
    /**
     * 初始化状态指示器元素 (Initialize status indicator elements)
     */
    initializeElements() {
        if (!this.container) {
            this.createStatusIndicator();
        }
        
        // 确保所有必要的子元素存在 (Ensure all necessary child elements exist)
        if (!this.iconElement) {
            this.iconElement = this.container.querySelector('.status-icon') || this.createIconElement();
        }
        
        if (!this.textElement) {
            this.textElement = this.container.querySelector('.status-text') || this.createTextElement();
        }
        
        if (!this.progressElement) {
            this.progressElement = this.container.querySelector('.status-progress') || this.createProgressElement();
        }
        
        // 初始隐藏 (Initially hidden)
        this.container.style.display = 'none';
    }
    
    /**
     * 创建状态指示器容器 (Create status indicator container)
     */
    createStatusIndicator() {
        this.container = document.createElement('div');
        this.container.id = 'status-indicator';
        this.container.className = 'status-indicator';
        
        // 添加到页面 (Add to page)
        const chatContainer = document.querySelector('.chat-container') || document.body;
        chatContainer.appendChild(this.container);
    }
    
    /**
     * 创建图标元素 (Create icon element)
     */
    createIconElement() {
        const icon = document.createElement('i');
        icon.className = 'status-icon';
        this.container.appendChild(icon);
        return icon;
    }
    
    /**
     * 创建文本元素 (Create text element)
     */
    createTextElement() {
        const text = document.createElement('span');
        text.className = 'status-text';
        this.container.appendChild(text);
        return text;
    }
    
    /**
     * 创建进度元素 (Create progress element)
     */
    createProgressElement() {
        const progressContainer = document.createElement('div');
        progressContainer.className = 'status-progress-container';
        
        const progressBar = document.createElement('div');
        progressBar.className = 'status-progress';
        
        progressContainer.appendChild(progressBar);
        this.container.appendChild(progressContainer);
        
        return progressBar;
    }
    
    /**
     * 显示状态指示器 (Show status indicator)
     */
    show(type, message, options = {}) {
        const config = this.statusConfig[type] || this.statusConfig.info;
        
        // 清除之前的隐藏定时器 (Clear previous hide timeout)
        if (this.hideTimeout) {
            clearTimeout(this.hideTimeout);
            this.hideTimeout = null;
        }
        
        // 更新状态 (Update status)
        this.currentStatus = type;
        this.isVisible = true;
        
        // 更新样式类 (Update style classes)
        this.container.className = `status-indicator ${config.className}`;
        
        // 更新图标 (Update icon)
        if (this.iconElement) {
            this.iconElement.className = `status-icon ${config.icon}`;
        }
        
        // 更新文本 (Update text)
        if (this.textElement) {
            this.textElement.textContent = message;
        }
        
        // 处理进度条 (Handle progress bar)
        if (config.showProgress && this.progressElement) {
            this.progressElement.parentElement.style.display = 'block';
            this.updateProgress(options.progress || 0);
        } else if (this.progressElement) {
            this.progressElement.parentElement.style.display = 'none';
        }
        
        // 显示容器 (Show container)
        this.container.style.display = 'flex';
        
        // 添加显示动画 (Add show animation)
        this.container.style.opacity = '0';
        this.container.style.transform = 'translateY(-10px)';
        
        requestAnimationFrame(() => {
            this.container.style.transition = 'all 0.3s ease-out';
            this.container.style.opacity = '1';
            this.container.style.transform = 'translateY(0)';
        });
        
        // 自动隐藏设置 (Auto-hide setting)
        const autoHideDelay = options.autoHide !== false ? (options.autoHideDelay || 3000) : null;
        if (autoHideDelay && type !== 'loading' && type !== 'processing' && type !== 'recording') {
            this.hideTimeout = setTimeout(() => {
                this.hide();
            }, autoHideDelay);
        }
        
        // 触发回调 (Trigger callbacks)
        this.onShow(type, message);
        this.onStatusChange(type, message);
    }
    
    /**
     * 隐藏状态指示器 (Hide status indicator)
     */
    hide() {
        if (!this.isVisible) return;
        
        // 清除隐藏定时器 (Clear hide timeout)
        if (this.hideTimeout) {
            clearTimeout(this.hideTimeout);
            this.hideTimeout = null;
        }
        
        // 添加隐藏动画 (Add hide animation)
        this.container.style.transition = 'all 0.3s ease-in';
        this.container.style.opacity = '0';
        this.container.style.transform = 'translateY(-10px)';
        
        setTimeout(() => {
            this.container.style.display = 'none';
            this.isVisible = false;
            this.currentStatus = null;
            this.progressValue = 0;
            
            // 触发回调 (Trigger callback)
            this.onHide();
        }, 300);
    }
    
    /**
     * 更新进度 (Update progress)
     */
    updateProgress(value) {
        this.progressValue = Math.max(0, Math.min(100, value));
        
        if (this.progressElement) {
            this.progressElement.style.width = `${this.progressValue}%`;
        }
    }
    
    /**
     * 更新状态消息 (Update status message)
     */
    updateMessage(message) {
        if (this.textElement) {
            this.textElement.textContent = message;
        }
    }
    
    /**
     * 显示加载状态 (Show loading status)
     */
    showLoading(message = 'Loading...', options = {}) {
        this.show('loading', message, { autoHide: false, ...options });
    }
    
    /**
     * 显示成功状态 (Show success status)
     */
    showSuccess(message = 'Success!', options = {}) {
        this.show('success', message, { autoHideDelay: 2000, ...options });
    }
    
    /**
     * 显示错误状态 (Show error status)
     */
    showError(message = 'Error occurred', options = {}) {
        this.show('error', message, { autoHideDelay: 5000, ...options });
    }
    
    /**
     * 显示警告状态 (Show warning status)
     */
    showWarning(message = 'Warning', options = {}) {
        this.show('warning', message, { autoHideDelay: 4000, ...options });
    }
    
    /**
     * 显示信息状态 (Show info status)
     */
    showInfo(message = 'Information', options = {}) {
        this.show('info', message, { autoHideDelay: 3000, ...options });
    }
    
    /**
     * 显示录音状态 (Show recording status)
     */
    showRecording(message = 'Recording...', options = {}) {
        this.show('recording', message, { autoHide: false, ...options });
    }
    
    /**
     * 显示处理状态 (Show processing status)
     */
    showProcessing(message = 'Processing...', options = {}) {
        this.show('processing', message, { autoHide: false, ...options });
    }
    
    /**
     * 显示播放状态 (Show playing status)
     */
    showPlaying(message = 'Playing audio...', options = {}) {
        this.show('playing', message, { autoHide: false, ...options });
    }
    
    /**
     * 获取当前状态 (Get current status)
     */
    getCurrentStatus() {
        return {
            type: this.currentStatus,
            isVisible: this.isVisible,
            progress: this.progressValue
        };
    }
    
    /**
     * 销毁状态指示器 (Destroy status indicator)
     */
    destroy() {
        if (this.hideTimeout) {
            clearTimeout(this.hideTimeout);
        }
        
        if (this.container && this.container.parentNode) {
            this.container.parentNode.removeChild(this.container);
        }
        
        this.container = null;
        this.textElement = null;
        this.iconElement = null;
        this.progressElement = null;
    }
}

// --- AudioPlayer Class ---
class AudioPlayer {
    constructor(options = {}) {
        this.audioElement = options.audioElement || document.getElementById('tts-audio');
        this.isPlaying = false;
        this.isPaused = false;
        this.currentAudio = null;
        this.playbackRate = 1.0;
        this.volume = 1.0;
        
        // 回调函数 (Callback functions)
        this.onPlayStart = options.onPlayStart || (() => {});
        this.onPlayEnd = options.onPlayEnd || (() => {});
        this.onPlayPause = options.onPlayPause || (() => {});
        this.onPlayResume = options.onPlayResume || (() => {});
        this.onError = options.onError || ((error) => console.error('AudioPlayer Error:', error));
        this.onProgress = options.onProgress || (() => {});
        
        // 配置选项 (Configuration options)
        this.autoPlay = options.autoPlay !== false; // 默认自动播放
        this.showControls = options.showControls !== false; // 默认显示控制按钮
        this.enableProgress = options.enableProgress !== false; // 默认启用进度跟踪
        
        // 进度跟踪 (Progress tracking)
        this.progressInterval = null;
        this.progressUpdateRate = options.progressUpdateRate || 100; // 100ms更新间隔
        
        this.initializeAudioElement();
    }
    
    /**
     * 初始化音频元素 (Initialize audio element)
     */
    initializeAudioElement() {
        if (!this.audioElement) {
            console.warn('Audio element not found, creating new one');
            this.audioElement = document.createElement('audio');
            this.audioElement.id = 'tts-audio';
            this.audioElement.preload = 'none';
            document.body.appendChild(this.audioElement);
        }
        
        // 设置事件监听器 (Set up event listeners)
        this.audioElement.addEventListener('ended', () => this.handlePlayEnd());
        this.audioElement.addEventListener('error', (event) => this.handleError(event));
        this.audioElement.addEventListener('loadstart', () => this.handleLoadStart());
        this.audioElement.addEventListener('canplay', () => this.handleCanPlay());
        this.audioElement.addEventListener('pause', () => this.handlePause());
        this.audioElement.addEventListener('play', () => this.handlePlay());
        
        // 设置默认属性 (Set default properties)
        this.audioElement.volume = this.volume;
        this.audioElement.playbackRate = this.playbackRate;
    }
    
    /**
     * 播放Base64编码的音频 (Play Base64 encoded audio)
     */
    async playBase64Audio(base64Data, options = {}) {
        if (!base64Data) {
            this.onError(new Error('No audio data provided'));
            return false;
        }
        
        try {
            // 停止当前播放 (Stop current playback)
            this.stop();
            
            // 设置播放选项 (Set playback options)
            const playbackRate = options.playbackRate || this.playbackRate;
            const volume = options.volume !== undefined ? options.volume : this.volume;
            const autoPlay = options.autoPlay !== undefined ? options.autoPlay : this.autoPlay;
            
            // 设置音频源 (Set audio source)
            const audioSrc = base64Data.startsWith('data:') ? 
                base64Data : `data:audio/mp3;base64,${base64Data}`;
            
            this.audioElement.src = audioSrc;
            this.audioElement.playbackRate = playbackRate;
            this.audioElement.volume = volume;
            
            // 存储当前音频信息 (Store current audio info)
            this.currentAudio = {
                base64Data: base64Data,
                playbackRate: playbackRate,
                volume: volume,
                timestamp: Date.now()
            };
            
            if (autoPlay) {
                await this.audioElement.play();
            }
            
            return true;
            
        } catch (error) {
            this.onError(error);
            return false;
        }
    }
    
    /**
     * 播放音频 (Play audio)
     */
    async play() {
        if (!this.audioElement.src) {
            this.onError(new Error('No audio source available'));
            return false;
        }
        
        try {
            await this.audioElement.play();
            return true;
        } catch (error) {
            this.onError(error);
            return false;
        }
    }
    
    /**
     * 暂停播放 (Pause playback)
     */
    pause() {
        if (this.isPlaying && !this.audioElement.paused) {
            this.audioElement.pause();
            return true;
        }
        return false;
    }
    
    /**
     * 停止播放 (Stop playback)
     */
    stop() {
        if (this.audioElement) {
            this.audioElement.pause();
            this.audioElement.currentTime = 0;
            this.clearProgressTracking();
            this.isPlaying = false;
            this.isPaused = false;
        }
    }
    
    /**
     * 重播当前音频 (Replay current audio)
     */
    async replay() {
        if (this.currentAudio) {
            return await this.playBase64Audio(this.currentAudio.base64Data, {
                playbackRate: this.currentAudio.playbackRate,
                volume: this.currentAudio.volume
            });
        } else {
            this.onError(new Error('No audio to replay'));
            return false;
        }
    }
    
    /**
     * 设置播放速度 (Set playback rate)
     */
    setPlaybackRate(rate) {
        if (rate > 0 && rate <= 3) {
            this.playbackRate = rate;
            if (this.audioElement) {
                this.audioElement.playbackRate = rate;
            }
            if (this.currentAudio) {
                this.currentAudio.playbackRate = rate;
            }
        }
    }
    
    /**
     * 设置音量 (Set volume)
     */
    setVolume(volume) {
        if (volume >= 0 && volume <= 1) {
            this.volume = volume;
            if (this.audioElement) {
                this.audioElement.volume = volume;
            }
            if (this.currentAudio) {
                this.currentAudio.volume = volume;
            }
        }
    }
    
    /**
     * 获取播放状态 (Get playback state)
     */
    getState() {
        return {
            isPlaying: this.isPlaying,
            isPaused: this.isPaused,
            currentTime: this.audioElement ? this.audioElement.currentTime : 0,
            duration: this.audioElement ? this.audioElement.duration : 0,
            playbackRate: this.playbackRate,
            volume: this.volume,
            hasAudio: !!this.currentAudio
        };
    }
    
    /**
     * 开始进度跟踪 (Start progress tracking)
     */
    startProgressTracking() {
        if (!this.enableProgress) return;
        
        this.clearProgressTracking();
        this.progressInterval = setInterval(() => {
            if (this.isPlaying && this.audioElement) {
                const progress = {
                    currentTime: this.audioElement.currentTime,
                    duration: this.audioElement.duration || 0,
                    percentage: this.audioElement.duration ? 
                        (this.audioElement.currentTime / this.audioElement.duration) * 100 : 0
                };
                this.onProgress(progress);
            }
        }, this.progressUpdateRate);
    }
    
    /**
     * 清除进度跟踪 (Clear progress tracking)
     */
    clearProgressTracking() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
    }
    
    /**
     * 处理播放开始事件 (Handle play start event)
     */
    handlePlay() {
        this.isPlaying = true;
        this.isPaused = false;
        this.startProgressTracking();
        this.onPlayStart();
    }
    
    /**
     * 处理播放结束事件 (Handle play end event)
     */
    handlePlayEnd() {
        this.isPlaying = false;
        this.isPaused = false;
        this.clearProgressTracking();
        this.onPlayEnd();
    }
    
    /**
     * 处理暂停事件 (Handle pause event)
     */
    handlePause() {
        if (this.isPlaying) {
            this.isPaused = true;
            this.isPlaying = false;
            this.clearProgressTracking();
            this.onPlayPause();
        }
    }
    
    /**
     * 处理错误事件 (Handle error event)
     */
    handleError(event) {
        this.isPlaying = false;
        this.isPaused = false;
        this.clearProgressTracking();
        
        const error = new Error(`Audio playback error: ${event.target.error?.message || 'Unknown error'}`);
        this.onError(error);
    }
    
    /**
     * 处理加载开始事件 (Handle load start event)
     */
    handleLoadStart() {
        // 可以在这里添加加载状态指示
    }
    
    /**
     * 处理可以播放事件 (Handle can play event)
     */
    handleCanPlay() {
        // 音频已准备好播放
    }
    
    /**
     * 销毁播放器实例 (Destroy player instance)
     */
    destroy() {
        this.stop();
        this.clearProgressTracking();
        
        if (this.audioElement) {
            // 移除事件监听器 (Remove event listeners)
            this.audioElement.removeEventListener('ended', this.handlePlayEnd);
            this.audioElement.removeEventListener('error', this.handleError);
            this.audioElement.removeEventListener('loadstart', this.handleLoadStart);
            this.audioElement.removeEventListener('canplay', this.handleCanPlay);
            this.audioElement.removeEventListener('pause', this.handlePause);
            this.audioElement.removeEventListener('play', this.handlePlay);
        }
        
        this.currentAudio = null;
    }
}

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
    
    // 创建状态指示器实例 (Create status indicator instance)
    const statusIndicator = new StatusIndicator({
        container: document.getElementById('status-indicator'),
        textElement: document.getElementById('status-text'),
        iconElement: document.getElementById('status-icon'),
        progressElement: document.getElementById('status-progress'),
        onShow: (type, message) => {
            console.log(`Status shown: ${type} - ${message}`);
        },
        onHide: () => {
            console.log('Status hidden');
        },
        onStatusChange: (type, message) => {
            console.log(`Status changed: ${type} - ${message}`);
        }
    });
    
    // 创建错误处理器实例 (Create error handler instance)
    const errorHandler = new ErrorHandler({
        statusIndicator: statusIndicator,
        maxRetries: 3,
        retryDelay: 1000,
        retryMultiplier: 2,
        onError: (error, errorType, context) => {
            console.error(`Error handled by ErrorHandler: ${errorType}`, error, context);
        },
        onRetry: (operationId, attempt) => {
            console.log(`Retrying operation ${operationId}, attempt ${attempt}`);
        },
        onRetrySuccess: (operationId, attempts) => {
            console.log(`Operation ${operationId} succeeded after ${attempts} attempts`);
        },
        onRetryFailed: (operationId, attempts) => {
            console.error(`Operation ${operationId} failed after ${attempts} attempts`);
        }
    });
    
    // 创建UX增强器实例 (Create UX enhancer instance)
    const uxEnhancer = new UXEnhancer({
        statusIndicator: statusIndicator,
        errorHandler: errorHandler,
        onShortcut: (action, event) => {
            console.log(`Keyboard shortcut executed: ${action}`);
        },
        onUndo: (operation) => {
            console.log(`Operation undone:`, operation);
        },
        onHelp: (visible) => {
            console.log(`Help ${visible ? 'shown' : 'hidden'}`);
        }
    });
    
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
    
    // 创建音频播放器实例 (Create audio player instance)
    const audioPlayer = new AudioPlayer({
        audioElement: ttsAudio,
        onPlayStart: () => {
            console.log('TTS audio playback started');
            showAudioPlaybackStatus('playing');
            updateAudioControlsState('playing');
        },
        onPlayEnd: () => {
            console.log('TTS audio playback ended');
            showAudioPlaybackStatus('completed');
            updateAudioControlsState('stopped');
            
            // 播放完成后重置状态 (Reset state after playback completion)
            setTimeout(() => {
                hideStatus();
            }, 1000);
        },
        onPlayPause: () => {
            console.log('TTS audio playback paused');
            showAudioPlaybackStatus('paused');
            updateAudioControlsState('paused');
        },
        onPlayResume: () => {
            console.log('TTS audio playback resumed');
            showAudioPlaybackStatus('playing');
            updateAudioControlsState('playing');
        },
        onError: (error) => {
            console.error('TTS audio playback error:', error);
            showAudioPlaybackStatus('error');
            updateAudioControlsState('error');
            
            // 错误后重置状态 (Reset state after error)
            setTimeout(() => {
                hideStatus();
            }, 3000);
        },
        onProgress: (progress) => {
            // 更新进度条 (Update progress bar)
            updateAudioProgress(progress);
        },
        autoPlay: true,
        showControls: true,
        enableProgress: true
    });

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
    
    // Audio control event listeners
    const replayTtsBtn = document.getElementById('replay-tts-btn');
    const slowTtsBtn = document.getElementById('slow-tts-btn');
    const stopTtsBtn = document.getElementById('stop-tts-btn');
    const playTtsBtn = document.getElementById('play-tts-btn');
    
    if (replayTtsBtn) {
        replayTtsBtn.addEventListener('click', replayCurrentAudio);
    }
    if (slowTtsBtn) {
        slowTtsBtn.addEventListener('click', playSlowAudio);
    }
    if (stopTtsBtn) {
        stopTtsBtn.addEventListener('click', stopCurrentAudio);
    }
    if (playTtsBtn) {
        playTtsBtn.addEventListener('click', playCurrentAudio);
    }
    
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
        } else {
            // 全局音频控制快捷键 (Global audio control shortcuts)
            if (e.key === ' ' && (e.ctrlKey || e.metaKey)) {
                // Ctrl/Cmd + Space: 暂停/恢复播放 (Pause/resume playback)
                e.preventDefault();
                toggleAudioPlayback();
            } else if (e.key === 'r' && (e.ctrlKey || e.metaKey) && e.shiftKey) {
                // Ctrl/Cmd + Shift + R: 重播音频 (Replay audio)
                e.preventDefault();
                replayCurrentAudio();
            } else if (e.key === 's' && (e.ctrlKey || e.metaKey) && e.shiftKey) {
                // Ctrl/Cmd + Shift + S: 停止播放 (Stop playback)
                e.preventDefault();
                stopCurrentAudio();
            } else if (e.key === 'ArrowUp' && (e.ctrlKey || e.metaKey)) {
                // Ctrl/Cmd + Arrow Up: 增加音量 (Increase volume)
                e.preventDefault();
                const currentVolume = audioPlayer.volume;
                setAudioVolume(Math.min(1, currentVolume + 0.1));
            } else if (e.key === 'ArrowDown' && (e.ctrlKey || e.metaKey)) {
                // Ctrl/Cmd + Arrow Down: 减少音量 (Decrease volume)
                e.preventDefault();
                const currentVolume = audioPlayer.volume;
                setAudioVolume(Math.max(0, currentVolume - 0.1));
            } else if (e.key === 'ArrowRight' && (e.ctrlKey || e.metaKey)) {
                // Ctrl/Cmd + Arrow Right: 加速播放 (Increase speed)
                e.preventDefault();
                const currentRate = audioPlayer.playbackRate;
                setAudioPlaybackRate(Math.min(3, currentRate + 0.25));
            } else if (e.key === 'ArrowLeft' && (e.ctrlKey || e.metaKey)) {
                // Ctrl/Cmd + Arrow Left: 减速播放 (Decrease speed)
                e.preventDefault();
                const currentRate = audioPlayer.playbackRate;
                setAudioPlaybackRate(Math.max(0.25, currentRate - 0.25));
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
        statusIndicator.showLoading(message);
    }
    
    function showRecordingStatus(message) {
        statusIndicator.showRecording(message);
        
        // 显示录音计时器 (Show recording timer)
        const recordingTimerEl = document.getElementById('recording-timer');
        if (recordingTimerEl) {
            recordingTimerEl.style.display = 'block';
        }
        
        // 禁用文本输入和发送按钮 (Disable text input and send button)
        textInput.disabled = true;
        sendTextBtn.disabled = true;
    }
    
    function showProcessingStatus(message) {
        statusIndicator.showProcessing(message);
        
        // 隐藏录音计时器 (Hide recording timer)
        const recordingTimerEl = document.getElementById('recording-timer');
        if (recordingTimerEl) {
            recordingTimerEl.style.display = 'none';
        }
        
        // 禁用所有输入控件 (Disable all input controls)
        textInput.disabled = true;
        recordBtn.disabled = true;
        sendTextBtn.disabled = true;
    }
    
    function showErrorStatus(message) {
        statusIndicator.showError(message);
        
        // 隐藏录音计时器 (Hide recording timer)
        const recordingTimerEl = document.getElementById('recording-timer');
        if (recordingTimerEl) {
            recordingTimerEl.style.display = 'none';
        }
    }
    
    function showSuccessStatus(message) {
        statusIndicator.showSuccess(message);
    }
    
    function showAudioPlaybackStatus(status) {
        let message;
        switch(status) {
            case 'playing':
                message = 'Playing audio...';
                statusIndicator.showPlaying(message);
                break;
            case 'paused':
                message = 'Audio paused';
                statusIndicator.showInfo(message);
                break;
            case 'completed':
                message = 'Audio completed';
                statusIndicator.showSuccess(message);
                break;
            case 'error':
                message = 'Audio playback error';
                statusIndicator.showError(message);
                break;
            default:
                return;
        }
    }

    function hideStatus() {
        statusIndicator.hide();
        
        // 隐藏录音计时器 (Hide recording timer)
        const recordingTimerEl = document.getElementById('recording-timer');
        if (recordingTimerEl) {
            recordingTimerEl.style.display = 'none';
        }
        
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
    
    // 存储当前AI回复数据 (Store current AI response data)
    let currentAIResponse = null;
    
    // 音频播放用户偏好设置 (Audio playback user preferences)
    let audioPreferences = {
        autoPlay: true,
        defaultVolume: 1.0,
        defaultSpeed: 1.0,
        showControls: true,
        enableKeyboardShortcuts: true
    };
    
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
        
        // 记录操作用于撤销 (Record operation for undo)
        uxEnhancer.recordOperation('text_edited', {
            previousText: originalTranscribedText,
            newText: editedText
        });
        
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
        const operationId = `retranslate_${Date.now()}`;
        
        if (!editedText) {
            showErrorStatus('Please enter some text to translate.');
            setTimeout(() => hideStatus(), 2000);
            return;
        }
        
        // 添加重新翻译动画 (Add re-translate animation)
        retranslateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Translating...';
        retranslateBtn.disabled = true;
        
        const retranslateOperation = async () => {
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
                const error = new Error(`HTTP ${response.status}: ${response.statusText}`);
                error.status = response.status;
                throw error;
            }
            
            const data = await response.json();
            if (!data.success) {
                const error = new Error(data.error || 'Re-translation failed.');
                error.status = data.status;
                throw error;
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
            
            return data;
        };
        
        try {
            return await retranslateOperation();
        } catch (error) {
            console.error('Re-translation Error:', error);
            
            // 使用错误处理器处理错误 (Use error handler to handle error)
            const handled = await errorHandler.handleError(error, {
                operationId: operationId,
                retryFunction: retranslateOperation,
                context: 'retranslation'
            });
            
            return handled;
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
    async function transcribeAudio(audioBlob) {
        const operationId = `transcribe_${Date.now()}`;
        
        const transcribeOperation = async () => {
            showProcessingStatus('Processing audio...');
            
            // 验证音频文件 (Validate audio file)
            const validation = audioProcessor.validateAudioFile(audioBlob);
            if (!validation.isValid) {
                const error = new Error(`Audio validation failed: ${validation.errors.join(', ')}`);
                error.name = 'AudioValidationError';
                throw error;
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
                const error = new Error(data.error || 'Transcription failed.');
                error.status = data.status;
                throw error;
            }
            
            hideStatus();
            
            // 集成确认流程到聊天逻辑 (Integrate confirmation flow into chat logic)
            showConfirmationWithValidation(data.chinese_text, data.english_translation, data);
            
            return data;
        };
        
        try {
            return await transcribeOperation();
        } catch (error) {
            console.error('Transcription Error:', error);
            
            // 使用错误处理器处理错误 (Use error handler to handle error)
            const handled = await errorHandler.handleError(error, {
                operationId: operationId,
                retryFunction: transcribeOperation,
                context: 'audio_transcription'
            });
            
            if (!handled) {
                setTimeout(() => resetInputState(), 3000);
            }
            
            return handled;
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
        const operationId = `send_message_${Date.now()}`;
        
        // Add user message to chat immediately
        appendMessage('user', { 
            chinese_text: message,
            input_method: inputMethod,
            english_translation: messageData.englishTranslation
        });
        
        // 记录操作用于撤销 (Record operation for undo)
        uxEnhancer.recordOperation('message_sent', {
            message: message,
            inputMethod: inputMethod,
            englishTranslation: messageData.englishTranslation
        });
        
        const sendOperation = async () => {
            showProcessingStatus('AI is thinking...');

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
                const error = new Error(`HTTP ${response.status}: ${response.statusText}`);
                error.status = response.status;
                throw error;
            }
            
            const data = await response.json();
            if (!data.success) {
                const error = new Error(data.error || 'Chat API failed.');
                error.status = data.status;
                throw error;
            }
            
            // Add AI response with delay for better UX
            setTimeout(() => {
                appendMessage('ai', data.ai_response);
                
                // Update token information display
                if (data.token_info) {
                    updateTokenDisplay(data.token_info);
                }
                
                // Play TTS audio if available with enhanced state management
                if (data.tts_audio) {
                    playAudioWithStateManagement(data.tts_audio, data.ai_response);
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
            
            return data;
        };

        try {
            return await sendOperation();
        } catch (error) {
            console.error('Chat Error:', error);
            
            // 使用错误处理器处理错误 (Use error handler to handle error)
            const handled = await errorHandler.handleError(error, {
                operationId: operationId,
                retryFunction: sendOperation,
                context: 'chat_message'
            });
            
            if (!handled) {
                setTimeout(() => resetInputState(), 3000);
            }
            
            return handled;
        } finally {
            // 只有在没有错误时才重置状态 (Only reset state if no error)
            if (!statusIndicator.getCurrentStatus().isVisible || 
                statusIndicator.getCurrentStatus().type === 'success') {
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
                <div class="audio-status-indicator" id="audio-status-${Date.now()}" style="
                    margin-top: 0.75rem;
                    padding: 0.5rem;
                    background: rgba(59, 130, 246, 0.1);
                    border: 1px solid rgba(59, 130, 246, 0.2);
                    border-radius: 0.5rem;
                    font-size: 0.75rem;
                    color: #3b82f6;
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                ">
                    <i class="fas fa-volume-up" style="color: #3b82f6;"></i>
                    <span>Audio will play automatically</span>
                </div>
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
        if (base64Audio) {
            audioPlayer.playBase64Audio(base64Audio).catch(error => {
                console.error('Audio playback failed:', error);
            });
        }
    }
    
    /**
     * 播放音频并管理状态 (Play audio with state management)
     */
    function playAudioWithStateManagement(base64Audio, aiResponse) {
        if (!base64Audio) {
            console.warn('No TTS audio available for AI response');
            return;
        }
        
        // 存储当前AI回复信息用于重播 (Store current AI response info for replay)
        currentAIResponse = {
            audio: base64Audio,
            response: aiResponse,
            timestamp: Date.now()
        };
        
        // 显示播放状态指示器 (Show playback status indicator)
        showAudioPlaybackStatus('preparing');
        
        // 播放音频 (Play audio)
        audioPlayer.playBase64Audio(base64Audio, {
            autoPlay: true,
            playbackRate: 1.0,
            volume: 1.0
        }).then(success => {
            if (success) {
                console.log('AI response TTS playback started successfully');
            } else {
                console.error('Failed to start AI response TTS playback');
                showAudioPlaybackStatus('error');
            }
        }).catch(error => {
            console.error('AI response TTS playback error:', error);
            showAudioPlaybackStatus('error');
        });
    }
    
    // --- Audio Control Functions ---
    function updateAudioControlsState(state) {
        // 更新音频控制按钮状态 (Update audio control button states)
        const audioControlButtons = document.querySelectorAll('.audio-control-btn');
        
        audioControlButtons.forEach(btn => {
            btn.classList.remove('playing', 'paused', 'error');
            
            switch(state) {
                case 'playing':
                    if (btn.id === 'stop-tts-btn') {
                        btn.classList.add('playing');
                        btn.disabled = false;
                    } else {
                        btn.disabled = true;
                    }
                    break;
                    
                case 'paused':
                    btn.classList.add('paused');
                    btn.disabled = false;
                    break;
                    
                case 'stopped':
                case 'error':
                    btn.disabled = false;
                    if (state === 'error') {
                        btn.classList.add('error');
                    }
                    break;
                    
                default:
                    btn.disabled = false;
                    break;
            }
        });
        
        console.log('Audio control state updated:', state);
    }
    
    function showAudioFeedback(message, type = 'info') {
        // 显示音频反馈信息 (Show audio feedback information)
        const feedbackElement = document.getElementById('audio-feedback');
        const feedbackMessage = document.getElementById('feedback-message');
        
        if (feedbackElement && feedbackMessage) {
            // 更新消息内容 (Update message content)
            const textSpan = feedbackMessage.querySelector('span') || feedbackMessage;
            textSpan.textContent = message;
            
            // 更新图标和样式 (Update icon and style)
            const icon = feedbackMessage.querySelector('i');
            if (icon) {
                switch(type) {
                    case 'success':
                        icon.className = 'fas fa-check-circle';
                        feedbackMessage.className = 'feedback-message success';
                        break;
                    case 'error':
                        icon.className = 'fas fa-exclamation-triangle';
                        feedbackMessage.className = 'feedback-message error';
                        break;
                    case 'info':
                    default:
                        icon.className = 'fas fa-info-circle';
                        feedbackMessage.className = 'feedback-message';
                        break;
                }
            }
            
            // 显示反馈区域 (Show feedback area)
            feedbackElement.style.display = 'block';
            
            // 自动隐藏成功和信息消息 (Auto-hide success and info messages)
            if (type === 'success' || type === 'info') {
                setTimeout(() => {
                    if (feedbackElement) {
                        feedbackElement.style.display = 'none';
                    }
                }, 3000);
            }
        }
        
        console.log(`Audio feedback [${type}]:`, message);
    }
    
    function updateAudioProgress(progress) {
        // 更新音频进度条 (Update audio progress bar)
        const progressBar = document.querySelector('.audio-progress-bar');
        
        if (progressBar && progress.duration > 0) {
            const percentage = Math.min(100, Math.max(0, progress.percentage));
            progressBar.style.width = `${percentage}%`;
            
            // 更新时间显示 (Update time display)
            const timeDisplay = document.getElementById('audio-time-display');
            if (timeDisplay) {
                const currentMinutes = Math.floor(progress.currentTime / 60);
                const currentSeconds = Math.floor(progress.currentTime % 60);
                const totalMinutes = Math.floor(progress.duration / 60);
                const totalSeconds = Math.floor(progress.duration % 60);
                
                timeDisplay.textContent = 
                    `${currentMinutes}:${currentSeconds.toString().padStart(2, '0')} / ` +
                    `${totalMinutes}:${totalSeconds.toString().padStart(2, '0')}`;
            }
        }
        
        console.log('Audio progress updated:', progress);
    }
    
    /**
     * 显示音频播放状态 (Show audio playback status)
     */
    function showAudioPlaybackStatus(status) {
        const statusMessages = {
            'preparing': 'Preparing audio...',
            'playing': 'Playing AI response...',
            'paused': 'Audio paused',
            'stopped': 'Audio stopped',
            'error': 'Audio playback failed',
            'completed': 'Audio playback completed'
        };
        
        const message = statusMessages[status] || 'Audio status unknown';
        const type = status === 'error' ? 'error' : 
                    status === 'completed' ? 'success' : 'info';
        
        // 显示状态在聊天界面 (Show status in chat interface)
        if (status === 'preparing' || status === 'playing') {
            showStatus(message);
        } else {
            hideStatus();
        }
        
        // 显示音频反馈 (Show audio feedback)
        showAudioFeedback(message, type);
        
        console.log('Audio playback status:', status, message);
    }
    
    // --- Audio Control Functions ---
    
    /**
     * 重播当前音频 (Replay current audio)
     */
    function replayCurrentAudio() {
        if (currentAIResponse && currentAIResponse.audio) {
            console.log('Replaying current AI response audio');
            showAudioPlaybackStatus('preparing');
            
            audioPlayer.playBase64Audio(currentAIResponse.audio, {
                autoPlay: true,
                playbackRate: 1.0,
                volume: audioPlayer.volume
            }).catch(error => {
                console.error('Replay failed:', error);
                showAudioPlaybackStatus('error');
            });
        } else {
            console.warn('No audio available to replay');
            showAudioFeedback('No audio available to replay', 'error');
        }
    }
    
    /**
     * 慢速播放当前音频 (Play current audio slowly)
     */
    function playSlowAudio() {
        if (currentAIResponse && currentAIResponse.audio) {
            console.log('Playing current AI response audio slowly');
            showAudioPlaybackStatus('preparing');
            
            audioPlayer.playBase64Audio(currentAIResponse.audio, {
                autoPlay: true,
                playbackRate: 0.7, // 70% speed for slow playback
                volume: audioPlayer.volume
            }).catch(error => {
                console.error('Slow playback failed:', error);
                showAudioPlaybackStatus('error');
            });
        } else {
            console.warn('No audio available for slow playback');
            showAudioFeedback('No audio available for slow playback', 'error');
        }
    }
    
    /**
     * 停止当前音频播放 (Stop current audio playback)
     */
    function stopCurrentAudio() {
        console.log('Stopping current audio playback');
        audioPlayer.stop();
        showAudioPlaybackStatus('stopped');
    }
    
    /**
     * 播放当前音频 (Play current audio)
     */
    function playCurrentAudio() {
        if (currentAIResponse && currentAIResponse.audio) {
            console.log('Playing current AI response audio');
            showAudioPlaybackStatus('preparing');
            
            audioPlayer.playBase64Audio(currentAIResponse.audio, {
                autoPlay: true,
                playbackRate: 1.0,
                volume: audioPlayer.volume
            }).catch(error => {
                console.error('Playback failed:', error);
                showAudioPlaybackStatus('error');
            });
        } else {
            console.warn('No audio available to play');
            showAudioFeedback('No audio available to play', 'error');
        }
    }
    
    /**
     * 暂停/恢复音频播放 (Pause/resume audio playback)
     */
    function toggleAudioPlayback() {
        const state = audioPlayer.getState();
        
        if (state.isPlaying) {
            audioPlayer.pause();
            console.log('Audio playback paused');
        } else if (state.isPaused) {
            audioPlayer.play().catch(error => {
                console.error('Resume playback failed:', error);
                showAudioPlaybackStatus('error');
            });
            console.log('Audio playback resumed');
        } else {
            // If not playing or paused, start playing current audio
            playCurrentAudio();
        }
    }
    
    /**
     * 设置音频播放速度 (Set audio playback speed)
     */
    function setAudioPlaybackRate(rate) {
        if (rate > 0 && rate <= 3) {
            audioPlayer.setPlaybackRate(rate);
            updateAudioPreference('defaultSpeed', rate);
            console.log('Audio playback rate set to:', rate);
            
            // 如果正在播放，重新开始以应用新速度 (If playing, restart to apply new speed)
            if (audioPlayer.getState().isPlaying && currentAIResponse) {
                audioPlayer.playBase64Audio(currentAIResponse.audio, {
                    autoPlay: true,
                    playbackRate: rate,
                    volume: audioPlayer.volume
                });
            }
        }
    }
    
    /**
     * 设置音频音量 (Set audio volume)
     */
    function setAudioVolume(volume) {
        if (volume >= 0 && volume <= 1) {
            audioPlayer.setVolume(volume);
            updateAudioPreference('defaultVolume', volume);
            console.log('Audio volume set to:', volume);
            showAudioFeedback(`Volume set to ${Math.round(volume * 100)}%`, 'info');
        }
    }
    
    /**
     * 创建音频控制面板 (Create audio control panel)
     */
    function createAudioControlPanel() {
        // 这个函数可以在未来扩展以创建更高级的控制面板
        // This function can be expanded in the future to create more advanced control panels
        const controlPanel = document.createElement('div');
        controlPanel.id = 'advanced-audio-controls';
        controlPanel.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(255, 255, 255, 0.95);
            border: 1px solid #e5e7eb;
            border-radius: 0.75rem;
            padding: 1rem;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
            backdrop-filter: blur(10px);
            z-index: 1000;
            display: none;
        `;
        
        controlPanel.innerHTML = `
            <div style="margin-bottom: 0.5rem; font-weight: 600; color: #374151;">
                Audio Controls
            </div>
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                <div>
                    <label style="font-size: 0.75rem; color: #6b7280;">Volume:</label>
                    <input type="range" id="volume-slider" min="0" max="100" value="100" 
                           style="width: 100%; margin-top: 0.25rem;">
                </div>
                <div>
                    <label style="font-size: 0.75rem; color: #6b7280;">Speed:</label>
                    <select id="speed-selector" style="width: 100%; margin-top: 0.25rem; padding: 0.25rem;">
                        <option value="0.5">0.5x (Very Slow)</option>
                        <option value="0.7">0.7x (Slow)</option>
                        <option value="1.0" selected>1.0x (Normal)</option>
                        <option value="1.25">1.25x (Fast)</option>
                        <option value="1.5">1.5x (Very Fast)</option>
                    </select>
                </div>
                <button onclick="document.getElementById('advanced-audio-controls').style.display='none'" 
                        style="margin-top: 0.5rem; padding: 0.25rem; background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 0.25rem; cursor: pointer;">
                    Close
                </button>
            </div>
        `;
        
        document.body.appendChild(controlPanel);
        
        // 添加事件监听器 (Add event listeners)
        const volumeSlider = document.getElementById('volume-slider');
        const speedSelector = document.getElementById('speed-selector');
        
        if (volumeSlider) {
            volumeSlider.addEventListener('input', (e) => {
                setAudioVolume(e.target.value / 100);
            });
        }
        
        if (speedSelector) {
            speedSelector.addEventListener('change', (e) => {
                setAudioPlaybackRate(parseFloat(e.target.value));
            });
        }
        
        return controlPanel;
    }
    
    // --- User Preferences Functions ---
    
    /**
     * 加载用户音频偏好设置 (Load user audio preferences)
     */
    function loadAudioPreferences() {
        try {
            const saved = localStorage.getItem('speak_practice_audio_preferences');
            if (saved) {
                const parsed = JSON.parse(saved);
                audioPreferences = { ...audioPreferences, ...parsed };
                
                // 应用加载的偏好设置 (Apply loaded preferences)
                audioPlayer.setVolume(audioPreferences.defaultVolume);
                audioPlayer.setPlaybackRate(audioPreferences.defaultSpeed);
                
                console.log('Audio preferences loaded:', audioPreferences);
            }
        } catch (error) {
            console.warn('Failed to load audio preferences:', error);
        }
    }
    
    /**
     * 保存用户音频偏好设置 (Save user audio preferences)
     */
    function saveAudioPreferences() {
        try {
            localStorage.setItem('speak_practice_audio_preferences', JSON.stringify(audioPreferences));
            console.log('Audio preferences saved:', audioPreferences);
        } catch (error) {
            console.warn('Failed to save audio preferences:', error);
        }
    }
    
    /**
     * 更新音频偏好设置 (Update audio preferences)
     */
    function updateAudioPreference(key, value) {
        if (audioPreferences.hasOwnProperty(key)) {
            audioPreferences[key] = value;
            saveAudioPreferences();
            
            // 立即应用某些设置 (Apply certain settings immediately)
            switch(key) {
                case 'defaultVolume':
                    audioPlayer.setVolume(value);
                    break;
                case 'defaultSpeed':
                    audioPlayer.setPlaybackRate(value);
                    break;
            }
            
            console.log(`Audio preference updated: ${key} = ${value}`);
        }
    }
    
    /**
     * 重置音频偏好设置为默认值 (Reset audio preferences to defaults)
     */
    function resetAudioPreferences() {
        audioPreferences = {
            autoPlay: true,
            defaultVolume: 1.0,
            defaultSpeed: 1.0,
            showControls: true,
            enableKeyboardShortcuts: true
        };
        
        saveAudioPreferences();
        loadAudioPreferences();
        
        console.log('Audio preferences reset to defaults');
        showAudioFeedback('Audio preferences reset to defaults', 'info');
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
        
        // 加载用户音频偏好设置 (Load user audio preferences)
        loadAudioPreferences();
        
        // 创建高级音频控制面板 (Create advanced audio control panel)
        createAudioControlPanel();
        
        // 添加音频控制面板切换按钮 (Add audio control panel toggle button)
        const audioControlToggle = document.createElement('button');
        audioControlToggle.id = 'audio-control-toggle';
        audioControlToggle.innerHTML = '<i class="fas fa-sliders-h"></i>';
        audioControlToggle.title = 'Advanced Audio Controls';
        audioControlToggle.style.cssText = `
            position: fixed;
            bottom: 80px;
            right: 20px;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: #3b82f6;
            color: white;
            border: none;
            cursor: pointer;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
            z-index: 999;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
        `;
        
        audioControlToggle.addEventListener('click', () => {
            const controlPanel = document.getElementById('advanced-audio-controls');
            if (controlPanel) {
                controlPanel.style.display = controlPanel.style.display === 'none' ? 'block' : 'none';
            }
        });
        
        audioControlToggle.addEventListener('mouseenter', () => {
            audioControlToggle.style.transform = 'scale(1.1)';
            audioControlToggle.style.background = '#2563eb';
        });
        
        audioControlToggle.addEventListener('mouseleave', () => {
            audioControlToggle.style.transform = 'scale(1)';
            audioControlToggle.style.background = '#3b82f6';
        });
        
        document.body.appendChild(audioControlToggle);
        
        console.log('Chat initialized successfully');
    }
    
    // 页面卸载时清理资源 (Cleanup resources when page unloads)
    window.addEventListener('beforeunload', () => {
        if (voiceRecorder) {
            voiceRecorder.destroy();
        }
        if (audioPlayer) {
            audioPlayer.destroy();
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
