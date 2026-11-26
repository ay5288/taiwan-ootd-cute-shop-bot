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
RENDER_BASE_URL = "https://taiwan-ootd-cute-shop-bot.onrender.com"
# ⚠️ 4. 請填入您的主賣場／蝦皮分潤總館／Notion 選品櫥窗網址（所有商品按鈕會自動導向您的分潤連結！）
MAIN_SHOP_URL = "https://shopee.tw"

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

CUTE_SHOP_ITEMS = [
    {"sku": "W01", "cat": "韓系顯瘦上衣", "badge": "🔥 本週爆賣 #1", "name": "軟糯奶杏色麻花針織開襟外套", "price": "$399", "orig": "$690", "img": "https://unsplash.com", "desc": "微寬鬆落肩版型超遮副乳與蝴蝶袖，早晚溫差搭這件溫柔感滿分！", "url": MAIN_SHOP_URL},
    {"sku": "W02", "cat": "顯瘦神褲裙裝", "badge": "✨ 梨形身材救星", "name": "高腰垂墜感西裝闊腿長褲（附腰帶）", "price": "$450", "orig": "$780", "img": "https://unsplash.com", "desc": "視覺腿長瞬間 +10cm！完美修飾假胯寬，上班約會都能穿。", "url": MAIN_SHOP_URL},
    {"sku": "W03", "cat": "可愛療癒小物", "badge": "🧸 閨蜜湊單熱銷", "name": "日系毛絨小熊雲朵手提化妝包", "price": "$169", "orig": "$299", "img": "https://unsplash.com", "desc": "超軟萌泰迪絨毛手感，放補妝氣墊、護手霜與行動電源剛剛好！", "url": MAIN_SHOP_URL},
    {"sku": "W04", "cat": "可愛療癒小物", "badge": "💖 辦公室治癒系", "name": "奶油白胖胖貓爪保溫隨行咖啡杯 500ml", "price": "$289", "orig": "$490", "img": "https://unsplash.com", "desc": "316 不鏽鋼陶瓷內膽，買超商咖啡現折 5 元，放辦公桌超吸睛！", "url": MAIN_SHOP_URL},
    {"sku": "B01", "cat": "整套優惠組", "badge": "👑 整套帶走省$350", "name": "【約會必勝三件套】奶杏針織外套＋高腰闊腿褲＋小熊化妝包", "price": "$899", "orig": "$1,249", "img": "https://unsplash.com", "desc": "整套幫你配到好！免煩惱上下身配色，整組帶走再享免運優惠！", "url": MAIN_SHOP_URL},
    {"sku": "W05", "cat": "韓系顯瘦上衣", "badge": "🌸 約會純欲風", "name": "法式方領鎖骨顯瘦坑條針織上衣", "price": "$299", "orig": "$520", "img": "https://unsplash.com", "desc": "露出最纖細的鎖骨線條，單穿或當大衣內搭都超級顯白！", "url": MAIN_SHOP_URL},
    {"sku": "W06", "cat": "可愛配飾包包", "badge": "🎀 韓妞氛圍感", "name": "復古燈芯絨百搭貝雷帽＋珍珠髮夾組", "price": "$199", "orig": "$350", "img": "https://unsplash.com", "desc": "沒洗頭也能 3 秒時髦出門，圓臉戴起來秒變精緻小V臉！", "url": MAIN_SHOP_URL}
]
def get_ootd_weather():
    try:
        u = "https://open-meteo.com"
        j = requests.get(u, timeout=6).json()
        cur_t = round(float(j.get("current", {}).get("temperature_2m", 21)))
        tmax = round(float(next(iter(j.get("daily", {}).get("temperature_2m_max") or []), 24)))
        tmin = round(float(next(iter(j.get("daily", {}).get("temperature_2m_min") or []), 18)))
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
    return {"status": "Online", "service": "Taiwan OOTD & Cute Boutique Pro App 6.0"}

@app.post("/api/shop_add")
async def web_shop_add(
    cat: str = Form("韓系顯瘦上衣"),
    badge: str = Form("✨ 店長新上架"),
    name: str = Form("韓系溫柔風針織衫"),
    price: str = Form("$399"),
    orig: str = Form("$690"),
    img: str = Form(""),
    desc: str = Form("超顯白顯瘦版型，限時優惠中！"),
    url: str = Form("")
):
    sku = f"W{len(CUTE_SHOP_ITEMS) + 1:02d}"
    default_img = "https://unsplash.com"
    CUTE_SHOP_ITEMS.insert(0, {
        "sku": sku,
        "cat": cat.strip() or "韓系顯瘦上衣",
        "badge": badge.strip() or "✨ 店長新上架",
        "name": name.strip() or "韓系新品",
        "price": price.strip() or "$399",
        "orig": orig.strip() or "$690",
        "img": img.strip() if img.strip().startswith("http") else default_img,
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
    toast_html = '<div class="toast">✨ 店長新品與美照已成功上架至精品選品櫥窗囉！</div>' if msg == "added" else ""

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
      .prod-img {{ width: 100%; height: 215px; object-fit: cover; border-radius: 16px; margin-bottom: 12px; border: 1px solid rgba(255,228,230,0.18); display: block; }}
      .price-row {{ display: flex; align-items: baseline; gap: 8px; margin-top: 8px; }}
      .price-now {{ font-size: 22px; font-weight: 900; color: #FB7185; }}
      .price-orig {{ font-size: 13px; color: #9CA3AF; text-decoration: line-through; }}
      .btn-row {{ display: flex; gap: 8px; margin-top: 12px; }}
      .btn {{ flex: 1; text-align: center; text-decoration: none; padding: 11px 6px; border-radius: 14px; font-size: 13px; font-weight: 800; cursor: pointer; border: none; color: #fff; }}
      .btn-rose {{ background: linear-gradient(135deg, #FB7185, #E11D48); box-shadow: 0 4px 12px rgba(225, 29, 72, 0.35); }}
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
      <div id="live-ticker" style="background:rgba(251,113,133,0.14);border:1px solid rgba(251,113,133,0.3);color:#FFE4E6;padding:8px 12px;border-radius:12px;font-size:11px;font-weight:700;margin-bottom:10px;text-align:center;">
        🔥 新北 陳小姐 2 分鐘前剛帶走【軟糯奶杏色針織外套】！
      </div>
      <div onclick="copyCoupon(this)" style="background:linear-gradient(90deg,#BE123C,#E11D48);color:#FFF1F2;padding:10px 14px;border-radius:14px;font-size:12px;font-weight:800;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;cursor:pointer;">
        <span>🎟️ 仙女專屬折價碼：<b>FAIRY88</b>（滿額現折＋免運）</span>
        <span style="background:#FFF1F2;color:#BE123C;padding:3px 9px;border-radius:10px;font-size:11px;">點我複製</span>
      </div>
      <div class="ootd-hero">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="font-size:12px;color:#FDA4AF;font-weight:800;">🌡️ 今日即時氣溫 {w_info['temp']}°C（{w_info['range']}）</span>
          <button type="button" id="sign-btn" onclick="dailySign()" style="background:rgba(251,113,133,0.25);border:1px solid #FB7185;color:#FFE4E6;padding:4px 10px;border-radius:14px;font-size:11px;font-weight:800;cursor:pointer;">💖 每日簽到 +10愛心</button>
        </div>
        <div style="font-size:16px;font-weight:900;color:#FFF1F2;margin-top:6px;">👗 今日顯瘦穿搭：{w_info['look']}</div>
        <div style="font-size:12px;color:#FBBF24;font-weight:800;margin-top:6px;">⏳ 仙女限時免運倒數：<span id="countdown">03:59:59</span></div>
        <div class="btn-row" style="margin-top:10px;">
          <button type="button" class="btn btn-rose" onclick="drawLuckyBox()">🎰 抽今日幸運色＆盲盒優惠</button>
        </div>
        <div id="lucky-res" style="display:none;margin-top:10px;background:rgba(20,14,17,0.75);padding:10px;border-radius:12px;font-size:13px;color:#FFE4E6;border:1px dashed #FB7185;"></div>
      </div>

      <div class="chips">
        <div class="chip active" onclick="filterCat('all', this)">✨ 全部爆款選品</div>
        <div class="chip" onclick="filterCat('整套優惠組', this)">🎁 整套帶走省更多</div>
        <div class="chip" onclick="filterCat('韓系顯瘦上衣', this)">👚 韓系顯瘦上衣</div>
        <div class="chip" onclick="filterCat('顯瘦神褲裙裝', this)">👖 顯瘦神褲裙裝</div>
        <div class="chip" onclick="filterCat('可愛療癒小物', this)">🧸 可愛療癒小物</div>
        <div class="chip" onclick="filterCat('可愛配飾包包', this)">🎀 配飾包包</div>
      </div>
      <div id="shop-box"></div>
    </div></div>

    <div id="page-tone" class="page"><div class="wrap">
      <div class="shop-card">
        <div style="font-size:16px;font-weight:900;color:#FDA4AF;margin-bottom:6px;">🎨 互動式上下身配色試衣間</div>
        <div style="display:flex;gap:10px;align-items:center;">
          <div style="flex:1;text-align:center;">
            <div id="top-swatch" style="height:50px;border-radius:12px;background:#FDE68A;border:2px solid #fff;display:flex;align-items:center;justify-content:center;color:#1F2937;font-weight:900;font-size:12px;">👚 奶杏白上衣</div>
            <div style="display:flex;gap:6px;justify-content:center;margin-top:6px;">
              <button type="button" onclick="setOutfit('top','#FDE68A','奶杏白上衣')" style="width:22px;height:22px;border-radius:50%;background:#FDE68A;border:1px solid #fff;cursor:pointer;"></button>
              <button type="button" onclick="setOutfit('top','#FDA4AF','蜜桃粉上衣')" style="width:22px;height:22px;border-radius:50%;background:#FDA4AF;border:1px solid #fff;cursor:pointer;"></button>
              <button type="button" onclick="setOutfit('top','#93C5FD','霧霾藍上衣')" style="width:22px;height:22px;border-radius:50%;background:#93C5FD;border:1px solid #fff;cursor:pointer;"></button>
            </div>
          </div>
          <div style="font-size:16px;font-weight:900;color:#FDA4AF;">➕</div>
          <div style="flex:1;text-align:center;">
            <div id="bot-swatch" style="height:50px;border-radius:12px;background:#334155;border:2px solid #fff;display:flex;align-items:center;justify-content:center;color:#F8FAFC;font-weight:900;font-size:12px;">👖 深灰西裝褲</div>
            <div style="display:flex;gap:6px;justify-content:center;margin-top:6px;">
              <button type="button" onclick="setOutfit('bot','#334155','深灰西裝褲')" style="width:22px;height:22px;border-radius:50%;background:#334155;border:1px solid #fff;cursor:pointer;"></button>
              <button type="button" onclick="setOutfit('bot','#F5F5F4','燕麥白長裙')" style="width:22px;height:22px;border-radius:50%;background:#F5F5F4;border:1px solid #fff;cursor:pointer;"></button>
              <button type="button" onclick="setOutfit('bot','#60A5FA','復古牛仔褲')" style="width:22px;height:22px;border-radius:50%;background:#60A5FA;border:1px solid #fff;cursor:pointer;"></button>
            </div>
          </div>
        </div>
        <div id="outfit-comment" style="background:rgba(20,14,17,0.82);padding:8px;border-radius:10px;margin-top:8px;font-size:12px;color:#FFE4E6;text-align:center;">✨ 韓系溫柔千金配色！上淺下深視覺顯瘦 -3kg！</div>
      </div>
      <div class="shop-card">
        <div style="font-size:16px;font-weight:900;color:#FDA4AF;margin-bottom:4px;">📏 AI 網購衣服尺碼 ＆ 免運湊單精算</div>
        <div style="display:flex;gap:8px;margin-top:8px;">
          <input id="h-in" type="number" class="field" placeholder="身高 cm (160)" style="margin-top:0;"/>
          <input id="w-in" type="number" class="field" placeholder="體重 kg (52)" style="margin-top:0;"/>
          <button type="button" class="btn btn-rose" style="max-width:90px;" onclick="calcSize()">算尺碼</button>
        </div>
        <div id="size-res" style="display:none;background:rgba(20,14,17,0.82);padding:10px;border-radius:10px;margin-top:8px;font-size:12px;color:#FFE4E6;border-left:3px solid #10B981;"></div>
        <div style="display:flex;gap:8px;margin-top:10px;">
          <input id="cart-in" type="number" class="field" placeholder="目前金額 (滿$599免運)" style="margin-top:0;"/>
          <button type="button" class="btn btn-glass" style="max-width:90px;" onclick="calcFreeShip()">算湊單</button>
        </div>
        <div id="ship-res" style="display:none;background:rgba(20,14,17,0.82);padding:10px;border-radius:10px;margin-top:8px;font-size:12px;color:#FFE4E6;border-left:3px solid #F59E0B;"></div>
      </div>

      <div class="shop-card">
        <div style="font-size:16px;font-weight:900;color:#FDA4AF;margin-bottom:4px;">🎁 交換禮物預算 ＆ 🔮 仙女心理測驗</div>
        <div class="chips" style="margin-top:8px;padding-bottom:4px;">
          <div class="chip" onclick="pickGift(300)">🧸 $300內禮物</div>
          <div class="chip" onclick="pickGift(500)">💖 $500內禮物</div>
          <div class="chip" onclick="pickGift(1000)">👑 $1000整套禮</div>
          <div class="chip" onclick="quizResult('milk')">🧋 測今日氣場</div>
        </div>
        <div id="gift-res" style="background:rgba(20,14,17,0.82);padding:12px;border-radius:10px;margin-top:8px;font-size:13px;line-height:1.6;color:#FFF1F2;border-left:3px solid #FB7185;">
          👆 點選上方按鈕，立即推薦交換禮物與你的今日命定穿搭！
        </div>
      </div>
    </div></div>

    <div id="page-admin" class="page"><div class="wrap">
      <div class="shop-card">
        <div style="font-size:16px;font-weight:900;color:#FDA4AF;margin-bottom:4px;">🛍️ 店長快速上架爆款女裝／可愛小物</div>
        <form action="{S}api{S}shop_add" method="post">
          <select name="cat" class="field">
            <option value="韓系顯瘦上衣">👚 韓系顯瘦上衣</option>
            <option value="顯瘦神褲裙裝">👖 顯瘦神褲裙裝</option>
            <option value="可愛療癒小物">🧸 可愛療癒小物</option>
            <option value="可愛配飾包包">🎀 可愛配飾包包</option>
            <option value="整套優惠組">🎁 整套優惠組</option>
          </select>
          <input name="badge" class="field" placeholder="🏷️ 吸睛標籤" value="🔥 店長強推爆款"/>
          <input name="name" class="field" placeholder="👗 商品名稱" required/>
          <input name="price" class="field" placeholder="💰 優惠價（如：$399）" value="$399" required/>
          <input name="orig" class="field" placeholder="💸 原價劃線價（如：$690）" value="$690"/>
          <input name="img" class="field" placeholder="🖼️ 商品實品圖片網址（選填）"/>
          <textarea name="desc" class="field" rows="2" placeholder="✨ 推坑賣點描述" required></textarea>
          <input name="url" class="field" placeholder="🔗 貼上您的蝦皮／MOMO／賣場分潤購買網址" required/>
          <button type="submit" class="btn btn-rose" style="width:100%;margin-top:12px;padding:14px;">🚀 立即上架至選品櫥窗</button>
        </form>
      </div>
    </div></div>

    <div class="tabbar">
      <div class="tab active" onclick="switchTab('shop', this)">🛍️ 精品選品櫥窗</div>
      <div class="tab" onclick="switchTab('tone', this)">🎨 試衣間與工具</div>
      <div class="tab" onclick="switchTab('admin', this)"><span class="tab-cta">➕ 店長上架</span></div>
    </div>
    <script>
      const ITEMS = {items_json};
      const NL = String.fromCharCode(10);
      let curCat = 'all';

      const TICKERS = [
        '🔥 新北 陳小姐 2 分鐘前剛帶走【軟糯奶杏色針織外套】！',
        '🧸 台北 林小姐 剛剛搶購了【日系毛絨小熊雲朵化妝包】！',
        '💖 台中 張小姐 剛下單【約會必勝顯瘦三件套優惠組】！',
        '☕ 高雄 黃小姐 剛剛收藏了【奶油白胖胖貓爪保溫杯】！'
      ];
      let tkIdx = 0;
      setInterval(() => {{
        tkIdx = (tkIdx + 1) % TICKERS.length;
        const el = document.getElementById('live-ticker');
        if (el) el.innerText = TICKERS[tkIdx];
      }}, 3500);

      setInterval(() => {{
        const now = new Date();
        const end = new Date(); end.setHours(23, 59, 59, 999);
        const diff = Math.max(0, Math.floor((end - now) / 1000));
        const h = String(Math.floor(diff / 3600)).padStart(2, '0');
        const m = String(Math.floor((diff % 3600) / 60)).padStart(2, '0');
        const s = String(diff % 60).padStart(2, '0');
        const el = document.getElementById('countdown');
        if (el) el.innerText = h + ':' + m + ':' + s;
      }}, 1000);

      function copyCoupon(el) {{
        if (navigator.clipboard) navigator.clipboard.writeText('FAIRY88');
        el.innerHTML = '<span>✅ 已成功複製折扣碼：<b>FAIRY88</b>（結帳直接貼上！）</span><span style="background:#10B981;color:#fff;padding:3px 9px;border-radius:10px;font-size:11px;">已複製</span>';
      }}

      function dailySign() {{
        let pts = Number(localStorage.getItem('fairy_pts') || 0) + 10;
        localStorage.setItem('fairy_pts', pts);
        document.getElementById('sign-btn').innerText = '✨ 已簽到（' + pts + ' 愛心）';
        const box = document.getElementById('lucky-res');
        box.style.display = 'block';
        box.innerText = '🎁 簽到成功！目前累計 ' + pts + ' 顆仙女愛心！結帳輸入 FAIRY88 再享滿額禮遇！';
      }}

      function setOutfit(part, color, label) {{
        const el = document.getElementById(part === 'top' ? 'top-swatch' : 'bot-swatch');
        el.style.background = color;
        el.style.color = (color === '#334155') ? '#F8FAFC' : '#1F2937';
        el.innerText = (part === 'top' ? '👚 ' : '👖 ') + label;
        document.getElementById('outfit-comment').innerText = '💖 絕美韓妞撞色搭配！顯白度 98%，回頭率超高！';
      }}

      function calcSize() {{
        const h = Number(document.getElementById('h-in').value || 160);
        const w = Number(document.getElementById('w-in').value || 52);
        const bmi = w / ((h / 100) * (h / 100));
        let sz = 'M 碼（標準韓系微寬鬆顯瘦版型）';
        if (bmi < 19.5) sz = 'S 碼（修身精緻仙女版型）';
        else if (bmi >= 22.5 && bmi < 25.5) sz = 'L 碼（舒適遮肉垂墜顯瘦版型）';
        else if (bmi >= 25.5) sz = 'XL 碼（慵懶藏肉棉花糖女孩首選）';
        const box = document.getElementById('size-res');
        box.style.display = 'block';
        box.innerText = '👗 身高 ' + h + 'cm / 體重 ' + w + 'kg 精算：推薦拿【' + sz + '】！';
      }}

      function calcFreeShip() {{
        const cur = Number(document.getElementById('cart-in').value || 450);
        const diff = Math.max(0, 599 - cur);
        const box = document.getElementById('ship-res');
        box.style.display = 'block';
        box.innerText = diff === 0 ? '🎉 已達 $599 免運門檻！輸入 FAIRY88 再享好禮！' : '🧸 只差 $' + diff + ' 元就享免運！推薦順手帶走【小熊雲朵化妝包 $169】現省 $60 運費！';
      }}

      function pickGift(budget) {{
        const gMap = {{
          300: '🧸【$300 內交換禮物首選】推薦【日系毛絨小熊雲朵化妝包 $169】或【貝雷帽髮夾組 $199】！' + NL + '💌 祝福小卡：「願這份軟萌可愛的小禮物，陪你度過每個閃閃發光的日子 ✨」',
          500: '💖【$500 內高顏值實用禮】推薦【奶油白胖胖貓爪保溫杯 $289】或【法式方領上衣 $299】！' + NL + '💌 祝福小卡：「天冷了記得多喝熱水，願你每天都被溫柔與好運包圍 💕」',
          1000: '👑【$1000 內閨蜜奢華禮】推薦【約會必勝三件套組合包 $899】！整套搭配直接送進心坎裡！' + NL + '💌 祝福小卡：「祝最可愛的仙女天天漂亮、好運大爆發 🌸」'
        }};
        document.getElementById('gift-res').innerText = gMap[budget] || '';
      }}

      function quizResult(choice) {{
        document.getElementById('gift-res').innerText = '🧋【軟萌初戀系少女 · 甜度 100%】' + NL + '你今天散發溫柔無害的治癒氣場！最適合「軟糯奶杏色針織開襟外套 ＋ 毛絨小熊化妝包」，回頭率超高！';
      }}

      function filterCat(c, el) {{
        curCat = c;
        document.querySelectorAll('#page-shop .chips .chip').forEach(x => x.classList.remove('active'));
        el.classList.add('active');
        renderShop();
      }}

      function renderShop() {{
        const list = ITEMS.filter(x => curCat === 'all' || x.cat === curCat);
        document.getElementById('shop-box').innerHTML = list.map((x, idx) => {{
          const voteTxt = '🗳️【姐妹救命！幫我投票二選一】' + NL + '我在考慮這件【' + x.name + '】（優惠 ' + x.price + '）' + NL + '你覺得好不好看？回覆「1」買起來 /「2」再想想！' + NL + '👉 點這裡看實品照：' + decodeURIComponent('{app_url_enc}');
          const lineVoteU = `https:{S}{S}line.me{S}R{S}share?text=${{encodeURIComponent(voteTxt)}}`;
          const imgHtml = x.img ? `<img class="prod-img" src="${{x.img}}" loading="lazy"/>` : '';
          return `<div class="shop-card">
            ${{imgHtml}}
            <span style="font-size:11px;font-weight:800;background:rgba(251,113,133,0.2);color:#FDA4AF;padding:4px 10px;border-radius:10px;">${{x.badge}} · ${{x.cat}}</span>
            <div style="font-size:18px;font-weight:900;color:#FFF1F2;margin-top:8px;">${{x.name}}</div>
            <div style="font-size:13px;color:#FECDD3;line-height:1.6;margin-top:6px;">${{x.desc}}</div>
            <div class="price-row"><span class="price-now">${{x.price}}</span><span class="price-orig">原價 ${{x.orig}}</span></div>
            <div style="font-size:11px;color:#FDA4AF;margin-top:6px;">🔥 本週姐妹已搶購 88% · 優惠庫存倒數中</div>
            <div style="background:rgba(255,255,255,0.05);padding:8px 10px;border-radius:10px;font-size:11px;color:#FECDD3;margin-top:6px;">💬 <b>158cm/49kg 姐妹實穿：</b>版型超級顯瘦不刺膚，已經回購第二件！</div>
            <div class="btn-row">
              <button type="button" class="btn btn-glass" onclick="saveWish('${{x.name}}','${{x.price}}',this)">💖 收藏許願</button>
              <a class="btn btn-glass" href="${{lineVoteU}}">🗳️ 閨蜜投票</a>
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

      function switchTab(t, el) {{ document.querySelectorAll('.page').forEach(x => x.classList.remove('active')); document.querySelectorAll('.tab').forEach(x => x.classList.remove('active')); document.getElementById('page-' + t).classList.add('active'); el.classList.add('active'); }}
      renderShop();
    </script></body></html>"""
    return HTMLResponse(content=html)
def make_ootd_shop_card():
    S = chr(47)
    app_uri = f"{RENDER_BASE_URL}/ootd_app?openExternalBrowser=1"
    w_info = get_ootd_weather()
    first_item = next(iter(CUTE_SHOP_ITEMS), {})
    hot_price = str(first_item.get("price", "$399")) if isinstance(first_item, dict) else "$399"
    hot_url = str(first_item.get("url", MAIN_SHOP_URL)) if isinstance(first_item, dict) else MAIN_SHOP_URL

    share_msg = f"👗【每日氣溫顯瘦穿搭 ＆ 韓系可愛選品館】\n今天氣溫 {w_info['temp']}°C，推薦穿搭：{w_info['look']}\n🧸 還有超多韓系顯瘦女裝與療癒可愛小物限時優惠中！\n📲 免費測顯白膚色與逛選品櫥窗：\nhttps:{S}{S}line.me{S}R{S}ti{S}p{S}{LINE_BOT_BASIC_ID}"
    share_uri = f"https:{S}{S}line.me{S}R{S}share?text={urllib.parse.quote(share_msg)}"
    threads_uri = f"https:{S}{S}www.threads.net{S}intent{S}post?text={urllib.parse.quote(share_msg + ' #每日穿搭 #韓系女裝 #可愛小物')}"

    bubble_1 = BubbleContainer(
        size="mega",
        header=BoxComponent(layout="vertical", background_color="#1D1318", padding_all="16px", contents=[
            TextComponent(text="👗 每日氣溫穿搭 ＆ 可愛選品館", weight="bold", size="md", color="#FFE4E6", wrap=True),
            TextComponent(text="AI 顯白顯瘦公式 · 爆款女裝 · 療癒小物", size="xs", color="#FDA4AF", weight="bold", wrap=True, margin="xs")
        ]),
        body=BoxComponent(layout="vertical", spacing="sm", background_color="#FFF5F7", contents=[
            BoxComponent(layout="horizontal", spacing="sm", contents=[
                BoxComponent(layout="vertical", background_color="#3D2430", corner_radius="12px", padding_all="10px", align_items="center", contents=[
                    TextComponent(text="🌡️ 今日氣溫", size="xxs", color="#FDA4AF", weight="bold"),
                    TextComponent(text=f"{w_info['temp']}°C", size="sm", color="#FFFFFF", weight="bold", margin="xs")
                ]),
                BoxComponent(layout="vertical", background_color="#3D2430", corner_radius="12px", padding_all="10px", align_items="center", contents=[
                    TextComponent(text="🔥 今日爆款", size="xxs", color="#FBBF24", weight="bold"),
                    TextComponent(text=f"{hot_price} 優惠", size="sm", color="#FFFFFF", weight="bold", margin="xs")
                ])
            ]),
            BoxComponent(layout="vertical", background_color="#FFE4E6", corner_radius="14px", padding_all="12px", contents=[
                TextComponent(text="✨ 今日顯瘦穿搭靈感：", size="xs", color="#BE123C", weight="bold"),
                TextComponent(text=w_info["look"], size="xs", color="#1F2937", wrap=True, margin="xs")
            ])
        ]),
        footer=BoxComponent(layout="vertical", spacing="sm", background_color="#FFF5F7", contents=[
            ButtonComponent(style="primary", color="#E11D48", height="sm", action=URIAction(label="🛍️ 開啟韓系女裝選品櫥窗", uri=app_uri)),
            BoxComponent(layout="horizontal", spacing="sm", contents=[
                ButtonComponent(style="primary", color="#FB7185", height="sm", action=URIAction(label="🔥 搶爆款", uri=hot_url)),
                ButtonComponent(style="secondary", height="sm", action=MessageAction(label="🔮 測氣場", text="心理測驗"))
            ]),
            BoxComponent(layout="horizontal", spacing="sm", contents=[
                ButtonComponent(style="secondary", height="sm", action=MessageAction(label="🧸 可愛物", text="可愛小物")),
                ButtonComponent(style="primary", color="#D97706", height="sm", action=MessageAction(label="🎰 幸運色", text="抽幸運色"))
            ])
        ])
    )

    bubble_2 = BubbleContainer(
        size="mega",
        header=BoxComponent(layout="vertical", background_color="#1D1318", padding_all="16px", contents=[
            TextComponent(text="💌 閨蜜湊免運 ＆ 官方賣場直達", weight="bold", size="md", color="#FFE4E6", wrap=True),
            TextComponent(text="一鍵轉傳給姐妹挑穿搭、逛主賣場全館折扣", size="xs", color="#FDA4AF", weight="bold", wrap=True, margin="xs")
        ]),
        body=BoxComponent(layout="vertical", spacing="xs", background_color="#FFF5F7", contents=[
            TextComponent(text="👈 向左滑動返回「今日氣溫穿搭與選品櫥窗」", size="xxs", color="#9F1239", weight="bold")
        ]),
        footer=BoxComponent(layout="vertical", spacing="sm", background_color="#FFF5F7", contents=[
            ButtonComponent(style="primary", color="#E11D48", height="sm", action=URIAction(label="🏪 前往官方全館賣場", uri=MAIN_SHOP_URL)),
            BoxComponent(layout="horizontal", spacing="sm", contents=[
                ButtonComponent(style="primary", color="#10B981", height="sm", action=URIAction(label="💌 問閨蜜", uri=share_uri)),
                ButtonComponent(style="primary", color="#1A1B1E", height="sm", action=URIAction(label="🧵 發脆文", uri=threads_uri))
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
        if any(k in txt for k in ["交換禮物", "送禮", "聖誕禮物", "生日禮物"]):
            gift_msg = (
                "🎁【女生收到會尖叫・交換禮物 ＆ 送禮排行榜】\n"
                "1. $300 內不踩雷：日系毛絨小熊雲朵化妝包（$169）\n"
                "2. $500 內超實用：奶油白胖胖貓爪保溫隨行杯（$289）\n"
                "3. $1000 內閨蜜禮：溫柔約會顯瘦三件套組合包（$899）\n"
                f"🛍️ 立即前往選品櫥窗搶購免運優惠：\n{MAIN_SHOP_URL}"
            )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=gift_msg))
            return

        if any(k in txt for k in ["怎麼洗", "洗護", "縮水", "起毛球", "保養"]):
            wash_msg = (
                "🧺【韓系精緻女裝防縮水洗護秘訣】\n"
                "1. 針織開襟衫：請裝入細網洗衣袋選「柔洗模式」或 30°C 以下冷水手洗，切勿烘乾，洗後平鋪晾乾就不會變形！\n"
                "2. 雪紡／法式上衣：反面套洗衣袋機洗，陰涼處懸掛晾乾即平整。\n"
                "3. 毛絨小熊化妝包：局部髒污用中性洗劑輕拍擦拭，自然風乾依然蓬鬆可愛！"
            )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=wash_msg))
            return

        if any(k in txt for k in ["約會", "尾牙", "聚餐", "上班", "通勤", "出國", "旅遊", "遮肚子", "顯瘦"]):
            app_uri = f"{RENDER_BASE_URL}/ootd_app?openExternalBrowser=1"
            advice = (
                "👗【專屬場合顯瘦穿搭顧問建議】\n"
                "💕 約會／聚餐：法式方領鎖骨針織上衣 ＋ 高腰A字裙，溫柔純欲感拉滿！\n"
                "💼 上班／通勤：軟糯奶杏針織開襟衫 ＋ 高腰垂墜西裝闊腿褲，俐落遮肉又顯腿長！\n"
                "✈️ 出國／旅遊：洋蔥式層次穿搭 ＋ 復古貝雷帽（拍照超上鏡又不怕風吹亂頭髮）！\n"
                f"🛍️ 點擊開啟選品櫥窗搶購整套優惠組：\n{app_uri}"
            )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=advice))
            return

        if any(k in txt for k in ["折扣碼", "優惠碼", "免運", "折價券"]):
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🎟️【仙女 VIP 專屬隱藏優惠口令】\n專屬折扣碼：FAIRY88\n✨ 滿額現折再享超商免運優惠！\n🛍️ 立即前往官方賣場使用：\n{MAIN_SHOP_URL}"))
            return

        if txt.startswith("尺碼"):
            nums = re.findall(r"\d+(?:\.\d+)?", txt)
            h = float(next(iter(nums), 160.0))
            w = float(nums[1]) if len(nums) >= 2 else 52.0
            bmi = w / ((h / 100.0) ** 2)
            sz = "S 碼（修身精緻版型）" if bmi < 19.5 else ("M 碼（標準韓系微寬鬆顯瘦）" if bmi < 22.5 else ("L 碼（舒適遮肉顯瘦版型）" if bmi < 25.5 else "XL 碼（慵懶藏肉版型）"))
            app_uri = f"{RENDER_BASE_URL}/ootd_app?openExternalBrowser=1"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"📏【AI 網購尺碼精算結果】\n身高 {int(h)}cm / 體重 {int(w)}kg\n👗 推薦拿：【{sz}】\n🛍️ 立即前往選品櫥窗挑選同款：\n{app_uri}"))
            return

        if txt in ["心理測驗", "測氣場", "穿搭測驗", "每日簽到", "簽到"]:
            app_uri = f"{RENDER_BASE_URL}/ootd_app?openExternalBrowser=1"
            msg = (
                "🔮【今日仙女氣場心理測驗 ＆ 每日簽到】\n"
                "憑直覺選一杯現在最想喝的飲品，秒測你的今日命定穿搭色系、顯白秘訣與幸運可愛小物！\n"
                "💖 每天簽到還能累積仙女愛心領取隱藏折價口令喔！\n"
                f"🛍️ 立即前往互動測驗與選品櫥窗：\n{app_uri}"
            )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
            return

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

        if txt == "可愛小物":
            cute_list = [x for x in CUTE_SHOP_ITEMS if isinstance(x, dict) and "可愛" in x.get("cat", "")]
            if not cute_list:
                cute_list = [x for x in CUTE_SHOP_ITEMS if isinstance(x, dict)][:3]
            lines = ["🧸【本週閨蜜瘋搶・可愛療癒小物 TOP 精選】"]
            for it in cute_list[:3]:
                lines.append(f"\n• {it.get('badge','')} {it.get('name','')}（優惠 {it.get('price','')}）\n  ✨ {it.get('desc','')}")
            lines.append(f"\n🛍️ 立即前往官方賣場搶購免運優惠：\n{MAIN_SHOP_URL}")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="\n".join(lines)))
            return

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

        matched = [x for x in CUTE_SHOP_ITEMS if isinstance(x, dict) and any(k in txt for k in ["針織", "外套", "褲", "化妝包", "杯", "帽", "三件套"])]
        if matched and txt not in ["穿搭", "可愛小物"]:
            it = next(iter(matched), {})
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🔍 為您找到相關爆款選品：\n\n{it.get('badge','')} {it.get('name','')}\n💰 優惠價：{it.get('price','')}（原價 {it.get('orig','')}）\n✨ {it.get('desc','')}\n\n🛍️ 立即搶購：\n{it.get('url', MAIN_SHOP_URL)}"))
            return

        card = make_ootd_shop_card()
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="👗 每日氣溫穿搭 ＆ 韓系可愛選品館", contents=card))
    except Exception as e:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"👗 系統小提示：{str(e)[:60]}（請輸入「穿搭」刷新畫面）"))
