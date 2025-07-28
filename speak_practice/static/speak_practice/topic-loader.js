/**
 * TopicLoader - 异步话题加载管理器
 * 处理AI生成话题的异步加载、重试机制、错误处理和UI状态管理
 */
class TopicLoader {
    constructor(options = {}) {
        // API配置
        this.apiUrl = options.apiUrl || '/speak/api/topics/';
        this.csrfToken = options.csrfToken || this.getCSRFToken();
        
        // 重试配置
        this.retryCount = 0;
        this.maxRetries = options.maxRetries || 3;
        this.retryDelay = options.retryDelay || 1000;
        this.retryMultiplier = options.retryMultiplier || 2;
        
        // 超时配置
        this.timeout = options.timeout || 30000; // 30秒超时
        
        // 状态回调函数
        this.onLoadingStart = options.onLoadingStart || null;
        this.onLoadingSuccess = options.onLoadingSuccess || null;
        this.onLoadingError = options.onLoadingError || null;
        
        // DOM元素引用
        this.topicsGrid = document.getElementById('topics-grid');
        this.topicsContainer = document.getElementById('topics-container');
        this.skeletonState = document.getElementById('skeleton-state');
        this.loadingIndicator = document.getElementById('loading-indicator');
        this.errorState = document.getElementById('error-state');
        
        // 网络状态检测
        this.isOnline = navigator.onLine;
        this.setupNetworkListeners();
        
        // 绑定方法上下文
        this.loadTopics = this.loadTopics.bind(this);
        this.retryLoad = this.retryLoad.bind(this);
        
        console.log('TopicLoader 初始化完成');
    }
    
    /**
     * 获取CSRF令牌
     */
    getCSRFToken() {
        // 首先尝试从表单中获取
        const tokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
        if (tokenElement && tokenElement.value) {
            return tokenElement.value;
        }
        
        // 尝试从meta标签获取
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken && metaToken.content) {
            return metaToken.content;
        }
        
        // 尝试从cookie获取
        const cookieValue = this.getCookieValue('csrftoken');
        if (cookieValue) {
            return cookieValue;
        }
        
        console.warn('无法获取CSRF令牌');
        return '';
    }
    
    /**
     * 从cookie中获取值
     */
    getCookieValue(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    /**
     * 更新CSRF令牌
     */
    updateCSRFToken(newToken) {
        if (newToken) {
            this.csrfToken = newToken;
            
            // 更新页面中的CSRF令牌
            const tokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
            if (tokenElement) {
                tokenElement.value = newToken;
            }
            
            console.log('CSRF令牌已更新');
        }
    }
    
    /**
     * 设置网络状态监听器
     */
    setupNetworkListeners() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            console.log('网络连接已恢复');
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            console.log('网络连接已断开');
        });
    }
    
    /**
     * 主要的话题加载方法 - 增强版本包含完整的降级策略
     */
    async loadTopics() {
        console.log('开始加载话题...');
        
        // 重置重试计数
        this.retryCount = 0;
        
        // 调用加载开始回调
        if (this.onLoadingStart) {
            this.onLoadingStart();
        }
        
        try {
            // 尝试从API获取话题
            const topics = await this.fetchTopicsWithRetry();
            this.renderTopics(topics);
            
            // 调用加载成功回调
            if (this.onLoadingSuccess) {
                this.onLoadingSuccess();
            }
            
            console.log('话题加载成功');
            return topics;
            
        } catch (error) {
            console.error('API话题加载失败，尝试本地降级:', error);
            
            try {
                // 尝试使用本地备用话题
                const fallbackTopics = await this.useLocalFallback();
                console.log('本地备用话题加载成功');
                return fallbackTopics;
                
            } catch (fallbackError) {
                console.error('所有降级策略都失败了:', fallbackError);
                
                // 处理完全失败的情况
                this.handleCompleteFailure(error, fallbackError);
                throw new Error('Complete failure: Unable to load any topics');
            }
        }
    }
    
    /**
     * 处理完全失败的情况
     */
    handleCompleteFailure(originalError, fallbackError) {
        console.error('完全失败 - 原始错误:', originalError);
        console.error('完全失败 - 降级错误:', fallbackError);
        
        // 调用错误回调
        if (this.onLoadingError) {
            this.onLoadingError(originalError, 'complete-failure');
        }
        
        // 显示完全失败的错误信息
        this.updateErrorMessage('Complete system failure', 'complete-failure');
        
        // 记录严重错误事件
        this.logErrorEvent('complete-failure', `Original: ${originalError.message}, Fallback: ${fallbackError.message}`);
        
        // 显示紧急通知
        this.showEmergencyNotification();
    }
    
    /**
     * 显示紧急通知
     */
    showEmergencyNotification() {
        const notification = document.createElement('div');
        notification.className = 'emergency-notification';
        notification.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #fef2f2;
            border: 2px solid #ef4444;
            color: #dc2626;
            padding: 20px;
            border-radius: 12px;
            font-size: 16px;
            max-width: 400px;
            z-index: 2000;
            box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
            text-align: center;
        `;
        notification.innerHTML = `
            <div style="margin-bottom: 16px;">
                <i class="fas fa-exclamation-circle" style="font-size: 24px; color: #ef4444; margin-bottom: 8px;"></i>
                <h3 style="margin: 0; font-size: 18px; font-weight: 700;">System Error</h3>
            </div>
            <p style="margin: 0 0 16px 0; line-height: 1.5;">
                We're experiencing technical difficulties. Please refresh the page or use the custom scenario option to continue practicing.
            </p>
            <div style="display: flex; gap: 12px; justify-content: center;">
                <button onclick="window.location.reload()" style="background: #ef4444; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 600;">
                    Refresh Page
                </button>
                <button onclick="this.parentElement.parentElement.parentElement.remove()" style="background: #6b7280; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 600;">
                    Close
                </button>
            </div>
        `;
        
        document.body.appendChild(notification);
    }
    
    /**
     * 带重试机制的话题获取 - 增强版本包含智能重试策略
     */
    async fetchTopicsWithRetry() {
        let lastError = null;
        
        while (this.retryCount <= this.maxRetries) {
            try {
                // 检查网络状态
                if (!this.isOnline) {
                    throw new Error('网络连接不可用');
                }
                
                const response = await this.fetchWithTimeout();
                const data = await response.json();
                
                // 处理成功响应
                if (data.success && data.topics) {
                    // 更新CSRF令牌（如果服务器提供了新的）
                    if (data.csrf_token) {
                        this.updateCSRFToken(data.csrf_token);
                    }
                    
                    // 验证话题数据
                    const validatedTopics = this.validateTopicsData(data.topics);
                    if (validatedTopics.length === 0) {
                        throw new Error('No valid topics received from server');
                    }
                    
                    // 如果是降级响应，记录但仍然返回话题
                    if (data.source === 'fallback') {
                        console.warn(`使用备用话题 (原因: ${data.fallback_reason}):`, data.message);
                        this.showFallbackNotification(data.message);
                    } else {
                        console.log('成功获取AI生成的话题');
                    }
                    return validatedTopics;
                }
                
                // 处理失败响应但有备用话题的情况
                if (data.fallback_topics) {
                    console.warn('API返回错误，使用备用话题:', data.error);
                    this.showFallbackNotification('Using backup topics due to AI service issues');
                    return data.fallback_topics;
                }
                
                // 如果没有话题数据，抛出错误
                throw new Error(data.error || 'API响应格式错误');
                
            } catch (error) {
                lastError = error;
                this.retryCount++;
                
                // 如果达到最大重试次数，抛出最后的错误
                if (this.retryCount > this.maxRetries) {
                    console.error(`所有重试尝试失败 (${this.maxRetries}次)，最后错误:`, error.message);
                    throw error;
                }
                
                // 判断是否应该重试
                if (!this.shouldRetry(error)) {
                    console.warn('错误类型不适合重试:', error.message);
                    throw error;
                }
                
                console.warn(`第${this.retryCount}次重试失败:`, error.message);
                
                // 计算指数退避延迟，包含抖动
                const baseDelay = this.retryDelay * Math.pow(this.retryMultiplier, this.retryCount - 1);
                const jitter = Math.random() * 0.3 * baseDelay; // 30%的随机抖动
                const delay = Math.min(baseDelay + jitter, 30000); // 最大延迟30秒
                
                console.log(`等待 ${Math.round(delay)}ms 后进行第${this.retryCount + 1}次重试...`);
                
                // 更新加载状态显示重试信息
                this.updateLoadingState(`Retrying... (${this.retryCount}/${this.maxRetries})`);
                
                // 等待指数退避延迟
                await this.sleep(delay);
            }
        }
        
        // 这行代码理论上不会执行到，但为了类型安全
        throw lastError || new Error('未知的重试错误');
    }
    
    /**
     * 判断错误是否应该重试
     */
    shouldRetry(error) {
        const errorMessage = error.message.toLowerCase();
        
        // 不应该重试的错误类型
        const nonRetryableErrors = [
            'http 401',  // 认证错误
            'http 403',  // 权限错误
            'http 404',  // 资源不存在
            'http 400',  // 请求格式错误
            'invalid json', // JSON格式错误
            'csrf'       // CSRF错误
        ];
        
        // 检查是否为不可重试的错误
        for (const nonRetryable of nonRetryableErrors) {
            if (errorMessage.includes(nonRetryable)) {
                return false;
            }
        }
        
        // 应该重试的错误类型
        const retryableErrors = [
            'timeout',     // 超时
            'http 5',      // 服务器错误 (5xx)
            'http 429',    // 速率限制
            'network',     // 网络错误
            'connection',  // 连接错误
            'fetch'        // Fetch API错误
        ];
        
        // 检查是否为可重试的错误
        for (const retryable of retryableErrors) {
            if (errorMessage.includes(retryable)) {
                return true;
            }
        }
        
        // 默认情况下，未知错误可以重试
        return true;
    }
    
    /**
     * 显示降级通知
     */
    showFallbackNotification(message) {
        // 创建一个临时通知显示降级信息
        const notification = document.createElement('div');
        notification.className = 'fallback-notification';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #fef3c7;
            border: 1px solid #f59e0b;
            color: #92400e;
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 14px;
            max-width: 300px;
            z-index: 1000;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        `;
        notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <i class="fas fa-exclamation-triangle" style="color: #f59e0b;"></i>
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #92400e; cursor: pointer; font-size: 16px; padding: 0; margin-left: auto;">×</button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // 5秒后自动移除通知
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }
    
    /**
     * 带超时的fetch请求
     */
    async fetchWithTimeout() {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);
        
        try {
            // 确保有有效的CSRF令牌
            if (!this.csrfToken) {
                this.csrfToken = this.getCSRFToken();
            }
            
            const response = await fetch(this.apiUrl, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'  // 标识为Ajax请求
                },
                credentials: 'same-origin',  // 包含同源cookie
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            
            if (error.name === 'AbortError') {
                throw new Error('请求超时');
            }
            
            throw error;
        }
    }
    
    /**
     * 更新加载状态文本
     */
    updateLoadingState(message) {
        if (this.loadingIndicator) {
            const loadingText = this.loadingIndicator.querySelector('.loading-text');
            if (loadingText) {
                loadingText.innerHTML = `${message}<span class="loading-dots"></span>`;
            }
        }
    }
    
    /**
     * 处理加载错误 - 增强版本包含错误分类和用户友好信息
     */
    handleLoadError(error) {
        console.error('处理加载错误:', error);
        
        // 分析错误类型
        let errorType = 'general-error';
        if (error.message.includes('timeout') || error.message.includes('超时')) {
            errorType = 'timeout-error';
        } else if (error.message.includes('网络连接不可用')) {
            errorType = 'offline-error';
        } else if (error.message.includes('HTTP 5')) {
            errorType = 'server-error';
        } else if (error.message.includes('HTTP 429')) {
            errorType = 'rate-limit-error';
        } else if (error.message.includes('HTTP 401')) {
            errorType = 'auth-error';
        }
        
        // 调用错误回调
        if (this.onLoadingError) {
            this.onLoadingError(error, errorType);
        }
        
        // 更新错误信息
        this.updateErrorMessage(error.message, errorType);
        
        // 记录错误统计（如果需要）
        this.logErrorEvent(errorType, error.message);
    }
    
    /**
     * 记录错误事件用于监控和分析
     */
    logErrorEvent(errorType, errorMessage) {
        try {
            // 可以发送到分析服务或本地存储
            const errorEvent = {
                type: errorType,
                message: errorMessage,
                timestamp: new Date().toISOString(),
                userAgent: navigator.userAgent,
                url: window.location.href
            };
            
            // 存储到本地存储用于调试
            const errorLog = JSON.parse(localStorage.getItem('topicLoader_errors') || '[]');
            errorLog.push(errorEvent);
            
            // 只保留最近的50个错误记录
            if (errorLog.length > 50) {
                errorLog.splice(0, errorLog.length - 50);
            }
            
            localStorage.setItem('topicLoader_errors', JSON.stringify(errorLog));
            
            console.log('错误事件已记录:', errorEvent);
        } catch (logError) {
            console.warn('无法记录错误事件:', logError);
        }
    }
    
    /**
     * 更新错误信息 - 增强版本提供更详细的用户友好信息
     */
    updateErrorMessage(errorMessage, errorType = null) {
        if (this.errorState) {
            const errorContent = this.errorState.querySelector('.error-message');
            const errorTitle = this.errorState.querySelector('.error-title');
            const errorSuggestion = this.errorState.querySelector('.error-suggestion');
            
            if (errorContent) {
                let userFriendlyMessage = '';
                let title = 'Connection Issue';
                let suggestion = 'Please try again or use the custom scenario option above to continue practicing.';
                
                // 根据错误类型提供具体的用户友好信息
                if (errorMessage.includes('网络') || errorMessage.includes('timeout') || errorMessage.includes('超时') || errorMessage.includes('请求超时')) {
                    title = 'Connection Timeout';
                    userFriendlyMessage = 'The connection to our AI service timed out. This might be due to a slow internet connection or high server load.';
                    suggestion = 'Please check your internet connection and try again. If the problem persists, you can use the custom scenario option above.';
                } else if (errorMessage.includes('网络连接不可用')) {
                    title = 'No Internet Connection';
                    userFriendlyMessage = 'Your device appears to be offline. Please check your internet connection.';
                    suggestion = 'Connect to the internet and try again. You can also use the custom scenario option which works offline.';
                } else if (errorMessage.includes('HTTP 5') || errorMessage.includes('服务器错误')) {
                    title = 'Service Temporarily Unavailable';
                    userFriendlyMessage = 'Our AI service is temporarily experiencing issues. This is usually resolved quickly.';
                    suggestion = 'Please try again in a few moments. If the issue continues, you can use the custom scenario option to continue practicing.';
                } else if (errorMessage.includes('HTTP 429') || errorMessage.includes('rate limit')) {
                    title = 'Service Busy';
                    userFriendlyMessage = 'Our AI service is currently experiencing high demand. Please wait a moment before trying again.';
                    suggestion = 'Try again in a few seconds, or use the custom scenario option to continue practicing immediately.';
                } else if (errorMessage.includes('HTTP 401') || errorMessage.includes('认证')) {
                    title = 'Authentication Issue';
                    userFriendlyMessage = 'There was an authentication problem. You may need to log in again.';
                    suggestion = 'Please refresh the page and log in again. If the problem persists, contact support.';
                } else if (errorMessage.includes('parse') || errorMessage.includes('JSON') || errorMessage.includes('格式错误')) {
                    title = 'Data Processing Issue';
                    userFriendlyMessage = 'There was a problem processing the AI response. This is usually temporary.';
                    suggestion = 'Please try again. If the issue continues, use the custom scenario option to continue practicing.';
                } else {
                    title = 'Service Issue';
                    userFriendlyMessage = 'We\'re having trouble connecting to our AI service. This could be due to network issues or temporary service problems.';
                    suggestion = 'Please try again in a moment. You can also use the custom scenario option above to continue practicing.';
                }
                
                // 更新DOM元素
                if (errorTitle) {
                    errorTitle.textContent = title;
                }
                errorContent.textContent = userFriendlyMessage;
                if (errorSuggestion) {
                    errorSuggestion.textContent = suggestion;
                }
                
                // 添加错误类型的CSS类用于样式定制
                this.errorState.className = `error-state ${errorType || 'general-error'}`;
            }
        }
    }
    
    /**
     * 重试加载话题
     */
    async retryLoad() {
        console.log('用户手动重试加载话题');
        await this.loadTopics();
    }
    
    /**
     * 渲染话题卡片
     */
    renderTopics(topics) {
        if (!this.topicsContainer || !Array.isArray(topics)) {
            console.error('无法渲染话题: DOM元素不存在或话题数据无效');
            return;
        }
        
        // 清除现有的话题卡片
        this.clearExistingTopics();
        
        // 设置容器为网格布局
        this.topicsContainer.style.display = 'grid';
        this.topicsContainer.style.gridTemplateColumns = 'repeat(auto-fit, minmax(320px, 1fr))';
        this.topicsContainer.style.gap = 'var(--space-xl)';
        
        // 渲染新的话题卡片
        topics.forEach((topic, index) => {
            const card = this.createTopicCard(topic, index);
            this.topicsContainer.appendChild(card);
        });
        
        console.log(`成功渲染${topics.length}个话题卡片`);
    }
    
    /**
     * 创建单个话题卡片
     */
    createTopicCard(topic, index) {
        const card = document.createElement('button');
        card.type = 'submit';
        card.name = 'scene';
        card.value = `${topic.title}: ${topic.description}`;
        card.className = 'scene-card';
        
        // 设置卡片内容
        card.innerHTML = `
            <div style="display: flex; align-items: flex-start; gap: 1.5rem; margin-bottom: 1.5rem;">
                <div class="topic-icon-container" style="width: 60px; height: 60px; background: linear-gradient(135deg, #fff7ed, #fed7aa); border-radius: 1rem; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: all 0.3s ease;">
                    <i class="${topic.icon}" style="font-size: 1.5rem; color: #FE4D01; transition: all 0.3s ease;"></i>
                </div>
                <div style="flex: 1; text-align: left;">
                    <h3 style="margin: 0 0 0.75rem 0; font-size: 1.25rem; font-weight: 700; color: #111827; line-height: 1.3;">
                        ${this.escapeHtml(topic.title)}
                    </h3>
                    <p style="margin: 0; color: #6b7280; font-size: 0.95rem; line-height: 1.5;">
                        ${this.escapeHtml(topic.description)}
                    </p>
                </div>
            </div>
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <span class="topic-level-badge" style="background: linear-gradient(135deg, #dbeafe, #bfdbfe); color: #1e40af; padding: 0.375rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">
                    ${this.escapeHtml(topic.level)}
                </span>
                <i class="fas fa-arrow-right topic-arrow" style="color: #9ca3af; font-size: 1rem; transition: all 0.3s ease;"></i>
            </div>
        `;
        
        // 添加交互事件
        this.addCardInteractions(card);
        
        // 添加入场动画
        this.addCardAnimation(card, index);
        
        return card;
    }
    
    /**
     * 添加卡片交互效果
     */
    addCardInteractions(card) {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-8px)';
            card.style.boxShadow = '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)';
            card.style.borderColor = '#fed7aa';
            
            // 图标容器动画
            const iconContainer = card.querySelector('.topic-icon-container');
            const icon = card.querySelector('.topic-icon-container i');
            if (iconContainer && icon) {
                iconContainer.style.background = 'linear-gradient(135deg, #FE4D01, #ea580c)';
                iconContainer.style.transform = 'scale(1.1)';
                icon.style.color = '#ffffff';
            }
            
            // 箭头动画
            const arrow = card.querySelector('.topic-arrow');
            if (arrow) {
                arrow.style.color = '#FE4D01';
                arrow.style.transform = 'translateX(4px)';
            }
        });
        
        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0)';
            card.style.boxShadow = '0 1px 2px 0 rgb(0 0 0 / 0.05)';
            card.style.borderColor = '#e5e7eb';
            
            // 重置图标容器
            const iconContainer = card.querySelector('.topic-icon-container');
            const icon = card.querySelector('.topic-icon-container i');
            if (iconContainer && icon) {
                iconContainer.style.background = 'linear-gradient(135deg, #fff7ed, #fed7aa)';
                iconContainer.style.transform = 'scale(1)';
                icon.style.color = '#FE4D01';
            }
            
            // 重置箭头
            const arrow = card.querySelector('.topic-arrow');
            if (arrow) {
                arrow.style.color = '#9ca3af';
                arrow.style.transform = 'translateX(0)';
            }
        });
    }
    
    /**
     * 添加卡片入场动画
     */
    addCardAnimation(card, index) {
        // 初始状态
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        // 延迟显示动画
        setTimeout(() => {
            card.style.transition = 'all 0.3s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    }
    
    /**
     * 清除现有的话题卡片
     */
    clearExistingTopics() {
        if (this.topicsContainer) {
            const existingCards = this.topicsContainer.querySelectorAll('.scene-card');
            existingCards.forEach(card => card.remove());
        }
    }
    
    /**
     * 获取静态备用话题 - 与后端保持一致的紧急备用话题
     */
    getFallbackTopics() {
        // 紧急情况下的最小话题集，与后端emergency_topics保持一致
        return [
            {
                title: "Café Chat",
                description: "Ordering coffee and pastries at a local café",
                level: "Beginner",
                icon: "fas fa-coffee"
            },
            {
                title: "Finding Places",
                description: "Asking for directions to popular tourist attractions",
                level: "Beginner",
                icon: "fas fa-map-marked-alt"
            },
            {
                title: "Weather Talk",
                description: "Discussing today's weather and weekend plans",
                level: "Beginner",
                icon: "fas fa-cloud-sun"
            },
            {
                title: "Work Intro",
                description: "Introducing yourself and background to new colleagues",
                level: "Intermediate",
                icon: "fas fa-handshake"
            },
            {
                title: "Food Ordering",
                description: "Ordering traditional Chinese dishes at a restaurant",
                level: "Intermediate",
                icon: "fas fa-utensils"
            },
            {
                title: "Emergency Help",
                description: "Asking for help in an emergency situation",
                level: "Advanced",
                icon: "fas fa-exclamation-triangle"
            }
        ];
    }
    
    /**
     * 使用本地备用话题作为最后的降级选项
     */
    async useLocalFallback() {
        console.warn('使用本地备用话题作为最后的降级选项');
        
        try {
            const fallbackTopics = this.getFallbackTopics();
            this.renderTopics(fallbackTopics);
            
            // 显示降级通知
            this.showFallbackNotification('Using offline backup topics due to connection issues');
            
            // 调用成功回调（虽然是降级，但对用户来说仍然是成功的）
            if (this.onLoadingSuccess) {
                this.onLoadingSuccess();
            }
            
            return fallbackTopics;
        } catch (error) {
            console.error('连本地备用话题都失败了:', error);
            throw new Error('Complete system failure - unable to load any topics');
        }
    }
    
    /**
     * 验证话题数据结构和内容
     */
    validateTopicsData(topics) {
        if (!Array.isArray(topics)) {
            console.error('话题数据不是数组格式');
            return [];
        }
        
        const validatedTopics = [];
        
        for (const topic of topics) {
            if (!this.isValidTopic(topic)) {
                console.warn('跳过无效话题:', topic);
                continue;
            }
            
            // 清理话题数据
            const cleanTopic = {
                title: this.sanitizeText(topic.title, 100),
                description: this.sanitizeText(topic.description, 500),
                level: this.sanitizeText(topic.level, 50),
                icon: this.sanitizeIconClass(topic.icon)
            };
            
            validatedTopics.push(cleanTopic);
        }
        
        return validatedTopics;
    }
    
    /**
     * 验证单个话题是否有效
     */
    isValidTopic(topic) {
        if (!topic || typeof topic !== 'object') {
            return false;
        }
        
        const requiredFields = ['title', 'description', 'level', 'icon'];
        for (const field of requiredFields) {
            if (!topic[field] || typeof topic[field] !== 'string' || topic[field].trim() === '') {
                return false;
            }
        }
        
        return true;
    }
    
    /**
     * 清理文本内容，防止XSS攻击
     */
    sanitizeText(text, maxLength = 1000) {
        if (!text || typeof text !== 'string') {
            return '';
        }
        
        // 限制长度
        text = text.substring(0, maxLength);
        
        // HTML转义
        text = this.escapeHtml(text);
        
        // 移除潜在的恶意内容
        text = text.replace(/<script[^>]*>.*?<\/script>/gi, '');
        text = text.replace(/javascript:/gi, '');
        text = text.replace(/on\w+\s*=/gi, '');
        
        // 清理多余空白
        text = text.replace(/\s+/g, ' ').trim();
        
        return text;
    }
    
    /**
     * 验证和清理图标类名
     */
    sanitizeIconClass(iconClass) {
        if (!iconClass || typeof iconClass !== 'string') {
            return 'fas fa-comment';
        }
        
        // 只允许Font Awesome图标格式
        const iconPattern = /^fas fa-[a-z0-9-]+$/;
        if (iconPattern.test(iconClass)) {
            return iconClass;
        }
        
        return 'fas fa-comment'; // 默认图标
    }
    
    /**
     * HTML转义函数，防止XSS攻击
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * 睡眠函数，用于重试延迟
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    /**
     * 销毁实例，清理事件监听器
     */
    destroy() {
        // 移除网络状态监听器
        window.removeEventListener('online', this.handleOnline);
        window.removeEventListener('offline', this.handleOffline);
        
        console.log('TopicLoader 实例已销毁');
    }
}

// 全局实例和便捷函数
let topicLoaderInstance = null;

/**
 * 初始化话题加载器
 */
function initializeTopicLoader(options = {}) {
    if (topicLoaderInstance) {
        topicLoaderInstance.destroy();
    }
    
    topicLoaderInstance = new TopicLoader(options);
    return topicLoaderInstance;
}

/**
 * 加载话题的全局函数
 */
function loadTopics() {
    if (topicLoaderInstance) {
        return topicLoaderInstance.loadTopics();
    } else {
        console.error('TopicLoader 未初始化');
    }
}

/**
 * 刷新话题的全局函数
 */
function refreshTopics() {
    if (topicLoaderInstance) {
        return topicLoaderInstance.loadTopics();
    } else {
        console.error('TopicLoader 未初始化');
    }
}

// 导出类和函数（如果使用模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { TopicLoader, initializeTopicLoader, loadTopics, refreshTopics };
}