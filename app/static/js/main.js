// 检查浏览器是否支持 ES2022 的 at 方法，如果不支持则添加 polyfill，添加兼容代码
if (!Array.prototype.at) {
    Array.prototype.at = function(index) {
        index = Math.trunc(index) || 0;
        if (index < 0) index += this.length;
        if (index < 0 || index >= this.length) return undefined;
        return this[index];
    };
}


document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('qa-form');
    const chatContainer = document.getElementById('chat-container');

    form.addEventListener('submit', handleFormSubmit);

    // 滑块事件监听
    document.getElementById('temperature').addEventListener('input', updateTempValue);
    document.getElementById('top_k').addEventListener('input', updateDocCount);
});

document.addEventListener('DOMContentLoaded', () => {
    // 检测浏览器是否支持 ES2022 的 at 方法
    if (!Array.prototype.at) {
        alert('检测到您的浏览器版本过旧，可能导致功能异常。请升级到 Chrome 80+ 或 Firefox 75+ 以获得最佳体验。');
    }
    // ... 其他初始化逻辑 ...
});

function handleFormSubmit(e) {
    e.preventDefault();
    // 表单处理逻辑...
}

function updateTempValue() {
    document.getElementById('temp-value').textContent = (this.value / 10).toFixed(1);
}

function updateDocCount() {
    document.getElementById('doc-count').textContent = this.value;
}

const form = document.getElementById('qa-form');
const chatContainer = document.getElementById('chat-container');

// 在文件顶部添加全局变量
let isSubmitting = false;

form.addEventListener('submit', async (e) => {
    if (isSubmitting) return;
    e.preventDefault();

    isSubmitting = true;  // 设置提交状态
    const submitBtn = document.getElementById('submit-btn');
    const submitText = document.getElementById('submit-text');
    submitBtn.disabled = true;
    submitText.textContent = '处理中...';

    const collectionType = document.querySelector('input[name="options"]:checked').value;

    const formData = new FormData(form);
    formData.append('collection_type', collectionType);
    const question = formData.get('question');

    // 清空输入框
    document.getElementById('question').value = '';

    displayMessage(question, 'user');

    const loadingId = 'loading-' + Date.now();
    createLoadingIndicator(loadingId);

    // 修改请求处理部分
    try {
        const response = await fetch('/chat/ask', {
            method: 'POST',
            body: formData
        });

        // 直接解析JSON数据
        const { answer, context } = await response.json();

        document.getElementById(loadingId).remove();
        displayMessage(answer, 'assistant', context.map(c => c.content)); // 直接使用context数组


    } catch (error) {
        console.error('Error:', error);
        document.getElementById(loadingId).remove();
        displayMessage('请求失败，请重试', 'error');
    } finally {
        // 无论成功失败都重新启用按钮
        isSubmitting = false;  // 重置提交状态
        submitBtn.disabled = false;
        submitText.textContent = '发送';
    }
});

// 修改回车键检测
document.getElementById('question').addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey && !isSubmitting) {
        e.preventDefault();
        const form = document.getElementById('qa-form');
        if (form) {
            form.dispatchEvent(new Event('submit'));
            const formData = new FormData(form);  // 确保从form元素创建
            const top_k = parseInt(formData.get('top_k'));
            document.getElementById('doc-count').textContent = top_k;
        }
    }
});



// 修改displayMessage函数
// 配置marked.js
marked.setOptions({
    breaks: true,
    gfm: true
});

function displayMessage(text, type, contexts = []) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';

    // 渲染Markdown
    const renderMarkdown = (content) => {
        return marked.parse(content);
    };

    if (type === 'user') {
        messageDiv.innerHTML = `
            <div class="question">
                <div>${renderMarkdown(text)}</div>
            </div>
        `;
    } else if (type === 'assistant') {
        messageDiv.innerHTML = `
            <div class="answer">
                <div class="answer-header">
                    <img src="/static/JARVIS.png" alt="JARVIS" class="avatar-icon">
                    <span>JARVIS</span>
                </div>
                <div class="answer-content">${renderMarkdown(text)}</div>
                ${contexts.length > 0 ? `
                <div class="context-badges">
                    ${contexts.map((ctx, i) => `
                        <div class="context-badge" data-index="${i}">
                            <img src="/static/icons/document-sm.png" alt="文档${i + 1}">
                            <span class="context-badge-text">参考 ${i + 1}</span>
                            <div class="context-tooltip">${renderMarkdown(ctx)}</div>
                        </div>
                    `).join('')}
                </div>
                ` : ''}
                <div class="feedback-buttons">
                    <button class="feedback-btn like-btn" data-feedback="1">
                        <img src="/static/icons/like.png" alt="赞"> 
                    </button>
                    <button class="feedback-btn dislike-btn" data-feedback="0">
                        <img src="/static/icons/dislike.png" alt="踩"> 
                    </button>
                </div>
            </div>
        `;
    }

    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function createLoadingIndicator(id) {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message';
    loadingDiv.id = id;
    loadingDiv.innerHTML = `
        <div class="answer">
            <div class="answer-header">
                <i class="mdi mdi-robot"></i>
                <span>JARVIS正在高速搜索知识库...</span>
            </div>
            <div class="progress-bar">
                <div class="progress"></div>
            </div>
        </div>
    `;

    chatContainer.appendChild(loadingDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    // 模拟进度条动画
    const progress = loadingDiv.querySelector('.progress');
    let width = 0;
    const interval = setInterval(() => {
        if (width >= 90) {
            clearInterval(interval);
        } else {
            width += 5;
            progress.style.width = width + '%';
        }
    }, 300);
}

// 更新滑块值显示
document.getElementById('temperature').addEventListener('input', function () {
    document.getElementById('temp-value').textContent = (this.value / 10).toFixed(1);
});

document.getElementById('top_k').addEventListener('input', function () {
    document.getElementById('doc-count').textContent = this.value;
});



// 添加反馈按钮点击处理
document.addEventListener('click', async (e) => {

    if (e.target.closest('.feedback-btn') && !e.target.closest('.feedback-btn.disabled')) {
        const container = e.target.closest('.feedback-buttons');
        const buttons = container.querySelectorAll('.feedback-btn');
        const clickedBtn = e.target.closest('.feedback-btn');
        const feedback = clickedBtn.dataset.feedback;  // 获取feedback值

        const questionElement = document.querySelector('.message:last-child .question > div');        const question = questionElement ? questionElement.textContent : '';

        // 禁用所有按钮
        buttons.forEach(btn => {
            btn.classList.add('disabled');
            btn.disabled = true;
        });

        // 高亮已点击的按钮
        clickedBtn.classList.add('active');

        try {
            await fetch('/chat/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({

                    timestamp: Date.now(),
                    feedback: feedback,
                    question: question.trim()

                })
            });
            clickedBtn.classList.add('active');
            //setTimeout(() => clickedBtn.classList.remove('active'), 1000);
        } catch (error) {
            console.error('反馈提交失败:', error);
        }
    }
});

function adjustOptionLayout() {
    const container = document.querySelector('.option-container');
    const options = container.querySelectorAll('.option-radio');
    const count = options.length;
    let flexBasis = '33.33%'; // 默认一行三个

    if (count === 4) {
        flexBasis = '50%'; // 四个选项时两行两列
    } else if (count <= 3) {
        flexBasis = `${100 / count}%`; // 少于等于三个时紧凑排列
    }

    options.forEach(option => {
        option.style.flexBasis = flexBasis;
    });
}

// 修改反馈提交逻辑
async function handleFeedback(interactionId, feedbackType) {
    try {
        await fetch('/chat/feedback', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                interaction_id: interactionId,
                feedback: feedbackType
            })
        });
    } catch (error) {
        console.error('反馈提交失败:', error);
    }
}

// 每5分钟更新统计信息
async function updateStats() {
    try {
        const response = await fetch('/chat/stats');
        const stats = await response.json();

        // 原代码：使用 todayElement → 改为通过类选择器获取
        const todayCount = document.querySelector('.stats-item:nth-child(1) .stats-value');
        const totalCount = document.querySelector('.stats-item:nth-child(2) .stats-value');
        
        if (todayCount) todayCount.textContent = stats.today_count || 0;
        if (totalCount) totalCount.textContent = stats.total_count || 0;

        const likeBtn = document.querySelector('.like-btn');
        const dislikeBtn = document.querySelector('.dislike-btn');
        
        if (todayCount) todayCount.textContent = stats.today_count;
        if (totalCount) totalCount.textContent = stats.total_count;
        if (likeBtn) likeBtn.textContent = stats.like_count;
        if (dislikeBtn) dislikeBtn.textContent = stats.dislike_count;    } catch (error) {
        console.error('统计信息更新失败:', error);
    }
}

// 初始化统计更新
setInterval(updateStats, 300000);
updateStats();


// 在DOM加载完成后调用
document.addEventListener('DOMContentLoaded', () => {
    loadVersionInfo();
});