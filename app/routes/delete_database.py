import requests
import json
from requests_toolbelt.multipart.encoder import MultipartEncoder

from app.routes.kb_admin_api import ADMIN_CREDENTIALS

def test_delete_knowledge_base(identifier: str, admin_password: str):

    # API 接口地址（根据实际服务部署调整）
    base_url = "http://localhost:8000"
    delete_endpoint = f"{base_url}/admin/knowledge/delete"

    # 使用 FormData 传递参数（与后端接口匹配）
    multipart_data = MultipartEncoder(
        fields={
            "identifier": identifier,
            "password": admin_password
        }
    )

    try:
        # 发送 POST 请求（注意 Content-Type）
        response = requests.post(
            url=delete_endpoint,
            headers={"Content-Type": multipart_data.content_type},
            data=multipart_data
        )
        response.raise_for_status()  # 检查 HTTP 错误状态码

        # 解析响应
        result = response.json()
        if result.get("status") == "success":
            print(f"删除成功！消息：{result['message']}")
        else:
            print(f"删除失败！错误：{result.get('detail', '未知错误')}")

    except requests.exceptions.HTTPError as e:
        print(f"HTTP 请求错误: {str(e)}")
    except requests.exceptions.ConnectionError:
        print("连接失败，请检查服务是否运行")
    except Exception as e:
        print(f"其他异常: {str(e)}")

if __name__ == "__main__":
    # 示例测试（根据实际需要修改参数）
    TEST_IDENTIFIER = "wer"  # 替换为实际要删除的知识库标识符
    ADMIN_PASSWORD = ADMIN_CREDENTIALS["password"]  # 当前硬编码的管理员密码
    
    test_delete_knowledge_base(
        identifier=TEST_IDENTIFIER,
        admin_password=ADMIN_PASSWORD
    )