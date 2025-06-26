import requests
import json

def test_llm_connection():
    """
    测试LLM服务连接是否正常
    通过向指定URL发送简单问题并打印响应结果
    """
    url = "http://10.55.136.170:7000/v1/chat/completions"
    test_question = "你好，能简单介绍一下你自己吗？"
    
    # 准备请求数据
    payload = {
        "model": "Qwen3_4B",  # 使用与原代码相同的模型
        "messages": [
            {"role": "system", "content": "你是一个AI助手"},
            {"role": "user", "content": test_question}
        ],
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print(f"正在向 {url} 发送测试请求...")
        print(f"测试问题: {test_question}")
        
        # 发送请求
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()  # 如果状态码不是200，抛出异常
        
        # 解析响应
        result = response.json()
        print("\n响应结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 提取并打印AI回复
        if "choices" in result and len(result["choices"]) > 0:
            ai_response = result["choices"][0]["message"]["content"]
            print(f"\nAI回复: {ai_response}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"\n请求失败: {str(e)}")
        return False
    except (KeyError, json.JSONDecodeError) as e:
        print(f"\n响应解析错误: {str(e)}")
        return False

if __name__ == "__main__":
    test_llm_connection()