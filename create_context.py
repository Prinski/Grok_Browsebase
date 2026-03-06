import os
from browserbase import Browserbase

BROWSERBASE_API_KEY    = os.getenv("BROWSERBASE_API_KEY")
BROWSERBASE_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID")

def main():
    client = Browserbase(api_key=BROWSERBASE_API_KEY)
    ctx = client.contexts.create(project_id=BROWSERBASE_PROJECT_ID)
    print("=" * 65, flush=True)
    print("✅ 新 Context 创建成功！", flush=True)
    print(f"请将以下值添加到 GitHub Secrets：", flush=True)
    print(f"变量名：BROWSERBASE_CONTEXT_ID", flush=True)
    print(f"变量值：{ctx.id}", flush=True)
    print("=" * 65, flush=True)

if __name__ == "__main__":
    main()
