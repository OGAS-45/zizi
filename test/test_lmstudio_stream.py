import requests
import json
import time

def test_stream_response():
    # 直接调用LLM服务器接口
    url = "http://10.55.136.170:7000/v1/chat/completions"
    
    messages = [
        {"role": "system", "content": "你是一个AI助手，请用流式传输方式回答用户问题"},
        {"role": "user", "content": "请用流式传输方式回答：为什么天空是蓝色的？"}
    ]
    
    try:
        response = requests.post(
            url,
            json={
                "model": os.getenv("LLM_MODEL_NAME"),
                "messages": messages,
                "temperature": 0.7,
                "stream": True  # 关键参数启用流式传输
            },
            stream=True,
            timeout=10
        )

        print("流式响应开始：")
        start_time = time.time()
        total_tokens = 0
        
        for chunk in response.iter_lines():
            if chunk:
                decoded = chunk.decode('utf-8').strip()
                if not decoded.startswith('data: '):
                    continue
                
                try:
                    data = json.loads(decoded[6:])
                    content = data['choices'][0]['delta'].get('content', '')
                    if content:
                        # 计算实时速度
                        elapsed = time.time() - start_time
                        total_tokens += len(content)  # 简单用字符数代替token
                        speed = total_tokens / elapsed if elapsed > 0 else 0
                        
                        print(f"{content}", end='', flush=True)
                        # print(f" [速度: {speed:.1f}字符/秒]", end='\r')  # 实时显示速度
                except Exception as parse_error:
                    print(f"\n解析错误: {str(parse_error)}")
                    continue
        print("\n\n流式响应结束")

    except Exception as e:
        print(f"请求失败: {str(e)}")

if __name__ == "__main__":
    test_stream_response()