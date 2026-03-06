import os, time
from browserbase import Browserbase
from playwright.sync_api import sync_playwright

BROWSERBASE_API_KEY    = os.getenv("BROWSERBASE_API_KEY")
BROWSERBASE_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID")
BROWSERBASE_CONTEXT_ID = os.getenv("BROWSERBASE_CONTEXT_ID")

def main():
    print(f"使用 Context ID：{BROWSERBASE_CONTEXT_ID}", flush=True)
    client  = Browserbase(api_key=BROWSERBASE_API_KEY)
    session = client.sessions.create(
        project_id=BROWSERBASE_PROJECT_ID,
        browser_settings={
            "context": {"id": BROWSERBASE_CONTEXT_ID, "persist": True}
        }
    )

    print(f"✅ 会话创建成功：{session.id}", flush=True)
    print(f"🔗 远程调试地址：{session.connect_url}", flush=True)

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(session.connect_url)
        ctx  = browser.contexts[0]
        page = ctx.new_page()

        print("正在打开 Grok 登录页...", flush=True)
        page.goto("https://grok.com/", wait_until="domcontentloaded", timeout=60000)

        # ── 等待 90 秒供你完成手动登录 ──
        # Browserbase 的 Live View 里手动操作
        print("⏳ 等待 90 秒，请在 Browserbase Live View 里完成登录...", flush=True)
        for i in range(9):
            time.sleep(10)
            print(f"  已等待 {(i+1)*10} 秒...", flush=True)

        # 验证登录态
        title = page.title()
        print(f"当前页面标题：{title}", flush=True)
        if "Grok" in title:
            print("✅ 登录态验证成功，Context 已保存！", flush=True)
        else:
            print("⚠️ 请检查是否完成了登录", flush=True)

        page.screenshot(path="login_check.png")
        print("📸 截图已保存为 login_check.png", flush=True)

        page.close()
        browser.close()

    print("登录流程完成", flush=True)

if __name__ == "__main__":
    main()
