import os, re, json, random, datetime, urllib.parse, requests
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, FollowEvent, TextMessage,
    TextSendMessage, FlexSendMessage, BubbleContainer, CarouselContainer,
    BoxComponent, TextComponent, ButtonComponent, URIAction, MessageAction
)

app = FastAPI()
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")

# ⚠️ 1. 請填入「韓系穿搭與可愛選品導購變現資料庫」的 Google Apps Script /exec 網址
GOOGLE_SHEET_API = "https://script.google.com/macros/s/AKfycbwYQCTZ_PrDnQztXoW11YxtMesSpe30d4c8h7d2P5vST3ZLCnHgzh04kV9UuLhvJyf4/exec"
# ⚠️ 2. 請填入這個穿搭機器人的 LINE 官方帳號 ID（包含 @ 符號，例如 @123abcde）
LINE_BOT_BASIC_ID = "@037omyph"
# ⚠️ 3. 請填入這個穿搭機器人的 Render 公開網址（結尾不要加斜線）
RENDER_BASE_URL = "https://onrender.com"
# ⚠️ 4. 請填入您的主賣場／蝦皮分潤總館／Notion 選品櫥窗網址（所有商品按鈕會自動導向您的分潤連結！）
MAIN_SHOP_URL = "https://shopee.tw"

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

CUTE_SHOP_ITEMS = [
    {"sku": "W01", "cat": "韓系顯瘦上衣", "badge": "🔥 本週爆賣 #1", "name": "軟糯奶杏色麻花針織開襟外套", "price": "$399", "orig": "$690", "desc": "微寬鬆落肩版型超遮副乳與蝴蝶袖，早晚溫差搭這件溫柔感滿分！", "url": MAIN_SHOP_URL},
    {"sku": "W02", "cat": "顯瘦神褲裙裝", "badge": "✨ 梨形身材救星", "name": "高腰垂墜感西裝闊腿長褲（附腰帶）", "price": "$450", "orig": "$780", "desc": "視覺腿長瞬間 +10cm！完美修飾假胯寬，上班約會都能穿。", "url": MAIN_SHOP_URL},
    {"sku": "W03", "cat": "可愛療癒小物", "badge": "🧸 閨蜜湊單熱銷", "name": "日系毛絨小熊雲朵手提化妝包", "price": "$169", "orig": "$299", "desc": "超軟萌泰迪絨毛手感，放補妝氣墊、護手霜與行動電源剛剛好！", "url": MAIN_SHOP_URL},
    {"sku": "W04", "cat": "可愛療癒小物", "badge": "💖 辦公室治癒系", "name": "奶油白胖胖貓爪保溫隨行咖啡杯 500ml", "price": "$289", "orig": "$490", "desc": "316 不鏽鋼陶瓷內膽，買超商咖啡現折 5 元，放辦公桌超吸睛！", "url": MAIN_SHOP_URL},
    {"sku": "W05", "cat": "韓系顯瘦上衣", "badge": "🌸 約會純欲風", "name": "法式方領鎖骨顯瘦坑條針織上衣", "price": "$299", "orig": "$520", "desc": "露出最纖細的鎖骨線條，單穿或當大衣內搭都超級顯白！", "url": MAIN_SHOP_URL},
    {"sku": "W06", "cat": "可愛配飾包包", "badge": "🎀 韓妞氛圍感", "name": "復古燈芯絨百搭貝雷帽＋珍珠髮夾組", "price": "$199", "orig": "$350", "desc": "沒洗頭也能 3 秒時髦出門，圓臉戴起來秒變精緻小V臉！", "url": MAIN_SHOP_URL}
]
def get_ootd_weather():
    try:
        u = "https://open-meteo.com"
        j = requests.get(u, timeout=6).json()
        cur_t = round(j.get("current", {}).get("temperature_2m", 21))
        tmax = round(j.get("daily", {}).get("temperature_2m_max", [24])[0])
        tmin = round(j.get("daily", {}).get("temperature_2m_min", [18])[0])
        if cur_t <= 17:
            look = "軟糯毛絨外套 ＋ 內搭發熱衣 ＋ 高腰顯瘦長褲"
        elif cur_t <= 23:
            look = "奶杏色針織開襟衫 ＋ 法式方領上衣 ＋ 垂墜闊腿褲"
        else:
            look = "法式透氣雪紡上衣 ＋ 高腰A字顯瘦短裙 ＋ 雲朵包"
        return {"temp": cur_t, "range": f"{tmin}°C ~ {tmax}°C", "look": look}
    except Exception:
        return {"temp": 21, "range": "18°C ~ 24°C", "look": "奶杏色針織開襟衫 ＋ 高腰垂墜西裝褲 ＋ 雲朵包"}

def call_sheet(payload: dict):
    try:
        r = requests.post(GOOGLE_SHEET_API, json=payload, timeout=12)
        return r.json()
    except Exception:
        return {}

def get_user_name(uid: str):
    try:
        return line_bot_api.get_profile(uid).display_name
    except Exception:
        return "仙女買家"

@app.get("/")
def root():
    return {"status": "Online", "service": "Taiwan OOTD & Cute Boutique Pro App 3.0"}

@app.post("/api/shop_add")
async def web_shop_add(
    cat: str = Form("韓系顯瘦上衣"),
    badge: str = Form("✨ 店長新上架"),
    name: str = Form("韓系溫柔風針織衫"),
    price: str = Form("$399"),
    orig: str = Form("$690"),
    desc: str = Form("超顯白顯瘦版型，限時優惠中！"),
    url: str = Form("")
):
    sku = f"W{len(CUTE_SHOP_ITEMS) + 1:02d}"
    CUTE_SHOP_ITEMS.insert(0, {
        "sku": sku,
        "cat": cat.strip() or "韓系顯瘦上衣",
        "badge": badge.strip() or "✨ 店長新上架",
        "name": name.strip() or "韓系新品",
        "price": price.strip() or "$399",
        "orig": orig.strip() or "$690",
        "desc": desc.strip() or "精緻女裝與可愛小物嚴選",
        "url": url.strip() or MAIN_SHOP_URL
    })
    return RedirectResponse(url="/ootd_app?msg=added", status_code=303)

@app.post("/api/wish_add")
async def web_wish_add(item_name: str = Form(...), price_tag: str = Form("$399")):
    wid = f"W{int(datetime.datetime.utcnow().timestamp() * 1000)}"
    call_sheet({"action": "add_wish", "wish_id": wid, "user_id": "web_girl", "user_name": "櫥窗買家", "item_name": item_name, "price_tag": price_tag, "note": "App心動收藏"})
    return {"status": "ok"}
@app.get("/ootd_app", response_class=HTMLResponse)
def ootd_cute_boutique_app(msg: str = ""):
    S = chr(47)
    items_json = json.dumps(CUTE_SHOP_ITEMS, ensure_ascii=False)
    w_info = get_ootd_weather()
    app_url_enc = urllib.parse.quote(f"{RENDER_BASE_URL}/ootd_app")
    toast_html = '<div class="toast">✨ 店長新品已成功上架至精品選品櫥窗囉！</div>' if msg == "added" else ""

    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no"/>
    <title>👗 每日氣溫穿搭 ＆ 韓系可愛選品館</title>
    <style>
      * {{ box-sizing: border-box; -webkit-tap-highlight-color: transparent; }}
      body {{ margin: 0; padding: 0 0 92px 0; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif; background: radial-gradient(circle at top right, #3D2430, #191216 58%); color: #FFF5F7; min-height: 100vh; }}
      .topbar {{ background: rgba(29, 19, 24, 0.9); backdrop-filter: blur(16px); padding: 15px 18px; position: sticky; top: 0; z-index: 100; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(251, 113, 133, 0.25); }}
      .topbar h1 {{ margin: 0; font-size: 16px; font-weight: 800; color: #FFE4E6; letter-spacing: 0.5px; }}
      .badge-vip {{ font-size: 11px; background: linear-gradient(135deg, #FB7185, #E11D48); color: #fff; padding: 4px 10px; border-radius: 20px; font-weight: 800; }}
      .wrap {{ max-width: 540px; margin: 0 auto; padding: 14px; }}
      .toast {{ background: rgba(251, 113, 133, 0.22); border: 1px solid #FB7185; color: #FFE4E6; padding: 12px; border-radius: 14px; font-size: 13px; font-weight: 700; margin-bottom: 12px; text-align: center; }}
      .ootd-hero {{ background: linear-gradient(135deg, rgba(251, 113, 133, 0.18), rgba(244, 114, 182, 0.12)); border: 1px solid rgba(251, 113, 133, 0.32); border-radius: 22px; padding: 16px; margin-bottom: 14px; }}
      .chips {{ display: flex; gap: 8px; overflow-x: auto; padding-bottom: 12px; scrollbar-width: none; }}
      .chip {{ white-space: nowrap; background: rgba(255,255,255,0.07); border: 1px solid rgba(255,228,230,0.16); color: #FECDD3; padding: 8px 14px; border-radius: 20px; font-size: 12px; font-weight: 700; cursor: pointer; }}
      .chip.active {{ background: linear-gradient(135deg, #FB7185, #E11D48); border-color: #FDA4AF; color: #fff; box-shadow: 0 4px 14px rgba(225, 29, 72, 0.4); }}
      .shop-card {{ background: rgba(36, 24, 30, 0.85); backdrop-filter: blur(16px); border: 1px solid rgba(255,228,230,0.14); border-radius: 22px; padding: 16px; margin-bottom: 14px; box-shadow: 0 10px 28px rgba(0,0,0,0.4); }}
      .price-row {{ display: flex; align-items: baseline; gap: 8px; margin-top: 8px; }}
      .price-now {{ font-size: 22px; font-weight: 900; color: #FB7185; }}
      .price-orig {{ font-size: 13px; color: #9CA3AF; text-decoration: line-through; }}
      .btn-row {{ display: flex; gap: 8px; margin-top: 12px; }}
      .btn {{ flex: 1; text-align: center; text-decoration: none; padding: 11px 6px; border-radius: 14px; font-size: 13px; font-weight: 800; cursor: pointer; border: none; color: #fff; }}
      .btn-rose {{ background: linear-gradient(135deg, #FB7185, #E11D48); box-shadow: 0 4px 12px rgba(225, 29, 72, 0.35); }}
      .btn-gold {{ background: linear-gradient(135deg, #F59E0B, #D97706); }}
      .btn-glass {{ background: rgba(255,255,255,0.1); color: #FFE4E6; border: 1px solid rgba(255,228,230,0.2); }}
      .field {{ width: 100%; background: rgba(20, 14, 17, 0.88); border: 1px solid rgba(255,228,230,0.22); color: #fff; padding: 12px; border-radius: 12px; font-size: 14px; margin-top: 8px; }}
      .page {{ display: none; }}
      .page.active {{ display: block; }}
      .tabbar {{ position: fixed; bottom: 0; left: 0; right: 0; background: rgba(25, 16, 21, 0.96); backdrop-filter: blur(18px); border-top: 1px solid rgba(251, 113, 133, 0.22); display: flex; padding: 8px 8px 14px; z-index: 120; }}
      .tab {{ flex: 1; text-align: center; color: #FDA4AF; font-size: 12px; font-weight: 800; cursor: pointer; padding-top: 4px; }}
      .tab.active {{ color: #FFF1F2; }}
      .tab-cta {{ background: linear-gradient(135deg, #FB7185, #E11D48); color: #fff; padding: 8px 12px; border-radius: 20px; font-size: 12px; }}
    </style></head><body>
    <div class="topbar"><h1>👗 韓系穿搭靈感 ＆ 可愛選品館</h1><span class="badge-vip">仙女 VIP 專享</span></div>
    <div id="page-shop" class="page active"><div class="wrap">
      {toast_html}
      <div class="ootd-hero">
        <div style="font-size:12px;color:#FDA4AF;font-weight:800;">🌡️ 今日即時氣溫 {w_info['temp']}°C（{w_info['range']}）</div>
        <div style="font-size:16px;font-weight:900;color:#FFF1F2;margin-top:4px;">👗 今日顯瘦穿搭：{w_info['look']}</div>
        <div class="btn-row" style="margin-top:10px;">
          <button type="button" class="btn btn-rose" onclick="drawLuckyBox()">🎰 抽今日幸運色＆盲盒優惠</button>
        </div>
        <div id="lucky-res" style="display:none;margin-top:10px;background:rgba(20,14,17,0.75);padding:10px;border-radius:12px;font-size:13px;color:#FFE4E6;border:1px dashed #FB7185;"></div>
      </div>

      <div class="chips">
        <div class="chip active" onclick="filterCat('all', this)">✨ 全部爆款選品</div>
        <div class="chip" onclick="filterCat('韓系顯瘦上衣', this)">👚 韓系顯瘦上衣</div>
        <div class="chip" onclick="filterCat('顯瘦神褲裙裝', this)">👖 顯瘦神褲裙裝</div>
        <div class="chip" onclick="filterCat('可愛療癒小物', this)">🧸 可愛療癒小物</div>
        <div class="chip" onclick="filterCat('可愛配飾包包', this)">🎀 配飾包包</div>
      </div>
      <div id="shop-box"></div>
    </div></div>

    <div id="page-tone" class="page"><div class="wrap">
      <div class="shop-card">
        <div style="font-size:17px;font-weight:900;color:#FDA4AF;margin-bottom:4px;">🎨 AI 膚色顯白 ＆ 身形修飾穿搭診斷</div>
        <div style="font-size:12px;color:#FECDD3;">點選您的膚色與身形，立刻獲得專屬顯瘦配色秘訣：</div>
        <div class="chips" style="margin-top:10px;padding-bottom:4px;">
          <div class="chip" onclick="showTone('warm')">🍑 暖黃皮（亞洲常見）</div>
          <div class="chip" onclick="showTone('cool')">❄️ 冷白皮仙女</div>
          <div class="chip" onclick="showTone('pear')">🍐 梨形身材（遮假胯寬）</div>
          <div class="chip" onclick="showTone('petite')">🌸 小個子增高（158以下）</div>
        </div>
        <div id="tone-res" style="background:rgba(20,14,17,0.8);padding:14px;border-radius:14px;margin-top:10px;font-size:13px;line-height:1.7;color:#FFF1F2;border-left:3px solid #FB7185;">
          👆 點擊上方按鈕，立即解鎖您的專屬顯白顯瘦穿搭公式！
        </div>
      </div>
    </div></div>

    <div id="page-admin" class="page"><div class="wrap">
      <div class="shop-card">
        <div style="font-size:17px;font-weight:900;color:#FDA4AF;margin-bottom:4px;">🛍️ 店長快速上架爆款女裝／可愛小物</div>
        <div style="font-size:12px;color:#FECDD3;">免改程式碼，貼上您的蝦皮／賣場分潤連結即可立即上架：</div>
        <form action="{S}api{S}shop_add" method="post">
          <select name="cat" class="field">
            <option value="韓系顯瘦上衣">👚 韓系顯瘦上衣</option>
            <option value="顯瘦神褲裙裝">👖 顯瘦神褲裙裝</option>
            <option value="可愛療癒小物">🧸 可愛療癒小物</option>
            <option value="可愛配飾包包">🎀 可愛配飾包包</option>
          </select>
          <input name="badge" class="field" placeholder="🏷️ 吸睛標籤（如：🔥 限時免運 #1 或 🧸 閨蜜湊單）" value="🔥 店長強推爆款"/>
          <input name="name" class="field" placeholder="👗 商品名稱（如：韓系奶杏色針織外套）" required/>
          <input name="price" class="field" placeholder="💰 優惠價（如：$399）" value="$399" required/>
          <input name="orig" class="field" placeholder="💸 原價劃線價（如：$690）" value="$690"/>
          <textarea name="desc" class="field" rows="2" placeholder="✨ 推坑賣點描述（如：超遮副乳與蝴蝶袖，溫柔感滿分！）" required></textarea>
          <input name="url" class="field" placeholder="🔗 貼上您的蝦皮／MOMO／賣場分潤購買網址" required/>
          <button type="submit" class="btn btn-rose" style="width:100%;margin-top:12px;padding:14px;">🚀 立即上架至選品櫥窗</button>
        </form>
      </div>
    </div></div>

    <div class="tabbar">
      <div class="tab active" onclick="switchTab('shop', this)">🛍️ 精品選品櫥窗</div>
      <div class="tab" onclick="switchTab('tone', this)">🎨 顯白顯瘦診斷</div>
      <div class="tab" onclick="switchTab('admin', this)"><span class="tab-cta">➕ 店長上架</span></div>
    </div>

    <script>
      const ITEMS = {items_json};
      const NL = String.fromCharCode(10);
      let curCat = 'all';

      function filterCat(c, el) {{
        curCat = c;
        document.querySelectorAll('#page-shop .chips .chip').forEach(x => x.classList.remove('active'));
        el.classList.add('active');
        renderShop();
      }}

      function renderShop() {{
        const list = ITEMS.filter(x => curCat === 'all' || x.cat === curCat);
        document.getElementById('shop-box').innerHTML = list.map((x, idx) => {{
          const shareTxt = '💖 姐妹快看這件超可愛又顯瘦！' + NL + '【' + x.name + '】只要 ' + x.price + '！' + NL + '👉 一起逛逛看：' + decodeURIComponent('{app_url_enc}');
          const lineShareU = `https:{S}{S}line.me{S}R{S}share?text=${{encodeURIComponent(shareTxt)}}`;
          return `<div class="shop-card">
            <span style="font-size:11px;font-weight:800;background:rgba(251,113,133,0.2);color:#FDA4AF;padding:4px 10px;border-radius:10px;">${{x.badge}} · ${{x.cat}}</span>
            <div style="font-size:18px;font-weight:900;color:#FFF1F2;margin-top:8px;">${{x.name}}</div>
            <div style="font-size:13px;color:#FECDD3;line-height:1.6;margin-top:6px;">${{x.desc}}</div>
            <div class="price-row"><span class="price-now">${{x.price}}</span><span class="price-orig">原價 ${{x.orig}}</span></div>
            <div class="btn-row">
              <button type="button" class="btn btn-glass" onclick="saveWish('${{x.name}}','${{x.price}}',this)">💖 收藏許願</button>
              <a class="btn btn-glass" href="${{lineShareU}}">💌 問閨蜜</a>
              <a class="btn btn-rose" href="${{x.url}}" target="_blank">🛍️ 搶購同款</a>
            </div>
          </div>`;
        }}).join('');
      }}

      async function saveWish(name, price, btn) {{
        btn.innerText = '✅ 已加入許願';
        const fd = new FormData();
        fd.append('item_name', name);
        fd.append('price_tag', price);
        await fetch('{S}api{S}wish_add', {{method:'POST', body: fd}});
      }}

      function drawLuckyBox() {{
        const prizes = [
          '🌸 今日幸運色：【奶杏燕麥色】！穿上軟糯針織衫，今日貴人運與桃花運大爆發！',
          '🧸 今日幸運小物：【泰迪熊雲朵化妝包】！帶上可愛小物出門，一整天心情都療癒滿分！',
          '🎀 今日幸運色：【蜜桃玫瑰粉】！搭配珍珠耳飾或貝雷帽，氣色瞬間白兩階！',
          '☕ 今日幸運搭配：【法式方領上衣 ＋ 貓爪保溫杯】！優雅又省錢的辦公室女神標配！'
        ];
        const box = document.getElementById('lucky-res');
        box.style.display = 'block';
        box.innerText = prizes[Math.floor(Math.random() * prizes.length)];
      }}

      function showTone(t) {{
        const map = {{
          'warm': '🍑【暖黃皮顯白秘訣】首選「奶杏色、燕麥白、霧霾藍、焦糖棕」，避開螢光粉與正橘色，臉部氣色立刻提亮兩階！',
          'cool': '❄️【冷白皮仙女秘訣】大膽駕馭「蜜桃粉、薰衣草紫、酒紅色、純白色」，自帶韓劇女主角高級濾鏡！',
          'pear': '🍐【梨形身材遮胯公式】上身選「法式方領／短版針織衫」強調腰線，下身搭配「高腰垂墜西裝闊腿褲」，瞬間遮住假胯寬！',
          'petite': '🌸【158以下小個子增高公式】把握「上短下長」黃金比例！短版開襟衫 ＋ 高腰A字短裙，視覺腿長立刻 +10cm！'
        }};
        document.getElementById('tone-res').innerText = map[t] || '';
      }}

      function switchTab(t, el) {{ document.querySelectorAll('.page').forEach(x => x.classList.remove('active')); document.querySelectorAll('.tab').forEach(x => x.classList.remove('active')); document.getElementById('page-' + t).classList.add('active'); el.classList.add('active'); }}
      renderShop();
    </script></body></html>"""
    return HTMLResponse(content=html)
def make_ootd_shop_card():
    S = chr(47)
    app_uri = f"{RENDER_BASE_URL}/ootd_app?openExternalBrowser=1"
    app_url_enc = urllib.parse.quote(f"{RENDER_BASE_URL}/ootd_app")
    w_info = get_ootd_weather()
    hot_item = CUTE_SHOP_ITEMS[0] if len(CUTE_SHOP_ITEMS) > 0 else {"name": "韓系奶杏色針織外套", "price": "$399", "url": MAIN_SHOP_URL}

    share_msg = f"👗【每日氣溫顯瘦穿搭 ＆ 韓系可愛選品館】\n今天氣溫 {w_info['temp']}°C，推薦穿搭：{w_info['look']}\n🧸 還有超多韓系顯瘦女裝與療癒可愛小物限時優惠中！\n📲 免費測顯白膚色與逛選品櫥窗：\nhttps:{S}{S}line.me{S}R{S}ti{S}p{S}{LINE_BOT_BASIC_ID}"
    share_uri = f"https:{S}{S}line.me{S}R{S}share?text={urllib.parse.quote(share_msg)}"
    threads_uri = f"https:{S}{S}www.threads.net{S}intent{S}post?text={urllib.parse.quote(share_msg + ' #每日穿搭 #韓系女裝 #可愛小物')}"

    bubble_1 = BubbleContainer(
        size="mega",
        header=BoxComponent(layout="vertical", background_color="#1D1318", padding_all="16px", contents=[
            TextComponent(text="👗 每日氣溫穿搭 ＆ 韓系可愛選品館", weight="bold", size="md", color="#FFE4E6", wrap=True),
            TextComponent(text="AI 顯白顯瘦穿搭公式 · 爆款女裝 · 療癒可愛小物", size="xs", color="#FDA4AF", weight="bold", wrap=True, margin="xs")
        ]),
        body=BoxComponent(layout="vertical", spacing="sm", background_color="#FFF5F7", contents=[
            BoxComponent(layout="horizontal", spacing="sm", contents=[
                BoxComponent(layout="vertical", background_color="#3D2430", corner_radius="12px", padding_all="10px", align_items="center", contents=[
                    TextComponent(text="🌡️ 今日即時氣溫", size="xxs", color="#FDA4AF", weight="bold"),
                    TextComponent(text=f"{w_info['temp']}°C ({w_info['range']})", size="xs", color="#FFFFFF", weight="bold", margin="xs")
                ]),
                BoxComponent(layout="vertical", background_color="#3D2430", corner_radius="12px", padding_all="10px", align_items="center", contents=[
                    TextComponent(text="🔥 今日爆賣單品", size="xxs", color="#FBBF24", weight="bold"),
                    TextComponent(text=f"{hot_item['price']} 限時優惠", size="xs", color="#FFFFFF", weight="bold", margin="xs")
                ])
            ]),
            BoxComponent(layout="vertical", background_color="#FFE4E6", corner_radius="14px", padding_all="12px", contents=[
                TextComponent(text="✨ 今日顯瘦穿搭靈感：", size="xs", color="#BE123C", weight="bold"),
                TextComponent(text=w_info["look"], size="xs", color="#1F2937", wrap=True, margin="xs")
            ])
        ]),
        footer=BoxComponent(layout="vertical", spacing="sm", background_color="#FFF5F7", contents=[
            ButtonComponent(style="primary", color="#E11D48", height="sm", action=URIAction(label="🛍️ 開啟韓系女裝 ＆ 可愛選品櫥窗 App", uri=app_uri)),
            BoxComponent(layout="horizontal", spacing="sm", contents=[
                ButtonComponent(style="primary", color="#FB7185", height="sm", action=URIAction(label="🔥 搶購今日爆款", uri=hot_item["url"])),
                ButtonComponent(style="secondary", height="sm", action=MessageAction(label="🎨 測顯白膚色", text="顯白診斷"))
            ]),
            BoxComponent(layout="horizontal", spacing="sm", contents=[
                ButtonComponent(style="secondary", height="sm", action=MessageAction(label="🧸 可愛小物推薦", text="可愛小物")),
                ButtonComponent(style="primary", color="#D97706", height="sm", action=MessageAction(label="🎰 抽今日幸運色", text="抽幸運色"))
            ])
        ])
    )

    bubble_2 = BubbleContainer(
        size="mega",
        header=BoxComponent(layout="vertical", background_color="#1D1318", padding_all="16px", contents=[
            TextComponent(text="💌 閨蜜群組湊免運 ＆ 賣場直達", weight="bold", size="md", color="#FFE4E6", wrap=True),
            TextComponent(text="一鍵轉傳給姐妹挑穿搭、逛主賣場全館折扣", size="xs", color="#FDA4AF", weight="bold", wrap=True, margin="xs")
        ]),
        body=BoxComponent(layout="vertical", spacing="xs", background_color="#FFF5F7", contents=[
            TextComponent(text="👈 向左滑動返回「今日氣溫穿搭與精品櫥窗」", size="xxs", color="#9F1239", weight="bold")
        ]),
        footer=BoxComponent(layout="vertical", spacing="sm", background_color="#FFF5F7", contents=[
            ButtonComponent(style="primary", color="#E11D48", height="sm", action=URIAction(label="🏪 前往官方全館賣場（領滿額折價券）", uri=MAIN_SHOP_URL)),
            BoxComponent(layout="horizontal", spacing="sm", contents=[
                ButtonComponent(style="primary", color="#10B981", height="sm", action=URIAction(label="💌 傳LINE問閨蜜", uri=share_uri)),
                ButtonComponent(style="primary", color="#1A1B1E", height="sm", action=URIAction(label="🧵 發脆Threads", uri=threads_uri))
            ])
        ])
    )
    return CarouselContainer(contents=[bubble_1, bubble_2])
@app.post("/callback")
async def callback(request: Request):
    sig = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    try:
        handler.handle(body.decode("utf-8"), sig)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return "OK"

@handler.add(FollowEvent)
def on_follow(event):
    card = make_ootd_shop_card()
    line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="👗 每日氣溫穿搭 ＆ 韓系可愛選品館已啟動", contents=card))

@handler.add(MessageEvent, message=TextMessage)
def on_text(event):
    uid = event.source.user_id
    uname = get_user_name(uid)
    txt = event.message.text.strip()

    try:
        # 1. AI 顯白膚色與身形穿搭診斷
        if txt == "顯白診斷":
            app_uri = f"{RENDER_BASE_URL}/ootd_app?openExternalBrowser=1"
            msg = (
                "🎨【AI 膚色顯白 ＆ 顯瘦穿搭公式】\n"
                "🍑 暖黃皮（亞洲常見）：首選「奶杏色、燕麥白、霧霾藍」，臉部氣色立刻提亮兩階！\n"
                "❄️ 冷白皮仙女：大膽駕馭「蜜桃玫瑰粉、薰衣草紫、純白色」，自帶韓劇女主濾鏡！\n"
                "🍐 梨形身材遮胯：法式方領短版上衣 ＋ 高腰垂墜西裝闊腿褲，視覺腿長 +10cm！\n"
                f"🛍️ 點擊開啟選品櫥窗挑選顯白同款：\n{app_uri}"
            )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
            return

        # 2. 可愛療癒小物推薦導購
        if txt == "可愛小物":
            cute_list = [x for x in CUTE_SHOP_ITEMS if "可愛" in x.get("cat", "")]
            if not cute_list:
                cute_list = CUTE_SHOP_ITEMS[:3]
            lines = ["🧸【本週閨蜜瘋搶・可愛療癒小物 TOP 精選】"]
            for it in cute_list[:3]:
                lines.append(f"\n• {it['badge']} {it['name']}（優惠 {it['price']}）\n  ✨ {it['desc']}")
            lines.append(f"\n🛍️ 立即前往官方賣場搶購免運優惠：\n{MAIN_SHOP_URL}")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="\n".join(lines)))
            return

        # 3. 今日幸運色＆盲盒抽獎
        if txt == "抽幸運色":
            prizes = [
                "🌸 今日幸運色：【奶杏燕麥色】！穿上軟糯針織衫，今日貴人運與桃花運大爆發！",
                "🧸 今日幸運小物：【泰迪熊雲朵化妝包】！帶上可愛小物出門，一整天心情都療癒滿分！",
                "🎀 今日幸運色：【蜜桃玫瑰粉】！搭配珍珠耳飾或貝雷帽，氣色瞬間白兩階！",
                "☕ 今日幸運搭配：【法式方領上衣 ＋ 貓爪保溫杯】！優雅又省錢的辦公室女神標配！"
            ]
            pick = random.choice(prizes)
            app_uri = f"{RENDER_BASE_URL}/ootd_app?openExternalBrowser=1"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🎰 {pick}\n\n🛍️ 點擊逛逛今日幸運色同款女裝與小物：\n{app_uri}"))
            return

        # 4. 預設顯示奶油蜜桃玫瑰金雙卡輪播主畫面
        card = make_ootd_shop_card()
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="👗 每日氣溫穿搭 ＆ 韓系可愛選品館", contents=card))
    except Exception as e:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"👗 系統小提示：{str(e)[:60]}（請輸入「穿搭」刷新畫面）"))
