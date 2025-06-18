from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
import requests
import json
import time
import os
from dotenv import load_dotenv

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def test_page(request: Request):
    return """
    <html>
    <head>
        <title>流式响应测试</title>
        <style>
            #output { 
                border: 1px solid #ccc; 
                padding: 20px; 
                margin: 20px; 
                min-height: 200px;
                white-space: pre-wrap;
            }
            .speed {
                color: #666;
                margin-left: 20px;
            }
        </style>
    </head>
    <body>
        <h1>流式响应测试</h1>
        <button onclick="startStream()">开始测试</button>
        <div id="output"></div>
        
        <script>
            function startStream() {
                const output = document.getElementById('output');
                output.innerHTML = '连接中...';
                
                const eventSource = new EventSource('/stream');
                
                eventSource.onmessage = function(e) {
                    const data = JSON.parse(e.data);
                    if (data.content) {
                        output.innerHTML += data.content;
                    }
                    if (data.speed) {
                        document.querySelector('.speed').innerHTML = 
                            `当前速度: ${data.speed.toFixed(1)}字符/秒`;
                    }
                };
                
                eventSource.onerror = function(e) {
                    output.innerHTML += '\\n连接关闭';
                    eventSource.close();
                };
            }
        </script>
        <div class="speed"></div>
    </body>
    </html>
    """

@app.get("/stream")
async def stream_response():
    def generate():
        url = os.getenv("LLM_SERVER_URL", "http://10.55.136.191:7000") + "/v1/chat/completions"
        messages = [
            {"role": "system", "content": "你是一个AI助手，请用流式传输方式回答用户问题"},
            {"role": "user", "content": "请详细说明人工智能的工作原理"}
        ]
        start_time = time.time()
        total_tokens = 0
        
        try:
            response = requests.post(
                url,
                json={
                    "model": os.getenv("LLM_MODEL_NAME", "Qwen2.5_7B"),
                    "messages": messages,
                    "temperature": 0.7,
                    "stream": True
                },
                stream=True,
                timeout=10
            )
            response.raise_for_status()  # 检查请求是否成功

            for chunk in response.iter_lines():
                if chunk:
                    decoded = chunk.decode('utf-8').strip()
                    if decoded.startswith('data: '):
                        try:
                            data = json.loads(decoded[6:])
                            content = data['choices'][0]['delta'].get('content', '')
                            elapsed = time.time() - start_time
                            speed = total_tokens / elapsed if elapsed > 0 else 0

                            if content:
                                total_tokens += len(content)
                                yield f"data: {json.dumps({'content': content, 'speed': speed})}\n\n"

                        except json.JSONDecodeError as e:
                            yield f"data: {json.dumps({'error': f'JSON解析错误: {str(e)}'})}\n\n"
                        except KeyError as e:
                            yield f"data: {json.dumps({'error': f'数据结构错误: {str(e)}'})}\n\n"
        except requests.RequestException as e:
            yield f"data: {json.dumps({'error': f'请求错误: {str(e)}'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
