"""
该模块提供了版本更新和显示版本信息的功能。
包含显示当前版本、更新版本信息以及主交互流程等功能。
"""
import datetime
from pathlib import Path
from utils.version_info import VERSION, UPDATE_DATE

def show_current_version():
    """显示当前版本信息"""
    try:
        print(f"\n当前版本: v{VERSION} ({UPDATE_DATE})")
    except NameError :
        print("\n当前版本: 尚未初始化")

def update_version(new_version, notes):
    """更新版本信息"""
    version_content = f'''# 版本核心信息
VERSION = "{new_version}"
UPDATE_DATE = "{datetime.date.today()}"
AUTHOR = "Gilbert Wang"
PROJECT_NAME = "JARVIS知识库系统"

def get_version_info():
    return {{
        "version": VERSION,
        "update_date": UPDATE_DATE,
        "author": AUTHOR,
        "system": PROJECT_NAME
    }}
    '''

    # 写入版本信息
    Path("./utils/version_info.py").write_text(version_content, encoding="utf-8")

    # 更新历史记录
    today = datetime.date.today()
    header = f"\n\n## v{new_version} ({today})\n"
    history_items = "\n".join(f"- {note}" for note in notes)
    history = header + history_items
    with open("app/static/version/VERSION_HISTORY.md", "a", encoding="utf-8") as f:
        f.write(history)

    print(f"\n✅ 版本已更新至 v{new_version}")

def main():
    """主交互流程"""
    print("🔄 版本更新工具 (Ctrl+C退出)")
    show_current_version()

    try:
        # 获取新版本号
        new_ver = input("\n请输入新版本号: ").strip()
        if not new_ver:
            print("❌ 版本号不能为空")
            return

        # 获取更新说明
        notes = []
        print("\n请输入更新说明 (每条输入后回车，空行结束):")
        while True:
            note = input(f"说明 {len(notes)+1}: ").strip()
            if not note:
                if len(notes) == 0:
                    print("⚠️ 至少需要一条说明")
                    continue
                break
            notes.append(note)

        # 确认信息
        print(f"\n即将更新版本为: v{new_ver}")
        print("更新说明:")
        print("\n".join(f"• {n}" for n in notes))
        confirm = input("\n确认更新吗？(y/n): ").lower()

        if confirm == 'y':
            update_version(new_ver, notes)
        else:
            print("❌ 已取消更新")

    except KeyboardInterrupt:
        print("\n\n⏹️ 操作已取消")

if __name__ == "__main__":
    main()
    