import os
import re
import time
import json
import requests
from browserbase import Browserbase
from playwright.sync_api import sync_playwright

# ── 环境变量 ──────────────────────────────────────────────────────
BROWSERBASE_API_KEY    = os.getenv("BROWSERBASE_API_KEY", "")
BROWSERBASE_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID", "")
BROWSERBASE_CONTEXT_ID = os.getenv("BROWSERBASE_CONTEXT_ID", "")
JIJYUN_WEBHOOK_URL     = os.getenv("JIJYUN_WEBHOOK_URL", "")
FEISHU_WEBHOOK_URL     = os.getenv("FEISHU_WEBHOOK_URL", "")

def get_beijing_date_cn() -> str:
    from datetime import datetime, timezone, timedelta
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).strftime("%Y年%m月%d日")

# ════════════════════════════════════════════════════════════════
# Step 0：选择 Grok 4.2 Beta 模型
# ════════════════════════════════════════════════════════════════
def select_model(page):
    print("\n[模型选择] 正在选择 Grok 4.2 Beta...", flush=True)
    try:
        # 点击模型选择器按钮（通常在输入框上方或顶部）
        model_btn = page.wait_for_selector(
            "button[aria-haspopup='listbox'], "
            "button[aria-label*='model'], "
            "button[aria-label*='Model'], "
            "[data-testid='model-selector']",
            timeout=10000
        )
        model_btn.click()
        time.sleep(1)

        # 点击 Grok 4.2 Beta 选项
        grok4_option = page.wait_for_selector(
            "li:has-text('4.2'), "
            "div[role='option']:has-text('4.2'), "
            "button:has-text('Grok 4.2'), "
            "[data-value*='4.2']",
            timeout=8000
        )
        grok4_option.click()
        time.sleep(1)
        print("[模型选择] ✅ 已选择 Grok 4.2 Beta", flush=True)
    except Exception as e:
        print(f"[模型选择] ⚠️ 选择失败，使用当前默认模型：{e}", flush=True)
    page.screenshot(path="00_model_selected.png")

# ════════════════════════════════════════════════════════════════
# 核心函数 1：粘贴提示词并发送
# ════════════════════════════════════════════════════════════════
def send_prompt(page, prompt_text: str, label: str):
    print(f"\n[{label}] 填写提示词（共 {len(prompt_text)} 字符）...", flush=True)

    input_box = page.wait_for_selector(
        "div[contenteditable='true'], textarea",
        timeout=30000
    )
    input_box.click()
    time.sleep(0.5)

    # 清空
    page.keyboard.press("Control+a")
    page.keyboard.press("Backspace")
    time.sleep(0.3)

    # 剪贴板粘贴
    page.evaluate("""(text) => {
        const dt = new DataTransfer();
        dt.setData('text/plain', text);
        document.activeElement.dispatchEvent(
            new ClipboardEvent('paste', {clipboardData: dt, bubbles: true})
        );
    }""", prompt_text)
    time.sleep(1.5)

    page.screenshot(path=f"before_{label}.png")

    # 点发送
    send_btn = page.wait_for_selector(
        "button[aria-label='Send message'], button[type='submit']",
        timeout=10000
    )
    send_btn.click()
    print(f"[{label}] ✅ 已发送，等待 Grok 开始生成...", flush=True)
    time.sleep(5)

# ════════════════════════════════════════════════════════════════
# 核心函数 2：等待生成完毕，返回最新回复文本
# ════════════════════════════════════════════════════════════════
def wait_and_extract(page, label: str,
                     interval: int = 3,
                     stable_rounds: int = 4,
                     max_wait: int = 120) -> str:
    print(f"[{label}] 等待 Grok 回复（最长 {max_wait}s）...", flush=True)
    last_len = -1
    stable   = 0
    elapsed  = 0

    while elapsed < max_wait:
        time.sleep(interval)
        elapsed += interval

        text = page.evaluate("""() => {
            const msgs = document.querySelectorAll(
                '[data-testid="message"], .message-bubble, .response-content'
            );
            return msgs.length ? msgs[msgs.length - 1].innerText : "";
        }""")

        cur_len = len(text.strip())
        print(f"  {elapsed}s | 字符数: {cur_len}", flush=True)

        if cur_len == last_len and cur_len > 0:
            stable += 1
            if stable >= stable_rounds:
                print(f"[{label}] ✅ 回复完毕（连续 {stable_rounds} 次稳定）", flush=True)
                page.screenshot(path=f"done_{label}.png")
                return text.strip()
        else:
            stable   = 0
            last_len = cur_len

    print(f"[{label}] ⚠️ 已达上限 {max_wait}s，强制取结果", flush=True)
    page.screenshot(path=f"timeout_{label}.png")
    return page.evaluate("""() => {
        const msgs = document.querySelectorAll(
            '[data-testid="message"], .message-bubble, .response-content'
        );
        return msgs.length ? msgs[msgs.length - 1].innerText : "";
    }""").strip()

# ════════════════════════════════════════════════════════════════
# 阶段 A 提示词（固定）
# ════════════════════════════════════════════════════════════════
def build_prompt_a() -> str:
    date_string = get_beijing_date_cn()
    return f"""今天是新加坡/北京时间 {date_string}。你现在是一台绝对客观、严格遵守底层物理限制的"X 商业情报吸尘器"。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【阶段 0：前置时间计算（必须首先执行！）】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
请立即使用 code_execution 工具运行以下 Python 代码获取时间戳：
```python
import time
now = int(time.time())
print(f"since_time:{{now - 86400}} until_time:{{now}}")
```
👉 获取后必须将其写入下方搜索语句，并在日志中输出对应的 UTC 时间。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【阶段 A：无差别原始拉取 + 输出前过滤】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
第一步（拉取）：按以下批次执行全量拉取。
第二步（过滤）：对每条记录执行"三级过滤铁律"（过滤空壳、无关主题、无意义评论）。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【约束 1：10 批次并行拉取列表】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
批次 1（顶层巨头）：@sama, @lexfridman, @elonmusk, @karpathy, @ylecun, @sundarpichai, @satyanadella, @darioamodei, @gdb, @demishassabis, @geoffreyhinton, @jeffdean
批次 2（芯片与算力）：@jensenhuang, @LisaSu, @anshelsag, @IanCutress, @PatrickMoorhead, @ServeTheHome, @dylan522p, @SKHynix, @TSMC, @RajaXg
批次 3（AI 硬件与新物种）：@rabbit_inc, @Humane, @BrilliantLabsAR, @Frame_AI, @LimitlessAI, @Plaud_Official, @TabAl_HQ, @OasisAI, @Friend_AI, @AImars
批次 4（空间计算与 XR）：@ID_AA_Carmack, @boztank, @LumusVision, @XREAL_Global, @vitureofficial, @magicleap, @KarlGuttag, @NathieVR, @SadieTeper, @lucasrizzo
批次 5（硅谷观察家）：@rowancheung, @bentossell, @p_millerd, @venturebeat, @TechCrunch, @TheInformation, @skorusARK, @william_yang, @backlon, @vladsavov
批次 6（中文圈核心 A）：@dotey, @oran_ge, @waylybaye, @tualatrix, @K_O_D_A_D_A, @Sun_Zhuo, @Xander0214, @wong2_x, @imxiaohu, @vista8, @1moshu, @qiushui_ai
批次 7（中文圈核心 B）：@xiaogang_ai, @AI_Next_Gen, @MoonshotAI, @01AI_Official, @ZhipuAI, @DeepSeek_AI, @Baichuan_AI, @MiniMax_AI, @StepFun_AI, @Kimi_AI
批次 8（开发者与极客）：@stroughtonsmith, @_inside, @ali_heston, @bigclivedotcom, @chr1sa, @kevin_ashton, @DanielElizalde, @antgrasso, @Scobleizer, @GaryMarcus
批次 9（一级市场捕手）：@a16z, @sequoia, @ycombinator, @GreylockVC, @Accel, @Benchmark, @foundersfund, @IndexVentures, @LightspeedVP, @GeneralCatalyst
批次 10（研究与前沿）：@OpenAI, @GoogleDeepMind, @AnthropicAI, @MistralAI, @HuggingFace, @StabilityAI, @Midjourney, @Perplexity_AI, @GroqInc, @CerebrasSystems

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【输出格式：LLM 机读压缩行】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
列顺序固定：handle | 动作 | 对象 | 赞 | 评 | 内容直译 | 评论
字段规则：动作 P=原创, RT=转发, Q=引用, R=回复。指代不明请标注 [原推含图/链接，指代不明]。

最后附上单行检索日志。"""

# ════════════════════════════════════════════════════════════════
# 阶段 B 提示词（固定）
# ════════════════════════════════════════════════════════════════
def build_prompt_b() -> str:
    date_string = get_beijing_date_cn()
    return f"""【阶段 B：主编排版与深度解码】

你现在的角色是"AI 圈的顶级观察员与吃瓜课代表"。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【🧠 第一步：深度思考与打草稿】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
为了保证日报品质，请先进行深度的"思维链"分析。
1. 挑选最有价值的 10 个话题。
2. 仔细推敲"隐性博弈"和"资本风向标"的底层逻辑。
3. 思考过程你可以畅所欲言，但必须放在【最终成稿】之前。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【🚨 第二步：最终机器输出规范（严格执行）】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
完成思考后，请严格按以下格式输出最终定稿：

1. 强制机器抓取标识（极其重要）：为了防止你的排版被网页吃掉，你必须将所有最终输出内容，**完整包裹在一个 markdown 代码块中**（即使用 ```markdown 开始，``` 结束）。在代码块之外，不准说任何多余的废话！
   ⚠️ 绝对禁止将这对代码块符号放在任何"思考"或"草稿"段落中。
2. 代码块内防嵌套：在 ```markdown 内部的正文中，严禁再嵌套使用三个反引号包裹任何局部内容。
3. 绝不保留占位说明：下面模板中的括号提示语，请替换为你的真实分析，绝不能把"在此处填写"原样输出！

```markdown
📡 AI圈极客吃瓜日报 | {date_string}

**🏰 【巨头宫斗】**

**🍉 1. 填入真实话题标题**
**🗣️ 极客原声态：**
@原推账号 | 真实姓名 (❤️赞/💬评)
> "填入中文译文，绝对不要包含任何URL链接"
**📝 捕手解码：**
• 📌 增量事实：填入对该事件的客观事实补充
• 🧠 隐性博弈：填入巨头或行业之间的暗战剖析
• 🎯 资本风向标：填入对投资或商业趋势的研判

**🍉 2. 填入下一个话题标题**
...格式同上...

---

**🇨🇳 【中文圈大瓜】**

**🍉 3. 填入话题标题**
...以此类推，完成后续维度共 10 个话题...
```"""

# ════════════════════════════════════════════════════════════════
# 从 Grok 回复中提取 ```markdown ... ``` 代码块内容
# ════════════════════════════════════════════════════════════════
def extract_markdown_block(text: str) -> str:
    match = re.search(r'```markdown\s*([\s\S]+?)\s*```', text)
    if match:
        print("✅ 成功提取 markdown 代码块内容", flush=True)
        return match.group(1).strip()
    print("⚠️ 未找到 ```markdown 块，返回原始文本", flush=True)
    return text.strip()

# ════════════════════════════════════════════════════════════════
# 推送：飞书
# ════════════════════════════════════════════════════════════════
def push_to_feishu(text: str):
    if not FEISHU_WEBHOOK_URL:
        print("⚠️ FEISHU_WEBHOOK_URL 未配置，跳过", flush=True)
        return
    payload = {"msg_type": "text", "content": {"text": text[:4000]}}
    resp = requests.post(FEISHU_WEBHOOK_URL, json=payload, timeout=30)
    print(f"飞书推送：{resp.status_code}", flush=True)

# ════════════════════════════════════════════════════════════════
# 推送：极简云（微信公众号草稿）
# ════════════════════════════════════════════════════════════════
def push_to_jijyun(text: str, title: str):
    if not JIJYUN_WEBHOOK_URL:
        print("⚠️ JIJYUN_WEBHOOK_URL 未配置，跳过", flush=True)
        return
    html = text.replace("\n", "<br>")
    payload = {"title": title, "content": html, "draft": True}
    resp = requests.post(JIJYUN_WEBHOOK_URL, json=payload, timeout=30)
    print(f"极简云推送：{resp.status_code}", flush=True)

# ════════════════════════════════════════════════════════════════
# 主流程
# ════════════════════════════════════════════════════════════════
def main():
    if not BROWSERBASE_CONTEXT_ID:
        print("❌ 未找到 BROWSERBASE_CONTEXT_ID，请先配置 GitHub Secrets", flush=True)
        raise SystemExit(1)

    print("\n初始化 Browserbase 会话...", flush=True)
    client  = Browserbase(api_key=BROWSERBASE_API_KEY)
    session = client.sessions.create(
        project_id=BROWSERBASE_PROJECT_ID,
        browser_settings={
            "context": {"id": BROWSERBASE_CONTEXT_ID, "persist": True}
        }
    )
    print(f"会话 ID：{session.id}", flush=True)

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(session.connect_url)
        ctx     = browser.contexts[0]
        page    = ctx.new_page()

        # ── Step 1：打开 Grok ────────────────────────────────────
        print("\n[Step 1] 打开 grok.com...", flush=True)
        page.goto("https://grok.com/", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)
        page.screenshot(path="00_opened.png")

        # ── Step 2：选择 Grok 4.2 Beta 模型 ─────────────────────
        select_model(page)

        # ── Step 3：发送阶段 A 提示词 ────────────────────────────
        send_prompt(page, build_prompt_a(), "阶段A")

        # ── Step 4：等待阶段 A 完成（最长 2 分钟）───────────────
        wait_and_extract(page, "阶段A", interval=3, stable_rounds=4, max_wait=120)

        # ── Step 5：发送阶段 B 提示词（同一对话，Grok 有上下文）─
        send_prompt(page, build_prompt_b(), "阶段B")

        # ── Step 6：等待阶段 B 完成（最长 2 分钟），提取 Markdown
        raw_result = wait_and_extract(page, "阶段B", interval=3,
                                       stable_rounds=4, max_wait=120)

        # ── Step 7：提取 ```markdown 代码块 ─────────────────────
        final_markdown = extract_markdown_block(raw_result)
        print(f"\n最终内容长度：{len(final_markdown)} 字符", flush=True)

        # ── Step 8：提取标题 ─────────────────────────────────────
        title_match = re.search(r'AI圈极客吃瓜日报[^\n]*', final_markdown)
        title = title_match.group(0).strip() if title_match else f"{get_beijing_date_cn()} AI圈极客吃瓜日报"
        print(f"标题：{title}", flush=True)

        # ── Step 9：推送飞书 ─────────────────────────────────────
        print("\n[Step 9] 推送飞书...", flush=True)
        push_to_feishu(final_markdown)

        # ── Step 10：推送极简云 ───────────────────────────────────
        print("\n[Step 10] 推送极简云...", flush=True)
        push_to_jijyun(final_markdown, title)

        browser.close()

    print("\n🎉 全部完成！", flush=True)

if __name__ == "__main__":
    main()
