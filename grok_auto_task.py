import requests, time, os, json, re
from browserbase import Browserbase
from playwright.sync_api import sync_playwright
from datetime import datetime, timezone, timedelta

# ================================================================
#  环境变量（全部从 GitHub Secrets 读取，本地不需要填任何值）
# ================================================================
BROWSERBASE_API_KEY    = os.getenv("BROWSERBASE_API_KEY")
BROWSERBASE_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID")
BROWSERBASE_CONTEXT_ID = os.getenv("BROWSERBASE_CONTEXT_ID", "")
JIJYUN_WEBHOOK_URL     = os.getenv("JIJYUN_WEBHOOK_URL")
FEISHU_WEBHOOK_URL     = os.getenv("FEISHU_WEBHOOK_URL", "")
KIMI_API_KEY           = os.getenv("KIMI_API_KEY")
XAI_API_KEY            = os.getenv("XAI_API_KEY")

# ================================================================
#  固定配置
# ================================================================
AUTHOR = "大尉Prinski"

# 兜底封面图（当 xAI 生图失败时使用）
FALLBACK_COVER = "https://mmbiz.qpic.cn/sz_mmbiz_jpg/SfPwFYYicIlhIib2QwV99RsQ5cs79iaK8HNexauOphhGyYBEpnmaoTq2uy6spQfcBrIdmQhOVLy8RC9Zca8zhJnjeibAsqOOn0ebPIuodFejHYw/640?wx_fmt=jpeg"

# ================================================================
#  工具：获取北京时间今天日期
# ================================================================
def get_beijing_date() -> str:
    beijing_tz = timezone(timedelta(hours=8))
    today = datetime.now(beijing_tz)
    return f"{today.year}-{today.month:02d}-{today.day:02d}"

def get_beijing_date_cn() -> str:
    beijing_tz = timezone(timedelta(hours=8))
    today = datetime.now(beijing_tz)
    return f"{today.year}年{today.month}月{today.day}日"

# ================================================================
#  阶段 A 提示词：让 Grok 搜索 120 个账号的原始推文
# ================================================================
def build_prompt_a() -> str:
    return f"""今天是新加坡/北京时间 {get_beijing_date_cn()}。你现在是一台绝对客观、严格遵守底层物理限制的"X 商业情报吸尘器"。

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

# ================================================================
#  阶段 B 提示词：深度编排成公众号日报
# ================================================================
def build_prompt_b() -> str:
    date_str = get_beijing_date()
    return f"""【阶段 B：主编排版与深度解码】

你现在的角色是"AI 圈的顶级观察员与吃瓜课代表"。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【第一步：深度思考与打草稿】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
为了保证日报品质，请先进行深度的"思维链"分析：
1. 挑选最有价值的 10 个话题。
2. 仔细推敲"隐性博弈"和"资本风向标"的底层逻辑。
3. 思考过程你可以畅所欲言，但必须放在最终成稿之前。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【第二步：最终输出规范（严格执行）】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
完成思考后，将所有最终输出内容完整包裹在一个 markdown 代码块中（用 ```markdown 开始，用 ``` 结束）。代码块之外不准说任何多余的话。

代码块内部模板如下（括号内提示请替换为真实内容，不得原样输出）：

```markdown
📡 AI圈极客吃瓜日报 | {date_str}

**🏰 【巨头宫斗】**

**🍉 1. （填入真实话题标题）**
**🗣️ 极客原声态：**
@（原推账号） | （真实姓名） (❤️（赞数）/💬（评论数）)
> "（填入中文译文，绝对不要包含任何URL链接）"
**📝 捕手解码：**
• 📌 增量事实：（填入对该事件的客观事实补充）
• 🧠 隐性博弈：（填入巨头或行业之间的暗战剖析）
• 🎯 资本风向标：（填入对投资或商业趋势的研判）

**🍉 2. （填入下一个话题标题）**
（格式同上）

---

**🇨🇳 【中文圈大瓜】**

**🍉 3. （填入话题标题）**
（以此类推，完成共 10 个话题）
```"""

# ================================================================
#  Markdown → 微信公众号风格 HTML
# ================================================================
def convert_to_wechat_html(raw_text: str) -> str:
    clean = re.sub(r'```[a-zA-Z]*', '', raw_text)
    clean = re.sub(r'```', '', clean)
    clean = re.sub(r'^>\s*', '> ', clean, flags=re.MULTILINE)
    clean = clean.strip()

    lines = clean.split('\n')
    html  = ('<section style="padding:10px 15px;font-family:-apple-system,'
             'BlinkMacSystemFont,\'PingFang SC\',sans-serif;line-height:1.8;'
             'color:#333;font-size:16px;">')

    for i, line in enumerate(lines):
        t = re.sub(r'\*\*', '', line).strip()
        if not t:
            continue
        if i == 0 or t.startswith('📡'):
            html += (f'<p style="font-size:18px;color:#333;margin:5px 0 15px 0;'
                     f'font-weight:bold;text-align:center;">{t}</p>')
        elif re.match(r'^(🏰|🔬|💰|🛠️|🇨🇳|🏭|🧸|🥽|🔮|🎬|⚙️).*【.*】', t):
            html += (f'<div style="height:30px;"></div>'
                     f'<h2 style="font-size:20px;color:#333;margin:25px 0 15px 0;'
                     f'border-left:5px solid #e74c3c;padding-left:12px;font-weight:bold;">{t}</h2>')
        elif t.startswith('🍉'):
            html += (f'<h3 style="font-size:18px;color:#e74c3c;margin:20px 0 12px 0;'
                     f'font-weight:bold;border-bottom:1px solid #f0f0f0;padding-bottom:8px;">{t}</h3>')
        elif t.startswith('🗣') or t.startswith('📝'):
            html += (f'<p style="font-size:16px;font-weight:bold;color:#2c3e50;'
                     f'margin-top:18px;margin-bottom:8px;">{t}</p>')
        elif t.startswith('>'):
            html += (f'<blockquote style="font-size:16px;color:#555;background:#f8f9fa;'
                     f'padding:12px 15px;border-left:4px solid #bdc3c7;margin:8px 0;'
                     f'border-radius:4px;">&ldquo;{t[1:].strip()}&rdquo;</blockquote>')
        else:
            html += f'<p style="font-size:16px;color:#333;margin:8px 0;">{t}</p>'

    html += '</section>'
    return html

# ================================================================
#  Kimi 提炼导读词 + xAI 生成封面图
# ================================================================
def generate_cover(report_text: str) -> tuple:
    if not KIMI_API_KEY or not XAI_API_KEY:
        print("⚠️ KIMI_API_KEY 或 XAI_API_KEY 未配置，使用兜底封面", flush=True)
        return '', FALLBACK_COVER

    safe_text = report_text[:1200]
    prompt = f"""任务：作为顶级AI主编，请阅读下方新闻，找出"最抓马、最具冲突性"的一个事件。

【新闻正文】：
{safe_text}

【严格输出要求】：
只输出一个合法的 JSON 对象，不包含任何分析、问候语或 markdown 标记。格式如下：
{{
  "summary": "100字中文吃瓜导读",
  "image_prompt": "美式漫画风格的英文生图提示词, centered subject, ultra-wide"
}}"""

    try:
        print("正在调用 Kimi 提炼导读词...", flush=True)
        r = requests.post(
            "https://api.moonshot.cn/v1/chat/completions",
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {KIMI_API_KEY}"},
            json={"model": "moonshot-v1-8k",
                  "messages": [{"role": "user", "content": prompt}],
                  "response_format": {"type": "json_object"},
                  "max_tokens": 500},
            timeout=30
        )
        r.raise_for_status()
        raw = r.json()['choices'][0]['message']['content'].strip()
        raw = re.sub(r'<think>[\s\S]*?</think>', '', raw).strip()
        raw = re.sub(r'```json|```', '', raw).strip()
        match = re.search(r'\{[\s\S]*\}', raw)
        if not match:
            raise ValueError(f"Kimi 未返回 JSON：{raw[:100]}")
        parsed       = json.loads(match.group(0))
        summary      = parsed.get('summary', '')
        image_prompt = parsed.get('image_prompt', '')
        if not image_prompt:
            raise ValueError("Kimi 返回 JSON 缺少 image_prompt")
        print("✅ Kimi 提炼成功", flush=True)

        print("正在调用 xAI 生成封面图...", flush=True)
        r2 = requests.post(
            "https://api.x.ai/v1/images/generations",
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {XAI_API_KEY}"},
            json={"model": "aurora", "prompt": image_prompt, "n": 1},
            timeout=45
        )
        r2.raise_for_status()
        image_url = r2.json()['data'][0].get('url', '')
        if not image_url:
            raise ValueError("xAI 未返回图片 URL")
        print("✅ xAI 生图成功", flush=True)
        return summary, image_url

    except Exception as e:
        print(f"⚠️ 生图流程失败，使用兜底封面：{e}", flush=True)
        return '', FALLBACK_COVER

# ================================================================
#  把封面图和导读摘要插入 HTML 顶部
# ================================================================
def assemble_final_html(wechat_html: str, summary: str, cover_url: str) -> str:
    cover_block = (
        f'<div style="margin-bottom:20px;text-align:center;">'
        f'<img src="{cover_url}" alt="封面" style="max-width:100%;height:auto;'
        f'border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.1);display:block;margin:0 auto;"/>'
        f'<p style="font-size:12px;color:#95a5a6;margin-top:8px;">本文头图由 xAI Grok 自动生成</p>'
        f'</div>'
    )
    summary_block = ''
    if summary:
        summary_block = (
            f'<div style="background:#fff8e6;border-left:4px solid #ff9800;'
            f'padding:15px 18px;margin-bottom:30px;border-radius:6px;">'
            f'<p style="margin:0;font-size:14px;color:#444;line-height:1.6;">{summary}</p>'
            f'</div>'
        )
    insert = cover_block + '\n' + summary_block + '\n'
    return re.sub(r'(<section[^>]*>)', r'\1\n' + insert, wechat_html, count=1)

# ================================================================
#  推送到极简云
# ================================================================
def send_to_jijyun(title: str, html_content: str, cover_jpg: str):
    if not JIJYUN_WEBHOOK_URL:
        print("⚠️ JIJYUN_WEBHOOK_URL 未配置，跳过", flush=True)
        return
    payload = {"title": title, "author": AUTHOR,
                "html_content": html_content, "cover_jpg": cover_jpg}
    print(f"正在推送到极简云：{title}", flush=True)
    try:
        resp = requests.post(JIJYUN_WEBHOOK_URL,
                             headers={"Content-Type": "application/json"},
                             json=payload, timeout=30)
        print(f"✅ 极简云推送完成：{resp.status_code} | {resp.text[:150]}", flush=True)
    except Exception as e:
        print(f"❌ 极简云推送失败：{e}", flush=True)

# ================================================================
#  推送到飞书（可选，失败不影响主流程）
# ================================================================
def send_to_feishu(content: str, title: str):
    if not FEISHU_WEBHOOK_URL:
        return
    try:
        payload = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {"title": {"tag": "plain_text", "content": title},
                           "template": "blue"},
                "elements": [{"tag": "markdown", "content": content[:3000]}]
            }
        }
        resp = requests.post(FEISHU_WEBHOOK_URL,
                             headers={"Content-Type": "application/json"},
                             json=payload, timeout=10)
        print(f"✅ 飞书推送：{resp.status_code}", flush=True)
    except Exception as e:
        print(f"⚠️ 飞书推送失败（非致命）：{e}", flush=True)

# ================================================================
#  等待 Grok 回答生成稳定
# ================================================================
def wait_for_stable(page, label: str, stable_target=6, interval=5, max_loops=150):
    print(f"⏳ 等待 {label} 生成完毕...", flush=True)
    last_len, stable = 0, 0
    for i in range(max_loops):
        time.sleep(interval)
        try:
            cur_len = len(page.eval_on_selector("main", "el => el.innerText") or "")
        except Exception:
            cur_len = 0
        if cur_len > 0 and cur_len == last_len:
            stable += 1
            if stable >= stable_target:
                print(f"✅ {label} 已稳定，字数：{cur_len}（第 {i+1} 轮确认）", flush=True)
                return
        else:
            stable = 0
        last_len = cur_len
        if i % 12 == 0:
            print(f"  [{label}] 当前字数：{cur_len}，稳定计数：{stable}/{stable_target}", flush=True)
    print(f"⚠️ {label} 等待超时，强制继续", flush=True)

# ================================================================
#  往 TipTap 输入框注入提示词并提交
# ================================================================
def inject_prompt(page, prompt_text: str, label: str):
    print(f"\n{'='*50}", flush=True)
    print(f"📝 注入{label}提示词", flush=True)
    print(f"{'='*50}", flush=True)
    try:
        input_box = page.wait_for_selector(
            "div.ProseMirror[contenteditable='true']",
            timeout=60000
        )
        input_box.click()
        time.sleep(1)
        page.keyboard.press("Control+a")
        time.sleep(0.3)
        page.keyboard.press("Delete")
        time.sleep(0.5)
        page.keyboard.type(prompt_text)
        time.sleep(1)
        page.keyboard.press("Enter")
        print(f"✅ {label}已提交", flush=True)
    except Exception as e:
        raise Exception(f"注入{label}失败：{e}")

# ================================================================
#  从页面抓取 Grok 最终回答
# ================================================================
def extract_answer(page) -> str:
    try:
        blocks = page.query_selector_all("pre, code")
        if blocks:
            text = blocks[-1].text_content().strip()
            if len(text) > 200:
                print(f"✅ 从 pre/code 块抓取成功，字数：{len(text)}", flush=True)
                return text
    except Exception:
        pass

    for sel in [".prose", "[data-testid='message']",
                "main [class*='prose']", "main [class*='message']"]:
        try:
            els = page.query_selector_all(sel)
            if els:
                text = els[-1].text_content().strip()
                if len(text) > 200:
                    print(f"✅ 从 {sel} 抓取成功，字数：{len(text)}", flush=True)
                    return text
        except Exception:
            continue

    print("⚠️ 使用 main 区域全文作为兜底", flush=True)
    try:
        return page.eval_on_selector("main", "el => el.innerText").strip()
    except Exception as e:
        raise Exception(f"抓取回答失败：{e}")

# ================================================================
#  确保 Grok 4.20 Beta 开关处于开启状态
# ================================================================
def ensure_grok420_enabled(page):
    print("🔍 检查 Grok 4.20 Beta 开关...", flush=True)
    try:
        mode_btn = page.wait_for_selector(
            "button:has-text('快速模式'), button:has-text('Fast'), "
            "button:has-text('专家模式'), button:has-text('Expert'), "
            "button:has-text('Auto'), button:has-text('自动模式')",
            timeout=15000
        )
        mode_btn.click()
        time.sleep(2)

        page.wait_for_selector("button[role='switch']", timeout=8000)
        toggles = page.query_selector_all("button[role='switch']")
        print(f"  找到 {len(toggles)} 个 Toggle", flush=True)

        toggle = None
        for t in toggles:
            parent = t.evaluate(
                "el => el.closest('div') ? el.closest('div').innerText : ''"
            )
            if any(k in parent for k in ["4.2", "4.20", "Beta", "beta"]):
                toggle = t
                break
        if toggle is None and toggles:
            toggle = toggles[-1]

        if toggle:
            state = toggle.get_attribute("data-state") or toggle.get_attribute("aria-checked") or ""
            if state in ("checked", "true"):
                print("✅ Grok 4.20 Beta 已是开启状态", flush=True)
            else:
                toggle.click()
                time.sleep(1)
                print("✅ Grok 4.20 Beta 已开启", flush=True)
        else:
            print("⚠️ 未找到 Toggle，跳过", flush=True)

        page.keyboard.press("Escape")
        time.sleep(1)
    except Exception as e:
        print(f"⚠️ Beta 开关检查失败（继续运行）：{e}", flush=True)
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass

# ================================================================
#  主流程
# ================================================================
def main():
    context_id = BROWSERBASE_CONTEXT_ID
    if not context_id:
        print("❌ 未找到 BROWSERBASE_CONTEXT_ID，请先配置 GitHub Secrets", flush=True)
        return

    print(f"✅ 读取到 Context ID：{context_id}", flush=True)
    client  = Browserbase(api_key=BROWSERBASE_API_KEY)
    browser = None

    try:
        session = client.sessions.create(
            project_id=BROWSERBASE_PROJECT_ID,
            browser_settings={"context": {"id": context_id, "persist": True}}
        )
        print(f"✅ 会话创建成功：{session.id}", flush=True)

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(session.connect_url)
            ctx = browser.contexts[0]
            ctx.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3]});
                window.chrome = {runtime: {}};
            """)
            page = ctx.new_page()

            # Step 1：打开 Grok
            print("\n[Step 1] 打开 Grok...", flush=True)
            for attempt in range(1, 4):
                try:
                    resp = page.goto("https://grok.com/",
                                     wait_until="domcontentloaded", timeout=120000)
                    if resp and resp.status == 200:
                        page.wait_for_load_state("networkidle", timeout=60000)
                        if "Grok" in page.title():
                            print(f"✅ Grok 加载成功：{page.title()}", flush=True)
                            break
                except Exception as e:
                    print(f"  第 {attempt} 次尝试失败：{e}", flush=True)
                    time.sleep(5)

            # Step 2：确认 Grok 4.20 Beta 开启
            print("\n[Step 2] 确认 Grok 4.20 Beta 开启...", flush=True)
            ensure_grok420_enabled(page)

            page.screenshot(path="00_initial.png", full_page=False)
            print("📸 初始截图已保存", flush=True)

            # Step 3：注入阶段 A
            print("\n[Step 3] 阶段 A：120账号数据拉取", flush=True)
            inject_prompt(page, build_prompt_a(), "阶段A")
            time.sleep(5)
            wait_for_stable(page, "阶段A", stable_target=4, interval=3, max_loops=70)
            page.screenshot(path="01_stage_a_done.png", full_page=True)
            print("📸 阶段A完成截图已保存", flush=True)

            # Step 4：注入阶段 B
            print("\n[Step 4] 阶段 B：深度排版编排", flush=True)
            inject_prompt(page, build_prompt_b(), "阶段B")
            time.sleep(5)
            wait_for_stable(page, "阶段B", stable_target=4, interval=3, max_loops=70)
            page.screenshot(path="02_stage_b_done.png", full_page=True)
            print("📸 阶段B完成截图已保存", flush=True)

            # Step 5：抓取回答
            print("\n[Step 5] 抓取 Grok 回答...", flush=True)
            raw_answer = extract_answer(page)
            if not raw_answer or len(raw_answer) < 200:
                raise Exception(f"回答字数异常（{len(raw_answer) if raw_answer else 0}字），请检查截图")
            print(f"✅ 抓取成功，字数：{len(raw_answer)}", flush=True)
            print(f"  预览：{raw_answer[:150]}...", flush=True)

            page.close()
            browser.close()
            browser = None
            print("✅ 浏览器已关闭", flush=True)

        # Step 6：生成标题
        date_str = get_beijing_date()
        title = f"📡 昨夜x上爆出硅谷AI圈大瓜｜{date_str}"
        print(f"\n[Step 6] 标题：{title}", flush=True)

        # Step 7：Markdown → 微信 HTML
        print("\n[Step 7] 转换为微信公众号 HTML...", flush=True)
        wechat_html = convert_to_wechat_html(raw_answer)
        print(f"✅ HTML 生成完毕，字数：{len(wechat_html)}", flush=True)

        # Step 8：Kimi 提炼 + xAI 生图
        print("\n[Step 8] Kimi 提炼 + xAI 生成封面图...", flush=True)
        summary, cover_url = generate_cover(raw_answer)

        # Step 9：组装最终 HTML
        print("\n[Step 9] 组装最终 HTML...", flush=True)
        final_html = assemble_final_html(wechat_html, summary, cover_url)
        print(f"✅ 最终 HTML 字数：{len(final_html)}", flush=True)

        # Step 10：推送飞书
        print("\n[Step 10] 推送到飞书...", flush=True)
        send_to_feishu(raw_answer[:3000], title)

        # Step 11：推送极简云
        print("\n[Step 11] 推送到极简云...", flush=True)
        send_to_jijyun(title, final_html, cover_url)

        print("\n🎉 全部流程完成！", flush=True)

    except Exception as e:
        print(f"\n❌ 任务执行失败：{e}", flush=True)
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        print("脚本执行完成", flush=True)

if __name__ == "__main__":
    main()
