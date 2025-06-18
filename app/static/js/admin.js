document.addEventListener('DOMContentLoaded', () => {
    // 知识库搜索过滤
    const kbSearch = document.getElementById('kbSearch');
    kbSearch.addEventListener('input', filterKbList);

    // 分块参数实时预览
    const chunkSize = document.getElementById('chunkSize');
    const chunkOverlap = document.getElementById('chunkOverlap');
    chunkSize.addEventListener('input', updateChunkPreview);
    chunkOverlap.addEventListener('input', updateChunkPreview);

    // 文件上传处理
    const dropZone = document.getElementById('dropZone');
    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', handleDragOver);
    dropZone.addEventListener('drop', handleFileDrop);

    // 初始化进度环
    const progressRing = document.querySelector('.progress-ring__circle');
    const radius = progressRing.r.baseVal.value;
    const circumference = radius * 2 * Math.PI;
    progressRing.style.strokeDasharray = `${circumference} ${circumference}`;
});

// 修改文件输入框为支持目录选择
const fileInput = document.getElementById('fileInput');
fileInput.setAttribute('webkitdirectory', '');
fileInput.setAttribute('directory', '');
fileInput.setAttribute('multiple', '');

// 重写文件拖放处理逻辑，支持目录遍历
async function handleFileDrop(e) {
    e.preventDefault();
    const items = e.dataTransfer.items;
    const formData = new FormData();

    if (!window.selectedKB) {
        alert('请先选择知识库');
        return;
    }

    // 递归遍历目录获取所有文件及相对路径
    const traverseDir = async (entry, basePath = '') => {
        if (entry.isDirectory) {
            const dirReader = entry.createReader();
            const entries = await new Promise(resolve => dirReader.readEntries(resolve));
            for (const subEntry of entries) {
                await traverseDir(subEntry, `${basePath}${entry.name}/`);
            }
        } else if (entry.isFile) {
            const file = await new Promise(resolve => entry.file(resolve));
            const relativePath = `${basePath}${entry.name}`;
            formData.append('files', file, relativePath);  // 保留相对路径
        }
    };

    // 处理所有选中的目录/文件
    for (const item of items) {
        if (item.kind === 'file') {
            const entry = item.webkitGetAsEntry();
            if (entry) {
                await traverseDir(entry);
            }
        }
    }

    formData.append('knowledge_base_id', window.selectedKB.id);
    
    // 上传逻辑（保持原有）
    try {
        const response = await fetch('/admin/knowledge/upload-files', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            // 处理成功状态
            progressText.textContent = '处理完成';
        }
    } catch (error) {
        console.error('上传失败:', error);
    }
}

// // 危险操作验证
// document.getElementById('btnDelete').addEventListener('click', async () => {
//     const selectedKB = window.selectedKB;
//     if (!selectedKB) {
//         alert('请选择要删除的知识库');
//         return;
//     }

//     // 新增确认弹窗（显示标识符）
//     const confirmDelete = confirm(`是否确认删除标识符为 ${selectedKB.identifier} 的知识库？`);
//     if (!confirmDelete) return;

//     try {
//         const formData = new FormData()
//         formData.append('identifier',window.selectedKB.identifier)

//         // 调整为POST请求，传递标识符参数
//         console.log('即将删除的知识库标识符:', selectedKB.identifier);
//         const deleteRes = await fetch(`/admin/knowledge/delete`, {
//             method: 'POST',
//             body: formData
//         });
        
//         if (deleteRes.ok) {
//             alert('知识库删除成功');
//             location.reload(); // 刷新页面更新列表
//         } else {
//             alert('删除失败：' + await deleteRes.text());
//         }
//     } catch (error) {
//         alert('删除请求异常：' + error.message);
//     }
// });

// function showAuthModal(callback) {
//     const modal = document.getElementById('authModal');
//     modal.style.display = 'block';
    
//     document.getElementById('confirmAction').onclick = () => {
//         const password = document.getElementById('adminPassword').value;
//         callback(password);
//         modal.style.display = 'none';
//     };
// }


// 新增操作日志加载
async function loadOperationLogs() {
    try {
        const response = await fetch('/admin/knowledge/operation-logs');
        const logs = await response.json();
        
        const logsView = document.createElement('div');
        logsView.id = 'logsView';
        logsView.className = 'view';
        logsView.innerHTML = `
            <div class="log-header">
                <h3>最近操作记录</h3>
                <button class="btn-refresh">↻ 刷新</button>
            </div>
            <div class="log-list">
                ${logs.map(log => `
                    <div class="log-item ${log.status}">
                        <div class="log-meta">
                            <span class="timestamp">${new Date(log.timestamp).toLocaleString()}</span>
                            <span class="badge">${log.operation}</span>
                        </div>
                        <div class="log-content">${log.details}</div>
                    </div>
                `).join('')}
            </div>
        `;
        
        document.querySelector('.workspace').appendChild(logsView);
        logsView.querySelector('.btn-refresh').addEventListener('click', loadOperationLogs);
    } catch (error) {
        console.error('加载日志失败:', error);
    }
}

// 扩展视图切换功能
function showView(viewId) {
    document.querySelectorAll('.view').forEach(v => {
        v.classList.remove('active');
        if(v.id === viewId) {
            if(viewId === 'logsView' && !v.innerHTML) {
                loadOperationLogs();
            }
            v.classList.add('active');
        }
    });
}


// 增强分块预览逻辑
function updateChunkPreview() {
    const original = `这是一个示例文本用于展示分块效果。当调整分块参数时，可以实时看到文本如何被分割成多个块，并且相邻块之间会有指定的重叠部分。这有助于优化知识检索效果。`;
    
    const chunkSize = parseInt(chunkSize.value);
    const overlap = parseInt(chunkOverlap.value);
    
    // 分块算法实现
    const chunks = [];
    let pos = 0;
    while(pos < original.length) {
        const end = pos + chunkSize;
        const start = Math.max(0, pos - overlap);
        chunks.push(original.slice(start, end));
        pos = end - overlap;
    }
    
    // 可视化展示
    const previewHTML = chunks.map((chunk, i) => {
        const overlapMark = i > 0 ? `<mark class="overlap">${chunk.slice(0, overlap)}</mark>` : '';
        const mainContent = chunk.slice(overlap);
        return `
            <div class="chunk">
                <div class="chunk-header">块 #${i+1}</div>
                <div class="chunk-content">
                    ${overlapMark}${mainContent}
                </div>
            </div>
        `;
    }).join('');
    
    chunkPreview.innerHTML = previewHTML;
}

// 初始化分块预览
document.querySelectorAll('#chunkSize, #chunkOverlap').forEach(input => {
    input.addEventListener('input', updateChunkPreview);
});

document.getElementById('btnConfirmUpload').addEventListener('click', async () => {
    if (!window.selectedKB) {
        alert('请先选择知识库');
        return;
    }

    const formData = new FormData();
    const files = document.getElementById('fileInput').files;

    console.log(files)
    
    for (const file of files) {
        formData.append('files', file);
        console.log(formData)
    }
    formData.append('knowledge_base_id', window.selectedKB.id);
    console.log(window.selectedKB.id)
    console.log(formData)
    console.log(formData.values)
    console.log(formData.knowledge_base)
    console.log(formData.files)
    

    try {
        const response = await fetch('/admin/knowledge/upload-files', {
            method: 'POST',
            body: formData
        });
        console.log(formData)

        const result = await response.json();
        if (response.ok) {
            alert(`文件上传成功到知识库: ${result.knowledge_base}`);
        } else {
            throw new Error(result.message || '上传失败');
        }
    } catch (error) {
        console.error('上传失败:', error);
        alert('上传失败: ' + error.message);
    }       
});


document.getElementById('btnVectorize').addEventListener('click', async () => {
    if (!window.selectedKB) {
        alert('请先选择知识库');
        return;
    }
    console.log(1)

    try {
        console.log(2)
        const formData = new FormData()
        formData.append('knowledge_base',window.selectedKB.identifier)

        const response = await fetch('/admin/knowledge/vectorize-kb', {
            method: 'POST',
            body: formData
        });
        console.log(response)
        console.log(window.selectedKB.identifier)

        const result = await response.json();
        if (response.ok) {
            console.log(4)
            alert(`知识库 ${window.selectedKB.name} 向量化成功！`);
        } else {
            console.log(5)
            throw new Error(result.message || '向量化失败');
        }
    } catch (error) {
        console.error('向量化失败:', error);
        alert('向量化失败: ' + error.message);
    }
});


// 初始化：根据用户角色显示按钮
document.addEventListener('DOMContentLoaded', () => {
    const currentUser = JSON.parse(sessionStorage.getItem('currentUser'));
    if (currentUser?.role === 'Admin') {
        document.getElementById('btnNewKB').style.display = 'block';
    }

    // 选中知识库时启用操作日志按钮
    document.querySelectorAll('.kb-item').forEach(item => {
        item.addEventListener('click', () => {
            document.getElementById('btnOperationLogs').disabled = false;
        });
    });
});


document.addEventListener('DOMContentLoaded', () => {
    // 新增加载状态指示器
    const kbList = document.querySelector('.kb-list');
    kbList.innerHTML = '<div class="loading">加载知识库列表...</div>';

    // 优化后的列表加载逻辑
    fetch('/admin/knowledge/list-kbs')
        .then(async res => {
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            return await res.json();
        })
        .then(data => {
            kbList.innerHTML = '';
            if (!data || data.length === 0) {
                kbList.innerHTML = '<div class="empty">暂无知识库</div>';
                return;
            }

            // 添加排序功能 - 按名称排序
            data.sort((a, b) => a.name.localeCompare(b.name));
            
            data.forEach(kb => {
                const item = document.createElement('div');
                item.className = 'kb-item';
                item.dataset.id = kb.knowledge_base_id;
                item.dataset.status = kb.status || 'unknown';
                
                // 添加更丰富的信息展示
                item.innerHTML = `
                    <div class="kb-name">${kb.name}</div>
                    <div class="kb-meta">
                        <span class="kb-id">ID: ${kb.identifier}</span>
                        <span class="kb-status">状态: ${kb.status}</span>
                    </div>
                `;
                
                // 添加点击事件
                item.addEventListener('click', () => {
                    document.querySelectorAll('.kb-item').forEach(i => 
                        i.classList.remove('active'));
                    item.classList.add('active');
                    
                    // 保存选中的知识库信息到全局变量
                    window.selectedKB = {
                        id: kb.knowledge_base_id,
                        name: kb.name,
                        identifier: kb.identifier,
                        path: `D:\\401385\\zizi-1.5-5.6\\markdown_files\\${kb.identifier}`
                    };
                
                // 新增：启用删除按钮
                document.getElementById('btnDelete').disabled = false;
                });
                
                kbList.appendChild(item);
            });
        })
        .catch(error => {
            console.error('加载知识库列表失败:', error);
            kbList.innerHTML = `<div class="error">加载失败: ${error.message}</div>`;
        });
});

document.getElementById('btnNewKB').addEventListener('click', () => {
    const name = prompt('请输入知识库名称');
    const id = prompt('请输入知识库标识符(英文)');
    if(name && id) {
        fetch('/admin/knowledge/create-kb', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name, identifier: id})
        }).then(res => res.json())
        .then(data => {
            if(data.status === 'success') {
                location.reload();
            }
        });
    }
});


// 控制"新建知识库"按钮显示（新增）
const btnNewKB = document.getElementById('btnNewKB');
if (typeof window.isAdmin !== 'undefined' && !window.isAdmin) {
    btnNewKB.style.display = 'none';  // 非管理员隐藏按钮
}

