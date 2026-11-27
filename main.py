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
    {"sku": "W01", "cat": "韓系顯瘦上衣", "badge": "🌸 本週爆賣 #1", "name": "軟糯奶杏色麻花針織開襟外套", "price": "$399", "orig": "$690", "img": "https://unsplash.com", "desc": "微寬鬆落肩版型超遮副乳與蝴蝶袖，早晚溫差搭這件溫柔感滿分！", "url": MAIN_SHOP_URL},
    {"sku": "W02", "cat": "顯瘦神褲裙裝", "badge": "✨ 梨形身材救星", "name": "高腰垂墜感西裝闊腿長褲（附腰帶）", "price": "$450", "orig": "$780", "img": "https://unsplash.com", "desc": "視覺腿長瞬間 +10cm！完美修飾假胯寬，上班約會都能穿。", "url": MAIN_SHOP_URL},
    {"sku": "W03", "cat": "可愛療癒小物", "badge": "🧸 閨蜜湊單熱銷", "name": "日系毛絨小熊雲朵手提化妝包", "price": "$169", "orig": "$299", "img": "https://unsplash.com", "desc": "超軟萌泰迪絨毛手感，放補妝氣墊、護手霜與行動電源剛剛好！", "url": MAIN_SHOP_URL},
    {"sku": "W04", "cat": "可愛療癒小物", "badge": "💖 辦公室治癒系", "name": "奶油白胖胖貓爪保溫隨行咖啡杯 500ml", "price": "$289", "orig": "$490", "img": "https://unsplash.com", "desc": "316 不鏽鋼陶瓷內膽，買超商咖啡現折 5 元，放辦公桌超吸睛！", "url": MAIN_SHOP_URL},
    {"sku": "B01", "cat": "整套優惠組", "badge": "👑 整套帶走省$350", "name": "【約會必勝三件套】奶杏針織外套＋高腰闊腿褲＋小熊化妝包", "price": "$899", "orig": "$1,249", "img": "https://unsplash.com", "desc": "整套幫你配到好！免煩惱上下身配色，整組帶走再享免運優惠！", "url": MAIN_SHOP_URL},
    {"sku": "W05", "cat": "韓系顯瘦上衣", "badge": "🌷 約會純欲風", "name": "法式方領鎖骨顯瘦坑條針織上衣", "price": "$299", "orig": "$520", "img": "https://unsplash.com", "desc": "露出最纖細的鎖骨線條，單穿或當大衣內搭都超級顯白！", "url": MAIN_SHOP_URL},
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
    return {"status": "Online", "service": "Taiwan Romantic OOTD & Cute Boutique Pro App 7.0"}

@app.post("/api/shop_add")
async def web_shop_add(
    cat: str = Form("韓系顯瘦上衣"),
    badge: str = Form("🌸 店長浪漫新品"),
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
        "badge": badge.strip() or "🌸 店長浪漫新品",
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
    toast_html = '<div class="toast">🌸 店長浪漫新品已成功上架至精品選品櫥窗囉！</div>' if msg == "added" else ""

    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no"/>
    <title>🌸 每日氣溫穿搭 ＆ 韓系浪漫選品館</title>
    <style>
      * {{ box-sizing: border-box; -webkit-tap-highlight-color: transparent; }}
      body {{ margin: 0; padding: 0 0 92px 0; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif; background: linear-gradient(160deg, #FFF5F8 0%, #F8F3FF 50%, #FFF0F5 100%); color: #4A2535; min-height: 100vh; }}
      .topbar {{ background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(18px); padding: 15px 18px; position: sticky; top: 0; z-index: 100; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(244, 114, 182, 0.22); }}
      .topbar h1 {{ margin: 0; font-size: 16px; font-weight: 800; color: #831843; letter-spacing: 0.4px; }}
      .badge-vip {{ font-size: 11px; background: linear-gradient(135deg, #F472B6, #C084FC); color: #fff; padding: 4px 11px; border-radius: 20px; font-weight: 800; box-shadow: 0 3px 10px rgba(244, 114, 182, 0.3); }}
      .wrap {{ max-width: 540px; margin: 0 auto; padding: 14px; }}
      .toast {{ background: #FCE7F3; border: 1px solid #F472B6; color: #9D174D; padding: 12px; border-radius: 16px; font-size: 13px; font-weight: 700; margin-bottom: 12px; text-align: center; }}
      .ootd-hero {{ background: linear-gradient(135deg, rgba(255, 255, 255, 0.92), rgba(253, 242, 248, 0.92)); border: 1px solid rgba(244, 114, 182, 0.28); border-radius: 24px; padding: 16px; margin-bottom: 14px; box-shadow: 0 8px 24px rgba(244, 114, 182, 0.12); }}
      .chips {{ display: flex; gap: 8px; overflow-x: auto; padding-bottom: 12px; scrollbar-width: none; }}
      .chip {{ white-space: nowrap; background: rgba(255, 255, 255, 0.85); border: 1px solid rgba(244, 114, 182, 0.25); color: #9D174D; padding: 8px 14px; border-radius: 20px; font-size: 12px; font-weight: 700; cursor: pointer; box-shadow: 0 2px 8px rgba(244, 114, 182, 0.08); }}
      .chip.active {{ background: linear-gradient(135deg, #F472B6, #A855F7); border-color: #F9A8D4; color: #fff; box-shadow: 0 4px 14px rgba(219, 39, 119, 0.28); }}
      .shop-card {{ background: rgba(255, 255, 255, 0.92); backdrop-filter: blur(16px); border: 1px solid rgba(244, 114, 182, 0.22); border-radius: 24px; padding: 16px; margin-bottom: 14px; box-shadow: 0 8px 26px rgba(192, 132, 252, 0.12); }}
      .prod-img {{ width: 100%; height: 215px; object-fit: cover; border-radius: 18px; margin-bottom: 12px; border: 1px solid rgba(244, 114, 182, 0.2); display: block; }}
      .price-row {{ display: flex; align-items: baseline; gap: 8px; margin-top: 8px; }}
      .price-now {{ font-size: 22px; font-weight: 900; color: #DB2777; }}
      .price-orig {{ font-size: 13px; color: #9CA3AF; text-decoration: line-through; }}
      .btn-row {{ display: flex; gap: 8px; margin-top: 12px; }}
      .btn {{ flex: 1; text-align: center; text-decoration: none; padding: 11px 6px; border-radius: 14px; font-size: 13px; font-weight: 800; cursor: pointer; border: none; color: #fff; }}
      .btn-rose {{ background: linear-gradient(135deg, #F472B6, #EC4899); box-shadow: 0 4px 12px rgba(236, 72, 153, 0.28); }}
      .btn-glass {{ background: #FDF2F8; color: #9D174D; border: 1px solid #FBCFE8; }}
      .field {{ width: 100%; background: #FFF9FB; border: 1px solid #FBCFE8; color: #4A2535; padding: 12px; border-radius: 14px; font-size: 14px; margin-top: 8px; }}
      .page {{ display: none; }}
      .page.active {{ display: block; }}
      .tabbar {{ position: fixed; bottom: 0; left: 0; right: 0; background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(18px); border-top: 1px solid rgba(244, 114, 182, 0.22); display: flex; padding: 8px 8px 14px; z-index: 120; }}
      .tab {{ flex: 1; text-align: center; color: #9D174D; font-size: 12px; font-weight: 800; cursor: pointer; padding-top: 4px; }}
      .tab.active {{ color: #DB2777; }}
      .tab-cta {{ background: linear-gradient(135deg, #F472B6, #A855F7); color: #fff; padding: 8px 12px; border-radius: 20px; font-size: 12px; }}
    </style></head><body>
    <div class="topbar"><h1>🌸 韓系浪漫穿搭 ＆ 可愛選品館</h1><span class="badge-vip">仙女 VIP 專享</span></div>
    <div id="page-shop" class="page active"><div class="wrap">
      {toast_html}
      <div id="live-ticker" style="background:#FCE7F3;border:1px solid #F9A8D4;color:#9D174D;padding:8px 12px;border-radius:14px;font-size:11px;font-weight:700;margin-bottom:10px;text-align:center;">
        🌸 新北 陳小姐 2 分鐘前剛帶走【軟糯奶杏色針織外套】！
      </div>
      <div onclick="copyCoupon(this)" style="background:linear-gradient(90deg,#F472B6,#C084FC);color:#FFFFFF;padding:10px 14px;border-radius:16px;font-size:12px;font-weight:800;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;cursor:pointer;box-shadow:0 4px 14px rgba(244,114,182,0.28);">
        <span>🎟️ 浪漫 VIP 折價碼：<b>FAIRY88</b>（滿額現折＋免運）</span>
        <span style="background:#FFFFFF;color:#DB2777;padding:3px 9px;border-radius:10px;font-size:11px;">點我複製</span>
      </div>
      <div class="ootd-hero">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="font-size:12px;color:#BE185D;font-weight:800;">🌡️ 今日即時氣溫 {w_info['temp']}°C（{w_info['range']}）</span>
          <button type="button" id="sign-btn" onclick="dailySign()" style="background:#FCE7F3;border:1px solid #F472B6;color:#9D174D;padding:4px 10px;border-radius:14px;font-size:11px;font-weight:800;cursor:pointer;">💖 每日簽到 +10愛心</button>
        </div>
        <div style="font-size:16px;font-weight:900;color:#831843;margin-top:6px;">👗 今日顯瘦穿搭：{w_info['look']}</div>
        <div style="font-size:12px;color:#A855F7;font-weight:800;margin-top:6px;">⏳ 浪漫限時免運倒數：<span id="countdown">03:59:59</span></div>
        <div class="btn-row" style="margin-top:10px;">
          <button type="button" class="btn btn-rose" onclick="drawLuckyBox()">🎰 抽今日幸運色＆盲盒優惠</button>
        </div>
        <div id="lucky-res" style="display:none;margin-top:10px;background:#FFF5F8;padding:10px;border-radius:14px;font-size:13px;color:#831843;border:1px dashed #F472B6;"></div>
      </div>

      <div class="chips">
        <div class="chip active" onclick="filterCat('all', this)">✨ 全部浪漫選品</div>
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
        <div style="font-size:16px;font-weight:900;color:#831843;margin-bottom:6px;">🎨 互動式上下身配色試衣間</div>
        <div style="display:flex;gap:10px;align-items:center;">
          <div style="flex:1;text-align:center;">
            <div id="top-swatch" style="height:50px;border-radius:14px;background:#FEF3C7;border:2px solid #FBCFE8;display:flex;align-items:center;justify-content:center;color:#78350F;font-weight:900;font-size:12px;">👚 奶杏白上衣</div>
            <div style="display:flex;gap:6px;justify-content:center;margin-top:6px;">
              <button type="button" onclick="setOutfit('top','#FEF3C7','奶杏白上衣')" style="width:22px;height:22px;border-radius:50%;background:#FEF3C7;border:1px solid #F472B6;cursor:pointer;"></button>
              <button type="button" onclick="setOutfit('top','#FCE7F3','櫻花粉上衣')" style="width:22px;height:22px;border-radius:50%;background:#FCE7F3;border:1px solid #F472B6;cursor:pointer;"></button>
              <button type="button" onclick="setOutfit('top','#E0F2FE','晴空藍上衣')" style="width:22px;height:22px;border-radius:50%;background:#E0F2FE;border:1px solid #F472B6;cursor:pointer;"></button>
            </div>
          </div>
          <div style="font-size:16px;font-weight:900;color:#EC4899;">➕</div>
          <div style="flex:1;text-align:center;">
            <div id="bot-swatch" style="height:50px;border-radius:14px;background:#E2E8F0;border:2px solid #FBCFE8;display:flex;align-items:center;justify-content:center;color:#1E293B;font-weight:900;font-size:12px;">👖 霧灰西裝褲</div>
            <div style="display:flex;gap:6px;justify-content:center;margin-top:6px;">
              <button type="button" onclick="setOutfit('bot','#E2E8F0','霧灰西裝褲')" style="width:22px;height:22px;border-radius:50%;background:#E2E8F0;border:1px solid #F472B6;cursor:pointer;"></button>
              <button type="button" onclick="setOutfit('bot','#FFFBEB','燕麥白長裙')" style="width:22px;height:22px;border-radius:50%;background:#FFFBEB;border:1px solid #F472B6;cursor:pointer;"></button>
              <button type="button" onclick="setOutfit('bot','#DBEAFE','復古淺牛仔')" style="width:22px;height:22px;border-radius:50%;background:#DBEAFE;border:1px solid #F472B6;cursor:pointer;"></button>
            </div>
          </div>
        </div>
        <div id="outfit-comment" style="background:#FDF2F8;padding:8px;border-radius:12px;margin-top:8px;font-size:12px;color:#9D174D;text-align:center;">✨ 清新浪漫韓妞配色！顯白度 98%，溫柔氣質爆棚！</div>
      </div>
      <div class="shop-card">
        <div style="font-size:16px;font-weight:900;color:#831843;margin-bottom:4px;">✨ 今日星座開運穿搭 ＆ 📸 IG 浪漫語錄</div>
        <div class="chips" style="margin-top:8px;padding-bottom:4px;">
          <div class="chip" onclick="zodiacLuck('水象')">♓ 雙魚/巨蟹/天蠍</div>
          <div class="chip" onclick="zodiacLuck('風象')">♎ 天秤/水瓶/雙子</div>
          <div class="chip" onclick="zodiacLuck('火象')">♈ 牡羊/獅子/射手</div>
          <div class="chip" onclick="zodiacLuck('土象')">♍ 處女/金牛/摩羯</div>
        </div>
        <div id="zodiac-res" style="background:#FDF2F8;padding:10px;border-radius:12px;margin-top:6px;font-size:12px;line-height:1.6;color:#831843;border-left:3px solid #C084FC;">
          👆 點選你的星座象限，立即解鎖今日戀愛桃花色與開運單品！
        </div>
        <div class="btn-row" style="margin-top:10px;">
          <button type="button" class="btn btn-glass" onclick="genIgCaption()">📸 生成今日韓系 IG 穿搭文案</button>
        </div>
        <div id="ig-res" style="display:none;background:#F8F3FF;padding:10px;border-radius:12px;margin-top:8px;font-size:12px;color:#6B21A8;border:1px dashed #C084FC;"></div>
      </div>

      <div class="shop-card">
        <div style="font-size:16px;font-weight:900;color:#831843;margin-bottom:4px;">📏 AI 尺碼 ＆ 🧮 滿額免運／滿千折百精算</div>
        <div style="display:flex;gap:8px;margin-top:8px;">
          <input id="h-in" type="number" class="field" placeholder="身高 cm (160)" style="margin-top:0;"/>
          <input id="w-in" type="number" class="field" placeholder="體重 kg (52)" style="margin-top:0;"/>
          <button type="button" class="btn btn-rose" style="max-width:88px;" onclick="calcSize()">算尺碼</button>
        </div>
        <div id="size-res" style="display:none;background:#FDF2F8;padding:10px;border-radius:12px;margin-top:8px;font-size:12px;color:#831843;border-left:3px solid #EC4899;"></div>
        <div style="display:flex;gap:8px;margin-top:10px;">
          <input id="cart-in" type="number" class="field" placeholder="購物車金額 (滿$599免運/滿$1000折$120)" style="margin-top:0;"/>
          <button type="button" class="btn btn-glass" style="max-width:88px;" onclick="calcFreeShip()">算優惠</button>
        </div>
        <div id="ship-res" style="display:none;background:#FDF2F8;padding:10px;border-radius:12px;margin-top:8px;font-size:12px;color:#831843;border-left:3px solid #A855F7;"></div>
      </div>
    </div></div>

    <div id="page-admin" class="page"><div class="wrap">
      <div class="shop-card">
        <div style="font-size:16px;font-weight:900;color:#831843;margin-bottom:4px;">🛍️ 店長快速上架浪漫女裝／可愛小物</div>
        <form action="{S}api{S}shop_add" method="post">
          <select name="cat" class="field">
            <option value="韓系顯瘦上衣">👚 韓系顯瘦上衣</option>
            <option value="顯瘦神褲裙裝">👖 顯瘦神褲裙裝</option>
            <option value="可愛療癒小物">🧸 可愛療癒小物</option>
            <option value="可愛配飾包包">🎀 可愛配飾包包</option>
            <option value="整套優惠組">🎁 整套優惠組</option>
          </select>
          <input name="badge" class="field" placeholder="🏷️ 吸睛標籤" value="🌸 店長浪漫新品"/>
          <input name="name" class="field" placeholder="👗 商品名稱" required/>
          <input name="price" class="field" placeholder="💰 優惠價（如：$399）" value="$399" required/>
          <input name="orig" class="field" placeholder="💸 原價劃線價（如：$690）" value="$690"/>
          <input name="img" class="field" placeholder="🖼️ 商品實品圖片網址（選填）"/>
          <textarea name="desc" class="field" rows="2" placeholder="✨ 推坑賣點描述" required></textarea>
          <input name="url" class="field" placeholder="🔗 貼上您的蝦皮／MOMO／賣場分潤購買網址" required/>
          <button type="submit" class="btn btn-rose" style="width:100%;margin-top:12px;padding:14px;">🚀 立即上架至浪漫選品櫥窗</button>
        </form>
      </div>
    </div></div>

    <div class="tabbar">
      <div class="tab active" onclick="switchTab('shop', this)">🌸 浪漫選品櫥窗</div>
      <div class="tab" onclick="switchTab('tone', this)">✨ 試衣間與占卜</div>
      <div class="tab" onclick="switchTab('admin', this)"><span class="tab-cta">➕ 店長上架</span></div>
    </div>
    <script>
      const ITEMS = {items_json};
      const NL = String.fromCharCode(10);
      let curCat = 'all';

      const TICKERS = [
        '🌸 新北 陳小姐 2 分鐘前剛帶走【軟糯奶杏色針織外套】！',
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
        el.innerText = (part === 'top' ? '👚 ' : '👖 ') + label;
        document.getElementById('outfit-comment').innerText = '💖 清新浪漫韓妞配色！顯白度 98%，溫柔感爆棚！';
      }}

      function zodiacLuck(el) {{
        const zMap = {{
          '水象': '♓【水象星座・桃花指數 99%】今日開運色：櫻花粉＆奶杏白！穿上法式方領上衣，轉角遇見浪漫好運！',
          '風象': '♎【風象星座・貴人指數 96%】今日開運色：晴空藍＆燕麥白！搭配貝雷帽珍珠髮夾組，靈感與魅力滿分！',
          '火象': '♈【火象星座・元氣指數 98%】今日開運色：蜜桃珊瑚粉！帶上泰迪熊雲朵化妝包，整天充滿甜美正能量！',
          '土象': '♍【土象星座・質感指數 97%】今日開運色：焦糖奶杏色！高腰垂墜西裝褲配貓爪保溫杯，高級感滿分！'
        }};
        document.getElementById('zodiac-res').innerText = zMap[el] || '';
      }}

      function genIgCaption() {{
        const caps = [
          '🌸 把溫柔穿在身上，連微風都變得甜甜的 ✨ #每日穿搭 #韓系溫柔風 #OOTD',
          '🧸 今日份可愛已送達！軟糯針織衫是秋冬最治癒的擁抱 💕 #顯瘦穿搭 #韓系女裝',
          '☕ 喜歡剛剛好的溫度，和剛剛好的自己 🌷 #日常碎片 #仙女穿搭 #可愛小物'
        ];
        const pick = caps[Math.floor(Math.random() * caps.length)];
        if (navigator.clipboard) navigator.clipboard.writeText(pick);
        const box = document.getElementById('ig-res');
        box.style.display = 'block';
        box.innerText = '✅ 已為您生成並自動複製 IG 文案：' + NL + pick;
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
        const box = document.getElementById('ship-res');
        box.style.display = 'block';
        if (cur >= 1000) {{
          box.innerText = '👑 恭喜達標滿 $1,000 現折 $120 ＋ 免運！結帳再輸入 FAIRY88 享 VIP 禮！';
        }} else if (cur >= 599) {{
          box.innerText = '🎉 已享 $599 免運！再湊 $' + (1000 - cur) + ' 元即可現折 $120 喔！';
        }} else {{
          box.innerText = '🧸 只差 $' + (599 - cur) + ' 元就享免運！推薦帶走【小熊雲朵化妝包 $169】現省運費！';
        }}
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
            <span style="font-size:11px;font-weight:800;background:#FCE7F3;color:#BE185D;padding:4px 10px;border-radius:10px;">${{x.badge}} · ${{x.cat}}</span>
            <div style="font-size:18px;font-weight:900;color:#831843;margin-top:8px;">${{x.name}}</div>
            <div style="font-size:13px;color:#6B4256;line-height:1.6;margin-top:6px;">${{x.desc}}</div>
            <div class="price-row"><span class="price-now">${{x.price}}</span><span class="price-orig">原價 ${{x.orig}}</span></div>
            <div style="font-size:11px;color:#DB2777;font-weight:700;margin-top:6px;">🌸 本週姐妹已搶購 88% · 浪漫優惠倒數中</div>
            <div style="background:#FFF5F8;padding:8px 10px;border-radius:12px;font-size:11px;color:#831843;margin-top:6px;border:1px solid #FBCFE8;">💬 <b>158cm/49kg 姐妹實穿：</b>版型超級顯瘦不刺膚，已經回購第二件！</div>
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
          '🎀 今日幸運色：【櫻花蜜桃粉】！搭配珍珠耳飾或貝雷帽，氣色瞬間白兩階！',
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

    share_msg = f"🌸【每日氣溫浪漫穿搭 ＆ 韓系可愛選品館】\n今天氣溫 {w_info['temp']}°C，推薦穿搭：{w_info['look']}\n🧸 還有超多韓系顯瘦女裝與療癒可愛小物限時優惠中！\n📲 免費測星座開運色與逛浪漫櫥窗：\nhttps:{S}{S}line.me{S}R{S}ti{S}p{S}{LINE_BOT_BASIC_ID}"
    share_uri = f"https:{S}{S}line.me{S}R{S}share?text={urllib.parse.quote(share_msg)}"
    threads_uri = f"https:{S}{S}www.threads.net{S}intent{S}post?text={urllib.parse.quote(share_msg + ' #每日穿搭 #韓系女裝 #可愛小物')}"

    bubble_1 = BubbleContainer(
        size="mega",
        header=BoxComponent(layout="vertical", background_color="#FCE7F3", padding_all="16px", contents=[
            TextComponent(text="🌸 每日氣溫浪漫穿搭 ＆ 選品館", weight="bold", size="md", color="#831843", wrap=True),
            TextComponent(text="星座開運色 · 顯瘦女裝 · 療癒可愛小物", size="xs", color="#DB2777", weight="bold", wrap=True, margin="xs")
        ]),
        body=BoxComponent(layout="vertical", spacing="sm", background_color="#FFFFFF", contents=[
            BoxComponent(layout="horizontal", spacing="sm", contents=[
                BoxComponent(layout="vertical", background_color="#FDF2F8", corner_radius="12px", padding_all="10px", align_items="center", contents=[
                    TextComponent(text="🌡️ 今日氣溫", size="xxs", color="#BE185D", weight="bold"),
                    TextComponent(text=f"{w_info['temp']}°C", size="sm", color="#831843", weight="bold", margin="xs")
                ]),
                BoxComponent(layout="vertical", background_color="#F3E8FF", corner_radius="12px", padding_all="10px", align_items="center", contents=[
                    TextComponent(text="💖 浪漫爆款", size="xxs", color="#7E22CE", weight="bold"),
                    TextComponent(text=f"{hot_price} 優惠", size="sm", color="#581C87", weight="bold", margin="xs")
                ])
            ]),
            BoxComponent(layout="vertical", background_color="#FFF5F8", corner_radius="14px", padding_all="12px", contents=[
                TextComponent(text="✨ 今日顯瘦穿搭靈感：", size="xs", color="#BE185D", weight="bold"),
                TextComponent(text=w_info["look"], size="xs", color="#4A2535", wrap=True, margin="xs")
            ])
        ]),
        footer=BoxComponent(layout="vertical", spacing="sm", background_color="#FFFFFF", contents=[
            ButtonComponent(style="primary", color="#EC4899", height="sm", action=URIAction(label="🌸 開啟浪漫女裝選品櫥窗", uri=app_uri)),
            BoxComponent(layout="horizontal", spacing="sm", contents=[
                ButtonComponent(style="primary", color="#F472B6", height="sm", action=URIAction(label="🔥 搶爆款", uri=hot_url)),
                ButtonComponent(style="secondary", height="sm", action=MessageAction(label="✨ 測星座", text="星座穿搭"))
            ]),
            BoxComponent(layout="horizontal", spacing="sm", contents=[
                ButtonComponent(style="secondary", height="sm", action=MessageAction(label="🧸 可愛物", text="可愛小物")),
                ButtonComponent(style="primary", color="#A855F7", height="sm", action=MessageAction(label="🎰 幸運色", text="抽幸運色"))
            ])
        ])
    )

    bubble_2 = BubbleContainer(
        size="mega",
        header=BoxComponent(layout="vertical", background_color="#F3E8FF", padding_all="16px", contents=[
            TextComponent(text="💌 閨蜜湊免運 ＆ 官方賣場直達", weight="bold", size="md", color="#581C87", wrap=True),
            TextComponent(text="一鍵轉傳給姐妹挑穿搭、逛主賣場全館折扣", size="xs", color="#7E22CE", weight="bold", wrap=True, margin="xs")
        ]),
        body=BoxComponent(layout="vertical", spacing="xs", background_color="#FFFFFF", contents=[
            TextComponent(text="👈 向左滑動返回「今日浪漫穿搭與選品櫥窗」", size="xxs", color="#9D174D", weight="bold")
        ]),
        footer=BoxComponent(layout="vertical", spacing="sm", background_color="#FFFFFF", contents=[
            ButtonComponent(style="primary", color="#EC4899", height="sm", action=URIAction(label="🏪 前往官方全館賣場", uri=MAIN_SHOP_URL)),
            BoxComponent(layout="horizontal", spacing="sm", contents=[
                ButtonComponent(style="primary", color="#10B981", height="sm", action=URIAction(label="💌 問閨蜜", uri=share_uri)),
                ButtonComponent(style="primary", color="#A855F7", height="sm", action=URIAction(label="🧵 發脆文", uri=threads_uri))
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
    line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="🌸 每日氣溫浪漫穿搭 ＆ 韓系可愛選品館已啟動", contents=card))

@handler.add(MessageEvent, message=TextMessage)
def on_text(event):
    uid = event.source.user_id
    uname = get_user_name(uid)
    txt = event.message.text.strip()

    try:
        if any(k in txt for k in ["星座", "開運", "雙魚", "巨蟹", "天蠍", "天秤", "水瓶", "雙子", "牡羊", "獅子", "射手", "處女", "金牛", "摩羯"]):
            app_uri = f"{RENDER_BASE_URL}/ootd_app?openExternalBrowser=1"
            z_msg = (
                "✨【今日星座戀愛 ＆ 開運穿搭色占卜】\n"
                "♓ 水象星座（雙魚/巨蟹/天蠍）：開運色【櫻花粉＆奶杏白】，桃花指數 99%！\n"
                "♎ 風象星座（天秤/水瓶/雙子）：開運色【晴空藍＆燕麥白】，貴人運爆棚！\n"
                "♈ 火象星座（牡羊/獅子/射手）：開運色【蜜桃珊瑚粉】，元氣魅力滿分！\n"
                "♍ 土象星座（處女/金牛/摩羯）：開運色【焦糖奶杏色】，高級質感爆表！\n"
                f"🌸 點擊開啟浪漫選品櫥窗挑選開運單品：\n{app_uri}"
            )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=z_msg))
            return

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
                f"🌸 點擊開啟浪漫選品櫥窗搶購整套優惠組：\n{app_uri}"
            )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=advice))
            return

        if any(k in txt for k in ["折扣碼", "優惠碼", "免運", "折價券"]):
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🎟️【仙女 VIP 專屬隱藏優惠口令】\n專屬折扣碼：FAIRY88\n✨ 滿額現折再享超商免運優惠！\n🛍️ 立即前往官方賣場使用：\n{MAIN_SHOP_URL}"))
            return

        if txt.startswith("尺碼"):
            nums = re.findall(r"\d+(?:\.\d+)?", txt)
            h = float(next(iter(nums), 160.0))
            w = float(nums) if len(nums) >= 2 else 52.0
            bmi = w / ((h / 100.0) ** 2)
            sz = "S 碼（修身精緻版型）" if bmi < 19.5 else ("M 碼（標準韓系微寬鬆顯瘦）" if bmi < 22.5 else ("L 碼（舒適遮肉顯瘦版型）" if bmi < 25.5 else "XL 碼（慵懶藏肉版型）"))
            app_uri = f"{RENDER_BASE_URL}/ootd_app?openExternalBrowser=1"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"📏【AI 網購尺碼精算結果】\n身高 {int(h)}cm / 體重 {int(w)}kg\n👗 推薦拿：【{sz}】\n🌸 立即前往浪漫選品櫥窗挑選同款：\n{app_uri}"))
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
                "🎀 今日幸運色：【櫻花蜜桃粉】！搭配珍珠耳飾或貝雷帽，氣色瞬間白兩階！",
                "☕ 今日幸運搭配：【法式方領上衣 ＋ 貓爪保溫杯】！優雅又省錢的辦公室女神標配！"
            ]
            pick = random.choice(prizes)
            app_uri = f"{RENDER_BASE_URL}/ootd_app?openExternalBrowser=1"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🎰 {pick}\n\n🌸 點擊逛逛今日幸運色同款女裝與小物：\n{app_uri}"))
            return

        matched = [x for x in CUTE_SHOP_ITEMS if isinstance(x, dict) and any(k in txt for k in ["針織", "外套", "褲", "化妝包", "杯", "帽", "三件套"])]
        if matched and txt not in ["穿搭", "可愛小物"]:
            it = next(iter(matched), {})
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🔍 為您找到相關浪漫爆款選品：\n\n{it.get('badge','')} {it.get('name','')}\n💰 優惠價：{it.get('price','')}（原價 {it.get('orig','')}）\n✨ {it.get('desc','')}\n\n🛍️ 立即搶購：\n{it.get('url', MAIN_SHOP_URL)}"))
            return

        card = make_ootd_shop_card()
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="🌸 每日氣溫浪漫穿搭 ＆ 韓系可愛選品館", contents=card))
    except Exception as e:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🌸 系統小提示：{str(e)[:60]}（請輸入「穿搭」刷新畫面）"))
