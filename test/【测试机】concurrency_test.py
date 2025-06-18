import time
import random
import threading
import requests
from collections import defaultdict
import numpy as np

# 测试配置
BASE_URL = "http://10.55.136.191:8000/chat"  # 修改为您的服务器地址
TEST_DURATION = 60  # 测试持续时间(秒)，调整为5分钟
# 新增：阶梯测试配置（用户数从4到16，每4递增，每个用户数测试4次）
STAGE_CONFIG = [
    {"users": 4, "cycles": 4},
    {"users": 5, "cycles": 4},
    {"users": 6, "cycles": 4},
    {"users": 7, "cycles": 4},
]
COOL_DOWN_SECONDS = 120  # 每次测试后冷却
USER_GROUPS = [
    {"name": "重度", "count": 0, "min_hourly": 180, "max_hourly": 300},  # 每小时180-300次 → 每次间隔12-20秒
    {"name": "中度", "count": 10, "min_hourly": 120, "max_hourly": 200},  # 每小时120-200次 → 每次间隔18-30秒
    {"name": "轻度", "count": 0, "min_hourly": 30, "max_hourly": 60},    # 每小时30-60次 → 每次间隔60-120秒
]
NUM_USERS = sum(group["count"] for group in USER_GROUPS)  
QUESTIONS = [
    "并发测试1xx如何设置地图线宽？",
    "并发测试2xx8039错误怎么解决？",
    "并发测试3xxJARVIS系统有哪些功能？",
    "并发测试4xx知识库更新频率是多少？",
    "并发测试5xx技术支持联系方式是什么？",
    "并发测试6xx如何导出地图数据？",
    "并发测试7xx系统支持哪些文件格式？",
    "并发测试8xx如何优化查询性能？",
    "并发测试9xx常见错误代码有哪些？"
]

# 统计结果
response_times = []
stats = defaultdict(list)
lock = threading.Lock()

def simulate_user(user_id, group_name, min_hourly, max_hourly):
    start_time = time.time()
    # 计算该用户类型的单次请求间隔范围（秒）
    min_interval = 3600 / max_hourly  # 最大次数对应最小间隔
    max_interval = 3600 / min_hourly  # 最小次数对应最大间隔
    
    while time.time() - start_time < TEST_DURATION:
        # 按用户类型随机延迟
        time.sleep(random.uniform(min_interval, max_interval))
        
        # 随机选择一个问题
        question = random.choice(QUESTIONS)
        
        try:
            # 记录请求开始时间
            request_start = time.time()
            
            # 发送请求（添加版本验证头）
            response = requests.post(
                f"{BASE_URL}/ask",
                headers={"X-System-Version": "1.8.5"},  # 验证目标系统版本
                data={
                    "question": question,
                    "top_k": random.randint(1, 5),
                    "temperature": round(random.uniform(0.1, 0.9), 1),
                    "collection_type": random.choice(["robot", "mvp"])
                },
                timeout=30
            )
            
            # 计算响应时间
            response_time = time.time() - request_start
            
            # 获取响应内容
            response_data = response.json()
            answer = response_data.get("answer", "")[:15]
            
            # 记录统计信息
            with lock:
                response_times.append(response_time)
                stats["success"].append({
                    "user_id": user_id,
                    "group": group_name,
                    "time": response_time
                })
                
            print(f"用户 {user_id}（{group_name}）问题: {question[:15]}... 答案: {answer}... 耗时: {response_time:.2f}s")
                
        except Exception as e:
            with lock:
                stats["error"].append({
                    "user_id": user_id,
                    "group": group_name,
                    "error": str(e)
                })
            print(f"用户 {user_id}（{group_name}）请求失败: {str(e)}")

def run_test():
    for stage in STAGE_CONFIG:
        current_users = stage["users"]
        total_cycles = stage["cycles"]
        
        for cycle in range(1, total_cycles + 1):
            # 重置统计数据
            global response_times, stats
            response_times = []
            stats = defaultdict(list)
            
            # 动态调整用户组（这里假设只用中度用户）
            USER_GROUPS[1]["count"] = current_users  # 中度用户数设为当前阶段用户数
            NUM_USERS = sum(group["count"] for group in USER_GROUPS)
            
            print(f"\n==== 开始阶段测试：用户数 {current_users}，第 {cycle}/{total_cycles} 轮 ====")
            print(f"当前测试用户数: {NUM_USERS}（中度用户）")
            
            # 创建并启动线程
            threads = []
            user_id = 1
            for group in USER_GROUPS:
                for _ in range(group["count"]):
                    t = threading.Thread(
                        target=simulate_user,
                        args=(user_id, group["name"], group["min_hourly"], group["max_hourly"])
                    )
                    t.start()
                    threads.append(t)
                    user_id += 1
            
            # 等待当前轮次所有线程完成
            for t in threads:
                t.join()
            
            # 输出当前轮次统计结果
            if response_times:
                times = np.array(response_times)
                print(f"\n---- 阶段 {current_users} 用户，第 {cycle} 轮测试结果 ----")
                print(f"总提问数: {len(response_times)}")
                print(f"成功请求: {len(stats['success'])}")
                print(f"失败请求: {len(stats['error'])}")
                print(f"平均响应时间: {times.mean():.2f}s")
                print(f"中位数响应时间: {np.median(times):.2f}s")
                print(f"最大响应时间: {times.max():.2f}s")
                print(f"90百分位响应时间: {np.percentile(times, 90):.2f}s")
            
            # 冷却等待（最后一轮不等待）
            if cycle < total_cycles:
                print(f"\n开始冷却 {COOL_DOWN_SECONDS} 秒...")
                time.sleep(COOL_DOWN_SECONDS)
            else:
                print(f"\n阶段 {current_users} 用户测试完成，进入下一阶段\n")

if __name__ == "__main__":
    print("==== 开始阶梯并发测试 ====")
    print(f"测试阶段配置: {STAGE_CONFIG}")
    print(f"每阶段测试后冷却时间: {COOL_DOWN_SECONDS} 秒\n")
    run_test()
    print("==== 所有阶梯测试完成 ====")