import telebot
from telebot import types
import yt_dlp
import os
import time
import json
import datetime
from keep_alive import keep_alive

# ==========================================
# ⚙️ কনফিগারেশন এবং সেটআপ
# ==========================================
API_TOKEN = '8550545241:AAH2DibdXWUdtdMCLmjgGq1wT0VwpHbdcFY' 
ADMIN_ID = 6243881362
CHANNEL_ID = -1002879589597
CHANNEL_LINK = 'https://t.me/RedX_Developer' # আপনার চ্যানেলের লিংক
NAGAD_NUMBER = "01812774257"

bot = telebot.TeleBot(API_TOKEN)

# ফাইল পাথ
USER_DB = "database.json"
TRX_DB = "transactions.json"
VERIFIED_DB = "verified_rules.txt"

# প্যাকেজ কনফিগারেশন
PLANS = {
    "free": {"name": "Free Plan", "limit": 10, "price": 0, "days": 9999},
    "plan1": {"name": "Basic (7 Days)", "limit": 40, "price": 100, "days": 7},
    "plan2": {"name": "Standard (15 Days)", "limit": 60, "price": 250, "days": 15},
    "plan3": {"name": "Premium (30 Days)", "limit": 999999, "price": 700, "days": 30}
}

# ==========================================
# 💾 ডাটাবেস সিস্টেম (JSON + TXT)
# ==========================================
def load_db(file):
    if not os.path.exists(file):
        with open(file, 'w') as f: json.dump({}, f)
    try:
        with open(file, 'r') as f: return json.load(f)
    except: return {}

def save_db(file, data):
    with open(file, 'w') as f: json.dump(data, f, indent=4)

# রুলস সম্মতি ডাটাবেস
verified_users = set()
if os.path.exists(VERIFIED_DB):
    with open(VERIFIED_DB, "r") as f:
        for line in f: verified_users.add(int(line.strip()))

def save_verified_user(chat_id):
    if chat_id not in verified_users:
        verified_users.add(chat_id)
        with open(VERIFIED_DB, "a") as f: f.write(f"{chat_id}\n")

# ইউজার ডেটা ম্যানেজমেন্ট
def get_user(user_id):
    users = load_db(USER_DB)
    str_id = str(user_id)
    today = str(datetime.date.today())

    if str_id not in users:
        users[str_id] = {
            "plan": "free",
            "expiry": None,
            "downloads_today": 0,
            "last_date": today,
            "lang": "bn", # ডিফল্ট বাংলা
            "referrals": 0,
            "joined_date": today
        }
        save_db(USER_DB, users)
    
    # দৈনিক লিমিট রিসেট এবং মেয়াদ চেক
    user = users[str_id]
    if user.get("last_date") != today:
        user["last_date"] = today
        user["downloads_today"] = 0
        
        # সাবস্ক্রিপশন মেয়াদ চেক
        if user["plan"] != "free" and user["expiry"]:
            exp_date = datetime.datetime.strptime(user["expiry"], "%Y-%m-%d").date()
            if datetime.date.today() > exp_date:
                user["plan"] = "free"
                user["expiry"] = None
                bot.send_message(user_id, "⚠️ **আপনার সাবস্ক্রিপশনের মেয়াদ শেষ!**\nআপনাকে ফ্রি প্যাকেজে শিফট করা হয়েছে।")
        
        users[str_id] = user
        save_db(USER_DB, users)
        
    return users[str_id]

def update_user(user_id, data):
    users = load_db(USER_DB)
    users[str(user_id)] = data
    save_db(USER_DB, users)

# ==========================================
# 🔐 হেল্পার ফাংশন (Force Sub & Logic)
# ==========================================
def check_force_sub(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['creator', 'administrator', 'member']
    except: return True 

# ভাষা অভিধান
LANG = {
    "bn": {
        "welcome": "স্বাগতম", "download": "⬇️ ডাউনলোড", "sub": "💎 সাবস্ক্রিপশন", 
        "support": "👨‍💻 সাপোর্ট", "profile": "👤 প্রোফাইল", "lang": "🌐 ভাষা/Lang",
        "limit_over": "⚠️ আজকের লিমিট শেষ! প্রিমিয়াম কিনুন।", "link_ask": "🔗 আপনার ভিডিওর লিংক দিন:"
    },
    "en": {
        "welcome": "Welcome", "download": "⬇️ Download", "sub": "💎 Subscription", 
        "support": "👨‍💻 Support", "profile": "👤 Profile", "lang": "🌐 Language",
        "limit_over": "⚠️ Daily limit over! Buy Premium.", "link_ask": "🔗 Send your video link:"
    }
}

# ==========================================
# 🚀 স্টার্ট কমান্ড ও মেনু
# ==========================================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    user_data = get_user(user_id) # ডাটাবেস ইনিশিয়ালাইজ
    
    # ফোর্স সাবস্ক্রিপশন চেক
    if not check_force_sub(user_id):
        show_force_sub_message(user_id)
        return

    # রুলস সম্মতি চেক
    if user_id in verified_users:
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
        "• কপিরাইট দায়ভার ইউজারের\n"
        "• স্প্যামিং নিষিদ্ধ\n\n"
        "বট ব্যবহার করে আপনি এই শর্তাবলীতে সম্মত হচ্ছেন।"
    )
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub_callback(call):
    if check_force_sub(call.message.chat.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        # সাবস্ক্রাইব করার পর আবার রুলস চেক
        if call.message.chat.id in verified_users:
            show_main_menu(call.message.chat.id)
        else:
            show_rules(call.message.chat.id, call.from_user.first_name)
    else:
        bot.answer_callback_query(call.id, "❌ আপনি এখনো জয়েন করেননি!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "agree_terms")
def agree_terms_callback(call):
    save_verified_user(call.message.chat.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "ধন্যবাদ! স্বাগতম।")
    show_main_menu(call.message.chat.id)

def show_main_menu(user_id):
    user = get_user(user_id)
    ln = LANG[user['lang']]
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(ln['download'], ln['sub'])
    markup.add(ln['profile'], ln['support'])
    markup.add(ln['lang'])
    
    limit = PLANS[user['plan']]['limit']
    limit_display = "Unlimited" if limit > 90000 else limit
    
    text = (
        f"👋 **{ln['welcome']}! {bot.get_chat(user_id).first_name}**\n\n"
        f"📦 বর্তমান প্ল্যান: **{PLANS[user['plan']]['name']}**\n"
        f"📊 আজকের লিমিট: **{user['downloads_today']}/{limit_display}**\n\n"
        "🔗 **Auto Link Detection:** চালু আছে। যেকোনো লিংক দিলেই হবে!\n"
        "👇 নিচের মেনু ব্যবহার করুন:"
    )
    bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")

# ==========================================
# 💎 সাবস্ক্রিপশন ও পেমেন্ট সিস্টেম
# ==========================================
@bot.message_handler(func=lambda m: m.text in ["💎 সাবস্ক্রিপশন", "💎 Subscription"])
def subscription_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Basic - 100৳ (7 Days - 40 DL/Day)", callback_data="buy_plan1"),
        types.InlineKeyboardButton("Standard - 250৳ (15 Days - 60 DL/Day)", callback_data="buy_plan2"),
        types.InlineKeyboardButton("Premium - 700৳ (30 Days - Unlimited)", callback_data="buy_plan3")
    )
    bot.send_message(message.chat.id, "💎 **প্রিমিয়াম প্ল্যান সমূহ:**\nপছন্দের প্যাকেজ সিলেক্ট করুন 👇", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def payment_instruction(call):
    plan_code = call.data.split("_")[1]
    plan = PLANS[plan_code]
    
    text = (
        f"🛒 **প্যাকেজ:** {plan['name']}\n"
        f"💰 **টাকা:** {plan['price']}৳\n\n"
        f"💳 **পেমেন্ট মেথড (Nagad Personal):**\n"
        f"নাম্বার: `{NAGAD_NUMBER}` (Send Money)\n\n"
        "⚠️ **নিয়মাবলী:**\n"
        "১. উপরের নাম্বারে টাকা সেন্ড মানি করুন।\n"
        "২. এরপর নিচে আপনার **Transaction ID (TrxID)** টি লিখে পাঠান।\n\n"
        "উদাহরণ: `TXN12345678`"
    )
    msg = bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_payment, plan_code)

def process_payment(message, plan_code):
    trx_id = message.text.strip()
    user_id = message.chat.id
    
    # অ্যাডমিনের কাছে রিকুয়েস্ট পাঠানো
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"appr_{user_id}_{plan_code}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"rej_{user_id}")
    )
    
    admin_text = (
        f"🔔 **নতুন পেমেন্ট রিকুয়েস্ট!**\n"
        f"👤 ইউজার: {message.from_user.first_name} (`{user_id}`)\n"
        f"📦 প্ল্যান: {PLANS[plan_code]['name']}\n"
        f"💰 টাকা: {PLANS[plan_code]['price']}৳\n"
        f"🧾 **TrxID:** `{trx_id}`"
    )
    bot.send_message(ADMIN_ID, admin_text, reply_markup=markup, parse_mode="Markdown")
    bot.send_message(user_id, "✅ **তথ্য জমা হয়েছে!**\nঅ্যাডমিন যাচাই করার পর আপনার প্ল্যান চালু হবে।")

# ==========================================
# 👮‍♂️ অ্যাডমিন অ্যাকশন
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith(("appr_", "rej_")))
def admin_decision(call):
    if call.message.chat.id != ADMIN_ID: return
    
    data = call.data.split("_")
    action = data[0]
    target_id = data[1]
    
    if action == "rej":
        bot.edit_message_text(f"❌ Rejected request for {target_id}", ADMIN_ID, call.message.message_id)
        bot.send_message(target_id, "❌ **দুঃখিত!** আপনার পেমেন্ট বাতিল করা হয়েছে। সঠিক তথ্য দিন বা সাপোর্টে যোগাযোগ করুন।")
        
    elif action == "appr":
        plan_code = data[2]
        plan = PLANS[plan_code]
        
        # ইউজার আপডেট
        user = get_user(target_id)
        user["plan"] = plan_code
        expiry = datetime.date.today() + datetime.timedelta(days=plan['days'])
        user["expiry"] = str(expiry)
        update_user(target_id, user)
        
        bot.edit_message_text(f"✅ Approved {plan['name']} for {target_id}", ADMIN_ID, call.message.message_id)
        
        success_msg = (
            f"🎉 **অভিনন্দন!**\n"
            f"আপনার **{plan['name']}** চালু হয়েছে!\n"
            f"📅 মেয়াদ শেষ: {expiry}\n"
            f"🚀 এখন থেকে আপনি দৈনিক লিমিট অনুযায়ী ডাউনলোড করতে পারবেন।"
        )
        bot.send_message(target_id, success_msg, parse_mode="Markdown")

@bot.message_handler(commands=['admin', 'stats'])
def admin_stats(message):
    if message.chat.id == ADMIN_ID:
        users = load_db(USER_DB)
        total = len(users)
        paid = sum(1 for u in users.values() if u['plan'] != 'free')
        bot.reply_to(message, f"📊 **Admin Stats**\n👥 Total Users: {total}\n💎 Paid Users: {paid}")

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.chat.id == ADMIN_ID:
        msg = message.text.replace('/broadcast', '').strip()
        if not msg: return
        users = load_db(USER_DB)
        count = 0
        for uid in users:
            try:
                bot.send_message(uid, f"📢 **Swygen Notice:**\n{msg}", parse_mode="Markdown")
                count += 1
                time.sleep(0.05)
            except: pass
        bot.reply_to(message, f"✅ Sent to {count} users.")

# ==========================================
# 📥 অল-ইন-ওয়ান ডাউনলোডার ও প্লাটফর্ম মেনু
# ==========================================
# গ্লোবাল ভেরিয়েবল
download_queue = {}
platform_select = {}

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    text = message.text
    user_id = message.chat.id
    user = get_user(user_id)
    ln = LANG[user['lang']]

    # সাপোর্ট হ্যান্ডলিং
    if text in ["👨‍💻 সাপোর্ট", "👨‍💻 Support"]:
        bot.send_message(user_id, "📞 **Live Support:**\nআপনার সমস্যা লিখে পাঠান, অ্যাডমিন রিপ্লাই দেবেন।", parse_mode="Markdown")
        bot.register_next_step_handler(message, forward_support)
        return

    # প্রোফাইল
    if text in ["👤 প্রোফাইল", "👤 Profile"]:
        limit = PLANS[user['plan']]['limit']
        lim_str = "Unlimited" if limit > 90000 else limit
        msg = (
            f"👤 **Name:** {message.from_user.first_name}\n"
            f"🆔 **ID:** `{user_id}`\n"
            f"📦 **Plan:** {PLANS[user['plan']]['name']}\n"
            f"📊 **Usage:** {user['downloads_today']}/{lim_str}\n"
            f"📅 **Expiry:** {user['expiry'] if user['expiry'] else 'Lifetime'}"
        )
        bot.send_message(user_id, msg, parse_mode="Markdown")
        return

    # ভাষা পরিবর্তন
    if text in ["🌐 ভাষা/Lang", "🌐 Language"]:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🇧🇩 বাংলা", callback_data="set_bn"),
                   types.InlineKeyboardButton("🇺🇸 English", callback_data="set_en"))
        bot.send_message(user_id, "Select Language / ভাষা নির্বাচন করুন:", reply_markup=markup)
        return

    # ডাউনলোড মেনু (NEW REQUIREMENT: Platform Selection)
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
            f"👋 **{user_name}**, আপনি কোন প্লাটফর্মের Watermark ছাড়া ভিডিও ডাউনলোড করতে চান?\n\n"
            "👇 নিচের বাটন থেকে সিলেক্ট করুন:"
        )
        bot.send_message(user_id, msg_text, reply_markup=markup, parse_mode="Markdown")
        return

    # 🔗 অটো লিংক ডিটেকশন (Direct Link)
    if any(x in text.lower() for x in ["tiktok.com", "facebook.com", "instagram.com", "youtu", "reel"]):
        process_link_logic(user_id, text, user)

def forward_support(message):
    if message.chat.id != ADMIN_ID:
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "✅ Message sent to Admin.")

# ভাষা সেটিং
@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def set_language(call):
    lang = call.data.split("_")[1]
    user = get_user(call.message.chat.id)
    user['lang'] = lang
    update_user(call.message.chat.id, user)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_main_menu(call.message.chat.id)

# প্লাটফর্ম সিলেকশন হ্যান্ডলার
@bot.callback_query_handler(func=lambda call: call.data.startswith("plat_"))
def platform_selected(call):
    plat = call.data.split("_")[1].capitalize()
    user_id = call.message.chat.id
    
    msg = bot.send_message(user_id, f"🔗 দয়া করে আপনার **{plat}** ভিডিওর লিংকটি দিন:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, link_input_handler)

def link_input_handler(message):
    user_id = message.chat.id
    url = message.text
    user = get_user(user_id)
    process_link_logic(user_id, url, user)

def process_link_logic(user_id, url, user):
    # লিমিট চেক
    limit = PLANS[user['plan']]['limit']
    if user['downloads_today'] >= limit:
        bot.send_message(user_id, LANG[user['lang']]['limit_over'])
        return

    download_queue[user_id] = url
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🎬 Video (No Watermark/HD)", callback_data="dl_vid"),
        types.InlineKeyboardButton("🎵 Audio (MP3)", callback_data="dl_aud"),
        types.InlineKeyboardButton("🖼 Thumbnail", callback_data="dl_thumb")
    )
    bot.send_message(user_id, "📥 **Select Option:**", reply_markup=markup)

# ডাউনলোড এক্সিকিউশন
@bot.callback_query_handler(func=lambda call: call.data.startswith("dl_"))
def execute_download(call):
    user_id = call.message.chat.id
    if user_id not in download_queue:
        bot.send_message(user_id, "⚠️ **Link expired!** Please send again.")
        return
        
    url = download_queue[user_id]
    mode = call.data.split("_")[1]
    
    # লিমিট রি-চেক
    user = get_user(user_id)
    if user['downloads_today'] >= PLANS[user['plan']]['limit']:
        bot.send_message(user_id, "⚠️ Limit Over!")
        return

    msg = bot.edit_message_text("🚀 **Swygen Engine:** Processing...", user_id, call.message.message_id, parse_mode="Markdown")

    try:
        file_name = f"Swygen_{user_id}_{int(time.time())}"
        ydl_opts = {'quiet': True, 'no_warnings': True}

        if mode == "vid":
            file_name += ".mp4"
            ydl_opts.update({
                'format': 'bestvideo+bestaudio/best',
                'outtmpl': file_name,
                'merge_output_format': 'mp4'
            })
        elif mode == "aud":
            file_name += ".mp3"
            ydl_opts.update({
                'format': 'bestaudio/best',
                'outtmpl': file_name,
                'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]
            })
        elif mode == "thumb":
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                thumb_url = info.get('thumbnail')
                bot.send_photo(user_id, thumb_url, caption="🖼 **Thumbnail**\n🏷 Brand: Swygen IT")
                bot.delete_message(user_id, msg.message_id)
                return

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        bot.send_chat_action(user_id, 'upload_document')
        with open(file_name, 'rb') as f:
            caption = (
                "✅ **Download Complete!**\n"
                "────────────────\n"
                "🏷 **Brand:** Swygen IT\n"
                "🛠 **Dev:** Ayman Hasan Shaan"
            )
            if mode == "aud":
                bot.send_audio(user_id, f, caption=caption, parse_mode="Markdown")
            else:
                bot.send_video(user_id, f, caption=caption, parse_mode="Markdown")

        # কাউন্ট আপডেট
        user['downloads_today'] += 1
        update_user(user_id, user)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🌐 Visit Swygen.xyz", url="https://swygen.xyz"))
        bot.send_message(user_id, "❤️ Thanks for using Swygen IT!", reply_markup=markup)

        bot.delete_message(user_id, msg.message_id)
        if os.path.exists(file_name): os.remove(file_name)

    except Exception as e:
        bot.edit_message_text("❌ **Failed!** Link might be private or invalid.", user_id, msg.message_id)
        if os.path.exists(file_name): 
            try: os.remove(file_name)
            except: pass

keep_alive()
bot.polling(none_stop=True)
