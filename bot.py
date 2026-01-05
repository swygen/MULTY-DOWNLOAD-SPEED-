import telebot
from telebot import types
import yt_dlp
import os
import time
import datetime
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from keep_alive import keep_alive

# ==========================================
# ⚙️ কনফিগারেশন এবং সেটআপ
# ==========================================
API_TOKEN = '8550545241:AAH2DibdXWUdtdMCLmjgGq1wT0VwpHbdcFY'  
ADMIN_ID = 6243881362
CHANNEL_ID = -1002879589597
CHANNEL_LINK = 'https://t.me/SWYMULTIDWNLDBOT' # আপনার চ্যানেলের লিংক
NAGAD_NUMBER = "01812774257"

# 🔥 MongoDB কানেকশন
# TODO: <db_password> কেটে আপনার আসল পাসওয়ার্ড বসান
MONGO_URI = "mongodb+srv://u818920_db_user:AHZjnManBGVIcX3u@cluster0.6j1jk9d.mongodb.net/?appName=Cluster0"

try:
    client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
    client.admin.command('ping')
    print("✅ MongoDB Connected Successfully!")
    
    db = client['swygen_bot_db']
    users_col = db['users'] # ইউজার কালেকশন
    
except Exception as e:
    print(f"❌ MongoDB Connection Error: {e}")

bot = telebot.TeleBot(API_TOKEN)

# প্যাকেজ কনফিগারেশন
PLANS = {
    "free": {"name": "Free Plan", "limit": 10, "price": 0, "days": 9999},
    "plan1": {"name": "Basic (7 Days)", "limit": 40, "price": 100, "days": 7},
    "plan2": {"name": "Standard (15 Days)", "limit": 60, "price": 250, "days": 15},
    "plan3": {"name": "Premium (30 Days)", "limit": 999999, "price": 700, "days": 30}
}

# ==========================================
# 💾 ডাটাবেস ফাংশন (MongoDB Logic - Fixed)
# ==========================================

def get_user(user_id):
    user_id = int(user_id)
    today_str = str(datetime.date.today())
    
    user = users_col.find_one({"_id": user_id})

    # নতুন ইউজার তৈরি
    if not user:
        user = {
            "_id": user_id,
            "plan": "free",
            "expiry": None,
            "downloads_today": 0,
            "last_date": today_str,
            "lang": "bn",
            "referrals": 0,
            "joined_date": today_str,
            "is_verified": False 
        }
        users_col.insert_one(user)
        return user

    # আপডেট লজিক (মেয়াদ এবং লিমিট চেক)
    updates = {}
    
    # ১. তারিখ পরিবর্তন হলে লিমিট রিসেট
    if user.get("last_date") != today_str:
        updates["last_date"] = today_str
        updates["downloads_today"] = 0
        user["last_date"] = today_str
        user["downloads_today"] = 0

    # ২. সাবস্ক্রিপশন মেয়াদ চেক (Bug Fix)
    if user["plan"] != "free" and user.get("expiry"):
        try:
            exp_date = datetime.datetime.strptime(user["expiry"], "%Y-%m-%d").date()
            # যদি আজকের তারিখ মেয়াদের চেয়ে বড় হয় -> Expired
            if datetime.date.today() > exp_date:
                updates["plan"] = "free"
                updates["expiry"] = None
                user["plan"] = "free"
                bot.send_message(user_id, "⚠️ **আপনার সাবস্ক্রিপশনের মেয়াদ শেষ!**\nআপনাকে ফ্রি প্যাকেজে শিফট করা হয়েছে।")
        except:
            updates["plan"] = "free" # ডেট ফরম্যাট ভুল হলে সেফটির জন্য ফ্রি

    # ডাটাবেস আপডেট
    if updates:
        users_col.update_one({"_id": user_id}, {"$set": updates})

    return user

def update_user_field(user_id, field, value):
    users_col.update_one({"_id": int(user_id)}, {"$set": {field: value}})

def increment_download(user_id):
    users_col.update_one({"_id": int(user_id)}, {"$inc": {"downloads_today": 1}})

def increment_referral(referrer_id):
    users_col.update_one({"_id": int(referrer_id)}, {"$inc": {"referrals": 1}})

# ==========================================
# 🔐 হেল্পার ও ভাষা
# ==========================================
def check_force_sub(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['creator', 'administrator', 'member']
    except: return True 

LANG = {
    "bn": {
        "welcome": "স্বাগতম", "download": "⬇️ ডাউনলোড", "sub": "💎 সাবস্ক্রিপশন", 
        "support": "👨‍💻 সাপোর্ট", "profile": "👤 প্রোফাইল", "lang": "🌐 ভাষা/Lang", "ref": "👥 রেফারাল",
        "limit_over": "⚠️ আজকের ফ্রি লিমিট শেষ! আনলিমিটেড ডাউনলোড করতে সাবস্ক্রিপশন নিন।", 
        "link_ask": "🔗 আপনার ভিডিওর লিংক দিন:"
    },
    "en": {
        "welcome": "Welcome", "download": "⬇️ Download", "sub": "💎 Subscription", 
        "support": "👨‍💻 Support", "profile": "👤 Profile", "lang": "🌐 Language", "ref": "👥 Referral",
        "limit_over": "⚠️ Daily limit over! Buy Premium for unlimited access.", 
        "link_ask": "🔗 Send your video link:"
    }
}

# ==========================================
# 🚀 বট লজিক শুরু
# ==========================================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    user = get_user(user_id) # ডাটাবেস চেক
    
    # রেফারাল সিস্টেম
    text_split = message.text.split()
    if len(text_split) > 1:
        try:
            referrer_id = int(text_split[1])
            if referrer_id != user_id:
                # চেক করা এই ইউজার আগে জয়েন করেছে কিনা, না হলে রেফারাল কাউন্ট
                if user['joined_date'] == str(datetime.date.today()) and user['downloads_today'] == 0:
                     increment_referral(referrer_id)
        except: pass

    # ফোর্স সাবস্ক্রিপশন
    if not check_force_sub(user_id):
        show_force_sub_message(user_id)
        return

    # রুলস ভেরিফিকেশন চেক
    if user.get("is_verified", False):
        show_main_menu(user_id)
    else:
        show_rules(user_id, message.from_user.first_name)

def show_force_sub_message(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
    markup.add(types.InlineKeyboardButton("✅ Joined", callback_data="check_sub"))
    bot.send_message(chat_id, "⚠️ **বট ব্যবহার করতে আমাদের চ্যানেলে জয়েন করুন:**", reply_markup=markup)

def show_rules(chat_id, user_name):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ আমি সম্মত", callback_data="agree_terms"))
    text = (
        f"👋 **স্বাগতম! {user_name}**\n\n"
        "Swygen IT বটের মাধ্যমে আপনি TikTok, Facebook, Instagram, YouTube ভিডিও ডাউনলোড করতে পারবেন।\n\n"
        "📜 **ব্যবহার নীতিমালা:**\n"
        "• শুধুমাত্র বৈধ ব্যবহারের জন্য\n"
        "• কপিরাইট দায়ভার ইউজারের\n\n"
        "বট ব্যবহার করে আপনি এই শর্তাবলীতে সম্মত হচ্ছেন।"
    )
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub_callback(call):
    if check_force_sub(call.message.chat.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        user = get_user(call.message.chat.id)
        if user.get("is_verified", False):
            show_main_menu(call.message.chat.id)
        else:
            show_rules(call.message.chat.id, call.from_user.first_name)
    else:
        bot.answer_callback_query(call.id, "❌ আপনি এখনো জয়েন করেননি!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "agree_terms")
def agree_terms_callback(call):
    # MongoDB তে ভেরিফাইড আপডেট (পার্মানেন্ট)
    update_user_field(call.message.chat.id, "is_verified", True)
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "ধন্যবাদ! স্বাগতম।")
    show_main_menu(call.message.chat.id)

def show_main_menu(user_id):
    user = get_user(user_id)
    ln = LANG[user['lang']]
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(ln['download'], ln['sub'])
    markup.add(ln['profile'], ln['support'])
    markup.add(ln['ref'], ln['lang'])
    
    limit = PLANS[user['plan']]['limit']
    limit_display = "Unlimited" if limit > 90000 else limit
    
    text = (
        f"👋 **{ln['welcome']}! {bot.get_chat(user_id).first_name}**\n\n"
        f"📦 বর্তমান প্ল্যান: **{PLANS[user['plan']]['name']}**\n"
        f"📊 আজকের ব্যবহার: **{user['downloads_today']}/{limit_display}**\n\n"
        "👇 নিচের মেনু ব্যবহার করুন:"
    )
    bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")

# ==========================================
# 💎 সাবস্ক্রিপশন ও পেমেন্ট (MongoDB)
# ==========================================
@bot.message_handler(func=lambda m: m.text in ["💎 সাবস্ক্রিপশন", "💎 Subscription"])
def subscription_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Basic - 100৳ (7 Days)", callback_data="buy_plan1"),
        types.InlineKeyboardButton("Standard - 250৳ (15 Days)", callback_data="buy_plan2"),
        types.InlineKeyboardButton("Premium - 700৳ (30 Days)", callback_data="buy_plan3")
    )
    bot.send_message(message.chat.id, "💎 **প্রিমিয়াম প্ল্যান সমূহ:**\nপছন্দের প্যাকেজ সিলেক্ট করুন 👇", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def payment_instruction(call):
    plan_code = call.data.split("_")[1]
    plan = PLANS[plan_code]
    text = (
        f"🛒 **প্যাকেজ:** {plan['name']}\n💰 **টাকা:** {plan['price']}৳\n\n"
        f"💳 **Nagad Personal:** `{NAGAD_NUMBER}`\n\n"
        "টাকা পাঠানোর পর নিচে **TrxID** টি লিখে পাঠান।"
    )
    msg = bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_payment, plan_code)

def process_payment(message, plan_code):
    trx_id = message.text.strip()
    user_id = message.chat.id
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"appr_{user_id}_{plan_code}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"rej_{user_id}")
    )
    admin_text = f"🔔 **New Payment!**\n👤 User: `{user_id}`\n📦 Plan: {PLANS[plan_code]['name']}\n🧾 TrxID: `{trx_id}`"
    bot.send_message(ADMIN_ID, admin_text, reply_markup=markup, parse_mode="Markdown")
    bot.send_message(user_id, "✅ **তথ্য জমা হয়েছে!** অ্যাডমিন চেক করে অ্যাক্টিভ করে দেবেন।")

@bot.callback_query_handler(func=lambda call: call.data.startswith(("appr_", "rej_")))
def admin_decision(call):
    if call.message.chat.id != ADMIN_ID: return
    data = call.data.split("_")
    action, target_id = data[0], int(data[1])
    
    if action == "rej":
        bot.edit_message_text(f"❌ Rejected for {target_id}", ADMIN_ID, call.message.message_id)
        bot.send_message(target_id, "❌ **পেমেন্ট বাতিল করা হয়েছে।**")
    elif action == "appr":
        plan_code = data[2]
        # মেয়াদ সেট করা
        expiry = str(datetime.date.today() + datetime.timedelta(days=PLANS[plan_code]['days']))
        
        # MongoDB তে আপডেট (এটি পার্মানেন্ট)
        users_col.update_one(
            {"_id": target_id}, 
            {"$set": {"plan": plan_code, "expiry": expiry}}
        )
        
        bot.edit_message_text(f"✅ Approved {plan_code} for {target_id}", ADMIN_ID, call.message.message_id)
        bot.send_message(target_id, f"🎉 **অভিনন্দন!** আপনার **{PLANS[plan_code]['name']}** প্যাকেজ চালু হয়েছে।")

# ==========================================
# 📥 অ্যাডভান্সড ডাউনলোড মেনু
# ==========================================
download_queue = {}

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    text = message.text
    user_id = message.chat.id
    user = get_user(user_id) # ডাটা চেক
    ln = LANG[user['lang']]

    if text in ["👨‍💻 সাপোর্ট", "👨‍💻 Support"]:
        bot.send_message(user_id, "📞 সমস্যা লিখে পাঠান:", parse_mode="Markdown")
        bot.register_next_step_handler(message, lambda m: bot.forward_message(ADMIN_ID, m.chat.id, m.message_id))
        return

    if text in ["👥 রেফারাল", "👥 Referral"]:
        ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        msg = f"👥 **Referral System**\n\n🔗 Link: `{ref_link}`\n🎁 Total Referrals: {user.get('referrals', 0)}"
        bot.send_message(user_id, msg, parse_mode="Markdown")
        return

    if text in ["👤 প্রোফাইল", "👤 Profile"]:
        limit = PLANS[user['plan']]['limit']
        lim_str = "Unlimited" if limit > 90000 else limit
        bot.send_message(user_id, f"👤 **Profile**\n📦 Plan: {PLANS[user['plan']]['name']}\n📊 Limit: {user['downloads_today']}/{lim_str}\n📅 Expiry: {user['expiry']}", parse_mode="Markdown")
        return

    if text in ["🌐 ভাষা/Lang", "🌐 Language"]:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🇧🇩 বাংলা", callback_data="set_bn"), types.InlineKeyboardButton("🇺🇸 English", callback_data="set_en"))
        bot.send_message(user_id, "Select Language:", reply_markup=markup)
        return

    # ⬇️ অ্যাডভান্সড ডাউনলোড মেনু
    if text in ["⬇️ ডাউনলোড", "⬇️ Download"]:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🎵 TikTok", callback_data="plat_tiktok"),
            types.InlineKeyboardButton("📘 Facebook", callback_data="plat_facebook"),
            types.InlineKeyboardButton("📸 Instagram", callback_data="plat_instagram"),
            types.InlineKeyboardButton("📺 YouTube", callback_data="plat_youtube")
        )
        
        user_name = message.from_user.first_name
        msg_text = (
            f"👋 **{user_name}**, আপনি কোন প্লাটফর্মের **Watermark ছাড়া** ভিডিও ডাউনলোড করতে চান?\n\n"
            "👇 নিচের বাটন থেকে সিলেক্ট করুন:"
        )
        bot.send_message(user_id, msg_text, reply_markup=markup, parse_mode="Markdown")
        return

    # Auto Link Logic
    if any(x in text.lower() for x in ["tiktok.com", "facebook.com", "instagram.com", "youtu", "reel"]):
        process_link_logic(user_id, text, user)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def set_language(call):
    lang = call.data.split("_")[1]
    update_user_field(call.message.chat.id, "lang", lang)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_main_menu(call.message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("plat_"))
def platform_selected(call):
    plat = call.data.split("_")[1].capitalize()
    msg = bot.send_message(call.message.chat.id, f"🔗 আপনার **{plat}** ভিডিওর লিংকটি দিন:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: process_link_logic(m.chat.id, m.text, get_user(m.chat.id)))

def process_link_logic(user_id, url, user):
    if user['downloads_today'] >= PLANS[user['plan']]['limit']:
        bot.send_message(user_id, LANG[user['lang']]['limit_over'])
        return
    download_queue[user_id] = url
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🎬 Video (No Watermark)", callback_data="dl_vid"), types.InlineKeyboardButton("🎵 Audio (MP3)", callback_data="dl_aud"), types.InlineKeyboardButton("🖼 Thumbnail", callback_data="dl_thumb"))
    bot.send_message(user_id, "📥 **ফরম্যাট সিলেক্ট করুন:**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("dl_"))
def execute_download(call):
    user_id = call.message.chat.id
    user = get_user(user_id)
    if user['downloads_today'] >= PLANS[user['plan']]['limit']:
        bot.send_message(user_id, "⚠️ Limit Over!")
        return

    url = download_queue.get(user_id)
    if not url: return bot.send_message(user_id, "⚠️ Link Expired")
    
    msg = bot.edit_message_text("🚀 Processing...", user_id, call.message.message_id)
    mode = call.data.split("_")[1]
    file_name = f"swygen_{user_id}_{int(time.time())}"
    
    try:
        ydl_opts = {'quiet': True, 'format': 'bestvideo+bestaudio/best', 'outtmpl': file_name + '.mp4'}
        if mode == 'aud': ydl_opts['format'] = 'bestaudio/best'; ydl_opts['outtmpl'] = file_name + '.mp3'
        elif mode == 'thumb':
             with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                thumb = info.get('thumbnail')
                bot.send_photo(user_id, thumb, caption="✅ Swygen IT")
                bot.delete_message(user_id, msg.message_id)
                return

        with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
        
        bot.send_chat_action(user_id, 'upload_document')
        ext = '.mp3' if mode == 'aud' else '.mp4'
        with open(file_name + ext, 'rb') as f:
            if mode == 'aud': bot.send_audio(user_id, f, caption="✅ Swygen IT")
            else: bot.send_video(user_id, f, caption="✅ Swygen IT")
        
        # MongoDB কাউন্ট আপডেট
        increment_download(user_id)
        
        bot.delete_message(user_id, msg.message_id)
        os.remove(file_name + ext)
    except Exception as e:
        bot.edit_message_text("❌ Failed", user_id, msg.message_id)

# অ্যাডমিন প্যানেল কমান্ড
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id == ADMIN_ID:
        total = users_col.count_documents({})
        paid = users_col.count_documents({"plan": {"$ne": "free"}})
        bot.reply_to(message, f"📊 **Stats:**\nTotal: {total}\nPaid: {paid}")

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.chat.id == ADMIN_ID:
        msg = message.text.replace('/broadcast', '').strip()
        users = users_col.find({})
        count = 0
        for u in users:
            try: bot.send_message(u['_id'], msg); count += 1; time.sleep(0.05)
            except: pass
        bot.reply_to(message, f"Sent to {count} users")

keep_alive()
bot.polling(none_stop=True)
