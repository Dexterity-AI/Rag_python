// Global state
let systemReady = false;
let eventSource = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
            e.currentTarget.classList.add('active');
            
            const targetId = e.currentTarget.getAttribute('data-target');
            document.querySelectorAll('.panel').forEach(panel => panel.classList.remove('active'));
            document.getElementById(targetId).classList.add('active');
            
            // Trigger panel specific actions
            if (targetId === 'panel-system') loadSystemHealth();
            if (targetId === 'panel-data') loadFiles();
            if (targetId === 'panel-cache') loadCacheStats();
            if (targetId === 'panel-config') loadConfig();
        });
    });

    // Chat
    const chatInput = document.getElementById('chat-input');
    const btnSend = document.getElementById('btn-send');
    const btnStop = document.getElementById('btn-stop');
    const btnClear = document.getElementById('btn-clear-chat');
    
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    btnSend.addEventListener('click', sendMessage);
    btnStop.addEventListener('click', stopChat);
    btnClear.addEventListener('click', () => {
        document.getElementById('chat-container').innerHTML = `
            <div class="message assistant">
                <div class="message-content">你好！我是 GraphRAG 智能旅游助手。系统准备就绪后，你可以问我任何旅游相关的问题。</div>
            </div>`;
    });

    // System Status Polling
    setInterval(checkStatus, 2000);
    checkStatus();

    // Panel System
    document.getElementById('btn-refresh-system').addEventListener('click', loadSystemHealth);

    // Collect Data
    document.getElementById('form-collect').addEventListener('submit', (e) => {
        e.preventDefault();
        startCollect();
    });

    // Data Files
    document.getElementById('btn-load-files').addEventListener('click', loadFiles);

    // Cache
    document.getElementById('btn-clear-all-cache').addEventListener('click', () => {
        if (confirm('确定要清空所有缓存吗？')) clearCache(true, true, true, true);
    });

    // Initialize Particles
    initParticles();
});

// --- System Status ---
async function checkStatus() {
    try {
        const res = await fetch('/api/system/status');
        const data = await res.json();
        
        systemReady = data.ready;
        const dot = document.getElementById('sys-dot');
        const text = document.getElementById('sys-status-text');
        const warning = document.getElementById('global-warning');
        
        if (systemReady) {
            dot.classList.add('ready');
            text.innerText = '系统就绪';
            warning.classList.add('hidden');
            document.getElementById('btn-send').disabled = false;
        } else {
            dot.classList.remove('ready');
            text.innerText = '系统未就绪';
            warning.classList.remove('hidden');
            document.getElementById('init-progress-text').innerText = data.init_progress || '初始化中...';
            document.getElementById('btn-send').disabled = true;
        }
        
        document.getElementById('sys-model').innerText = data.model || '未配置';
        
    } catch (e) {
        console.error('Failed to get status', e);
    }
}

// --- Chat ---
function appendMessage(role, content) {
    const container = document.getElementById('chat-container');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    if (role === 'assistant') {
        contentDiv.innerHTML = marked.parse(content);
    } else {
        contentDiv.innerText = content;
    }
    
    msgDiv.appendChild(contentDiv);
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
    
    // syntax highlighting
    contentDiv.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
    });
    
    return contentDiv;
}

async function sendMessage() {
    if (!systemReady) {
        alert('系统未就绪，请等待初始化完成。');
        return;
    }

    const input = document.getElementById('chat-input');
    const question = input.value.trim();
    if (!question) return;

    input.value = '';
    appendMessage('user', question);
    
    const container = document.getElementById('chat-container');
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message assistant';
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content typing-indicator';
    msgDiv.appendChild(contentDiv);
    container.appendChild(msgDiv);
    
    document.getElementById('btn-send').classList.add('hidden');
    document.getElementById('btn-stop').classList.remove('hidden');
    
    let currentText = '';

    try {
        const response = await fetch('/api/chat/stream', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ question: question, stream: true })
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        
        // This is a naive chunk processor. In production, use a proper SSE parser.
        while (true) {
            const {done, value} = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value, {stream: true});
            const lines = chunk.split('\n');
            for (let line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.substring(6));
                        if (data.type === 'chunk') {
                            currentText += data.content;
                            contentDiv.innerHTML = marked.parse(currentText);
                            container.scrollTop = container.scrollHeight;
                        } else if (data.type === 'error') {
                            contentDiv.innerHTML += `<br><span style="color:var(--error)">错误: ${data.content}</span>`;
                        } else if (data.type === 'done') {
                            // done
                        }
                    } catch (e) {}
                }
            }
        }
    } catch (e) {
        contentDiv.innerText = "网络请求失败: " + e.message;
    } finally {
        contentDiv.classList.remove('typing-indicator');
        contentDiv.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });
        document.getElementById('btn-send').classList.remove('hidden');
        document.getElementById('btn-stop').classList.add('hidden');
    }
}

function stopChat() {
    // Implement abort controller if needed
    document.getElementById('btn-send').classList.remove('hidden');
    document.getElementById('btn-stop').classList.add('hidden');
    const msgs = document.querySelectorAll('.typing-indicator');
    msgs.forEach(m => m.classList.remove('typing-indicator'));
}

// --- System ---
async function loadSystemHealth() {
    try {
        // Status fetch
        const sRes = await fetch('/api/system/status');
        const statusData = await sRes.json();
        
        // Health fetch
        const hRes = await fetch('/api/system/health');
        const healthData = await hRes.json();
        
        // Render Health Cards
        const healthContainer = document.getElementById('health-cards');
        healthContainer.innerHTML = '';
        healthData.checks.forEach(check => {
            healthContainer.innerHTML += `
                <div class="card">
                    <div class="flex items-center justify-between mb-2">
                        <h3 class="card-title m-0">${check.name}</h3>
                        <span class="text-xl">${check.status ? '✅' : '❌'}</span>
                    </div>
                    <div class="text-sm ${check.status ? 'text-success' : 'text-error'}">
                        ${check.message}
                    </div>
                </div>
            `;
        });
        
        // Render KB Stats
        const kb = statusData.knowledge_base || {};
        const kbContainer = document.getElementById('kb-cards');
        kbContainer.innerHTML = `
            <div class="card"><h3 class="card-title">城市/地区</h3><p class="card-value">${kb.total_cities || 0}</p></div>
            <div class="card"><h3 class="card-title">景点数量</h3><p class="card-value">${kb.total_attractions || 0}</p></div>
            <div class="card"><h3 class="card-title">美食数量</h3><p class="card-value">${kb.total_foods || 0}</p></div>
            <div class="card"><h3 class="card-title">文档数量</h3><p class="card-value">${kb.total_documents || 0}</p></div>
            <div class="card"><h3 class="card-title">文本块数</h3><p class="card-value">${kb.total_chunks || 0}</p></div>
        `;
        
    } catch (e) {
        console.error(e);
    }
}

// --- Collect ---
async function startCollect() {
    const btn = document.getElementById('btn-start-collect');
    const logs = document.getElementById('collect-logs');
    const resultBox = document.getElementById('collect-result');
    
    const reqBody = {
        engine: document.getElementById('col-engine').value,
        source: document.getElementById('col-source').value,
        task: document.getElementById('col-task').value,
        url: document.getElementById('col-url').value,
        keyword: document.getElementById('col-keyword').value,
        mock: document.getElementById('col-mock').checked
    };
    
    btn.disabled = true;
    logs.innerHTML = '发送请求...\n';
    resultBox.classList.add('hidden');
    
    try {
        const response = await fetch('/api/collect/run', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(reqBody)
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        
        while (true) {
            const {done, value} = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value, {stream: true});
            const lines = chunk.split('\n');
            for (let line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.substring(6));
                        if (data.type === 'progress') {
                            logs.innerHTML += `${data.message}\n`;
                            logs.scrollTop = logs.scrollHeight;
                        } else if (data.type === 'result') {
                            logs.innerHTML += `✅ 采集完成，共 ${data.item_count} 条\n`;
                            resultBox.classList.remove('hidden');
                            document.getElementById('res-count').innerText = data.item_count;
                            document.getElementById('res-path').innerText = data.normalized_file;
                            document.getElementById('res-path').title = data.normalized_file;
                        } else if (data.type === 'error') {
                            logs.innerHTML += `❌ 错误: ${data.message}\n`;
                        }
                    } catch (e) {}
                }
            }
        }
    } catch (e) {
        logs.innerHTML += `❌ 请求失败: ${e.message}\n`;
    } finally {
        btn.disabled = false;
    }
}

// --- Data ---
async function loadFiles() {
    const type = document.getElementById('data-type').value;
    const source = document.getElementById('data-source').value;
    const tbody = document.getElementById('file-list-body');
    
    tbody.innerHTML = '<tr><td colspan="2">加载中...</td></tr>';
    
    try {
        const res = await fetch(`/api/data/files?type=${type}&source=${source}&size=50`);
        const data = await res.json();
        
        tbody.innerHTML = '';
        if (data.files.length === 0) {
            tbody.innerHTML = '<tr><td colspan="2">没有找到文件</td></tr>';
            return;
        }
        
        data.files.forEach(f => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><a href="#" class="file-link text-primary hover:underline" data-path="${f.path}">${f.filename}</a></td>
                <td>${f.size_kb}</td>
            `;
            tbody.appendChild(tr);
        });
        
        document.querySelectorAll('.file-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                previewFile(e.target.getAttribute('data-path'), e.target.innerText);
            });
        });
        
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="2" class="text-error">加载失败</td></tr>`;
    }
}

async function previewFile(path, filename) {
    const preview = document.getElementById('file-preview');
    const title = document.getElementById('preview-title');
    
    title.innerText = `预览: ${filename} (前 20 条)`;
    preview.innerText = '加载中...';
    
    try {
        const res = await fetch(`/api/data/files/${encodeURIComponent(path)}`);
        if (!res.ok) throw new Error('File not found or access denied');
        const data = await res.json();
        
        preview.innerText = JSON.stringify(data, null, 2);
        delete preview.dataset.highlighted;
        hljs.highlightElement(preview);
    } catch (e) {
        preview.innerText = `错误: ${e.message}`;
    }
}

// --- Cache ---
async function loadCacheStats() {
    try {
        const res = await fetch('/api/cache/stats');
        const stats = await res.json();
        
        const container = document.getElementById('cache-cards');
        container.innerHTML = '';
        
        const items = [
            { id: 'vector', name: '向量检索缓存', data: stats.vector_cache },
            { id: 'graph', name: '图查询缓存', data: stats.graph_cache },
            { id: 'llm', name: 'LLM结果缓存', data: stats.llm_cache }
        ];
        
        items.forEach(item => {
            if (!item.data) return;
            const rate = (item.data.hit_rate * 100).toFixed(1);
            container.innerHTML += `
                <div class="card">
                    <h3 class="card-title">${item.name}</h3>
                    <div class="my-4">
                        <div class="flex justify-between text-sm mb-1">
                            <span>命中率</span>
                            <span>${rate}%</span>
                        </div>
                        <div class="w-full bg-gray-700 rounded-full h-2.5">
                            <div class="bg-primary h-2.5 rounded-full" style="width: ${rate}%"></div>
                        </div>
                    </div>
                    <div class="text-sm text-gray-400 mb-4">
                        <p>条目数: ${item.data.size}</p>
                        <p>命中/未命中: ${item.data.hits} / ${item.data.misses}</p>
                    </div>
                    <button class="btn-secondary w-full text-sm" onclick="clearCache('${item.id}', false, false, false)">清空${item.name}</button>
                </div>
            `;
        });
        
    } catch (e) {
        console.error(e);
    }
}

async function clearCache(v, g, l, a) {
    let url = `/api/cache/clear?vector=${v=== 'vector' || a}&graph=${v=== 'graph' || a}&llm=${v=== 'llm' || a}&all=${a}`;
    try {
        const res = await fetch(url, { method: 'DELETE' });
        if (res.ok) {
            alert('缓存已清空');
            loadCacheStats();
        }
    } catch (e) {
        alert('清空失败');
    }
}

// --- Config ---
async function loadConfig() {
    try {
        const res = await fetch('/api/system/config');
        const data = await res.json();
        
        const tbody = document.getElementById('config-table-body');
        tbody.innerHTML = '';
        
        for (const [k, v] of Object.entries(data)) {
            tbody.innerHTML += `
                <tr>
                    <td class="font-medium">${k}</td>
                    <td><span class="bg-gray-800 px-2 py-1 rounded text-gray-300">${v}</span></td>
                </tr>
            `;
        }
        
    } catch (e) {
        console.error(e);
    }
}

// --- Particle Background System ---
function initParticles() {
    const canvas = document.getElementById('particle-canvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    let width, height;
    let particles = [];
    
    // Config
    const PARTICLE_COUNT = Math.min(Math.floor(window.innerWidth / 15), 60);
    const MOUSE_RADIUS = 150;
    
    // Moebius colors
    const colors = ['#8c7aae', '#78a889', '#eab7b7', '#8ab6d6'];
    const inkColor = '#2b2d42';
    
    let mouse = {
        x: null,
        y: null
    };

    function resize() {
        width = window.innerWidth;
        height = window.innerHeight;
        canvas.width = width;
        canvas.height = height;
    }
    
    window.addEventListener('resize', resize);
    window.addEventListener('mousemove', (e) => {
        mouse.x = e.x;
        mouse.y = e.y;
    });
    window.addEventListener('mouseout', () => {
        mouse.x = null;
        mouse.y = null;
    });
    
    resize();

    class Particle {
        constructor() {
            this.reset(true);
        }
        
        reset(randomY = false) {
            this.radius = Math.random() * 6 + 3;
            this.x = Math.random() * width;
            this.y = randomY ? Math.random() * height : height + this.radius * 2;
            this.vx = (Math.random() - 0.5) * 0.5;
            this.vy = -(Math.random() * 0.5 + 0.3); // Float upwards slowly
            
            // 40% filled, 60% outlined
            this.isFilled = Math.random() > 0.6;
            this.fillColor = colors[Math.floor(Math.random() * colors.length)];
            
            // Sway properties
            this.angle = Math.random() * Math.PI * 2;
            this.swaySpeed = Math.random() * 0.02 + 0.01;
            this.swayAmount = Math.random() * 0.5 + 0.1;
        }

        update() {
            this.angle += this.swaySpeed;
            this.x += this.vx + Math.sin(this.angle) * this.swayAmount;
            this.y += this.vy;

            // Reset if it goes off top screen
            if (this.y < -this.radius * 2) {
                this.reset(false);
            }
            
            // Mouse interaction - gentle push
            if (mouse.x != null && mouse.y != null) {
                let dx = mouse.x - this.x;
                let dy = mouse.y - this.y;
                let distance = Math.sqrt(dx * dx + dy * dy);
                if (distance < MOUSE_RADIUS) {
                    let forceDirectionX = dx / distance;
                    let forceDirectionY = dy / distance;
                    let force = (MOUSE_RADIUS - distance) / MOUSE_RADIUS;
                    
                    // Repel smoothly
                    this.x -= forceDirectionX * force * 1.5;
                    this.y -= forceDirectionY * force * 1.5;
                }
            }
        }

        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
            
            if (this.isFilled) {
                ctx.fillStyle = this.fillColor;
                ctx.fill();
            }
            
            ctx.strokeStyle = inkColor;
            ctx.lineWidth = 1.5;
            ctx.stroke();
            
            // Optional: draw a small inner line for some "geometric" particles
            if (this.radius > 6 && !this.isFilled) {
                ctx.beginPath();
                ctx.arc(this.x - 2, this.y - 2, this.radius * 0.2, 0, Math.PI * 2);
                ctx.strokeStyle = inkColor;
                ctx.lineWidth = 1;
                ctx.stroke();
            }
        }
    }

    for (let i = 0; i < PARTICLE_COUNT; i++) {
        particles.push(new Particle());
    }

    function animate() {
        ctx.clearRect(0, 0, width, height);

        for (let i = 0; i < particles.length; i++) {
            particles[i].update();
            particles[i].draw();
        }
        requestAnimationFrame(animate);
    }

    animate();
}
