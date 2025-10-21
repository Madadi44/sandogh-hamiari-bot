import logging
import json
import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# توکن از محیط
TOKEN = os.environ.get('BOT_TOKEN')

if not TOKEN:
    logging.error("❌ BOT_TOKEN not found!")
    sys.exit(1)

logging.info("✅ توکن ربات با موفقیت بارگذاری شد")

# فایل برای ذخیره داده‌ها
DATA_FILE = "data.json"

def load_data():
    """بارگذاری داده‌ها از فایل"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logging.error(f"خطا در بارگذاری داده‌ها: {e}")
        return {}

def save_data():
    """ذخیره داده‌ها در فایل"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"خطا در ذخیره داده‌ها: {e}")

# بارگذاری داده‌ها
data = load_data()
registration_data = {}

# منوی اصلی
main_keyboard = [
    ["📝 ثبت عضویت", "💳 پرداخت"],
    ["📋 لیست اعضا", "🔄 ویرایش اعضا"],
    ["ℹ️ راهنما"]
]

admin_keyboard = [
    ["📝 ثبت عضویت", "💳 پرداخت"],
    ["📋 لیست اعضا", "🔄 ویرایش اعضا"],
    ["✅ تایید پرداخت", "🗑️ ریست کل اطلاعات"],
    ["ℹ️ راهنما"]
]

def is_admin(update, context):
    """بررسی اینکه کاربر مدیر است یا نه"""
    try:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        member = context.bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except Exception as e:
        logging.error(f"خطا در بررسی ادمین: {e}")
        return False

def start(update, context):
    """دستور شروع"""
    chat_type = update.effective_chat.type
    
    if is_admin(update, context):
        reply_markup = ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True)
    else:
        reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
    
    welcome_text = "🤖 **ربات صندوق همیاری**\n\nلطفاً از دکمه‌های زیر استفاده کنید:"
    
    update.message.reply_text(welcome_text, reply_markup=reply_markup)

def handle_message(update, context):
    """پردازش پیام‌ها"""
    if not update.message or not update.message.text:
        return
    
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "📝 ثبت عضویت":
        start_registration(update, context)
    elif text == "💳 پرداخت":
        show_payment_menu(update, context)
    elif text == "📋 لیست اعضا":
        show_members_list(update, context)
    elif text == "🔄 ویرایش اعضا":
        show_edit_menu(update, context)
    elif text == "✅ تایید پرداخت":
        show_confirm_menu(update, context)
    elif text == "🗑️ ریست کل اطلاعات":
        show_reset_confirmation(update, context)
    elif text == "ℹ️ راهنما":
        show_help(update, context)
    elif user_id in registration_data:
        process_registration(update, context)
    elif context.user_data.get('waiting_for_reset_confirmation'):
        process_reset_confirmation(update, context)

def show_reset_confirmation(update, context):
    """نمایش تاییدیه برای ریست اطلاعات"""
    if not is_admin(update, context):
        update.message.reply_text("❌ فقط مدیران می‌توانند از این قابلیت استفاده کنند.")
        return
    
    group_id = update.effective_chat.id
    
    # بررسی آیا داده‌ای برای ریست وجود دارد
    if group_id not in data or not data[group_id]["members"]:
        update.message.reply_text("❌ هیچ داده‌ای برای ریست کردن وجود ندارد.")
        return
    
    # نمایش اطلاعات فعلی
    total_members = len(data[group_id]["members"])
    total_paid = sum(1 for member in data[group_id]["members"].values() if member["paid"])
    
    confirmation_text = (
        "⚠️ **هشدار: ریست کامل اطلاعات**\n\n"
        f"📊 **وضعیت فعلی:**\n"
        f"• تعداد اعضا: {total_members}\n"
        f"• پرداخت شده: {total_paid}\n"
        f"• در انتظار پرداخت: {total_members - total_paid}\n\n"
        "❌ **این عمل تمام اطلاعات زیر را حذف می‌کند:**\n"
        "• تمام اعضای ثبت‌نام شده\n"
        "• وضعیت پرداخت‌ها\n"
        "• تاریخچه قرعه‌کشی‌ها\n\n"
        "🔁 **شروع دوره جدید از صفر**\n\n"
        "برای تایید، لطفاً عبارت **\"تایید ریست\"** را تایپ کنید:"
    )
    
    context.user_data['waiting_for_reset_confirmation'] = True
    update.message.reply_text(confirmation_text)

def process_reset_confirmation(update, context):
    """پردازش تاییدیه ریست"""
    text = update.message.text
    group_id = update.effective_chat.id
    
    if text.strip() == "تایید ریست":
        # ریست داده‌ها
        if group_id in data:
            # ریست کامل
            data[group_id] = {"members": {}, "winners": [], "current_month": "1403-02"}
            save_data()
            
            # پاک کردن وضعیت ثبت‌نام
            for user_id in list(registration_data.keys()):
                if registration_data[user_id].get("group_id") == group_id:
                    del registration_data[user_id]
            
            context.user_data['waiting_for_reset_confirmation'] = False
            
            success_text = (
                "✅ **ریست کامل اطلاعات انجام شد!**\n\n"
                "🗑️ تمام اطلاعات قبلی حذف شد.\n"
                "🔄 دوره جدید شروع شد.\n\n"
                "📝 اعضا می‌توانند از نو ثبت‌نام کنند."
            )
            update.message.reply_text(success_text)
            
            # اطلاع‌رسانی به گروه
            announcement = "🔄 **شروع دوره جدید**\n\n📝 لطفاً برای دوره جدید ثبت‌نام کنید."
            update.message.reply_text(announcement)
            
        else:
            update.message.reply_text("❌ هیچ داده‌ای برای ریست کردن وجود ندارد.")
    else:
        update.message.reply_text("❌ ریست لغو شد. برای تایید باید عبارت \"تایید ریست\" را تایپ کنید.")
        context.user_data['waiting_for_reset_confirmation'] = False

def start_registration(update, context):
    """شروع ثبت نام"""
    user_id = update.effective_user.id
    group_id = update.effective_chat.id
    
    if group_id not in data:
        data[group_id] = {"members": {}, "winners": [], "current_month": "1403-02"}
    
    existing_members = [uid for uid in data[group_id]["members"] if data[group_id]["members"][uid].get("registered_by") == user_id]
    if existing_members:
        update.message.reply_text("❌ شما قبلاً ثبت نام کرده‌اید.")
        return
    
    registration_data[user_id] = {
        "step": "waiting_for_shares",
        "group_id": group_id,
        "names": [],
        "current_name_index": 0
    }
    
    keyboard = [
        [InlineKeyboardButton("1 سهم", callback_data="shares_1")],
        [InlineKeyboardButton("2 سهم", callback_data="shares_2")],
        [InlineKeyboardButton("3 سهم", callback_data="shares_3")],
        [InlineKeyboardButton("4 سهم", callback_data="shares_4")],
        [InlineKeyboardButton("5 سهم", callback_data="shares_5")],
        [InlineKeyboardButton("📝 تعداد دلخواه", callback_data="custom_shares")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text("📝 **ثبت نام جدید**\n\nلطفاً تعداد سهام را انتخاب کنید:", reply_markup=reply_markup)

def process_registration(update, context):
    """پردازش ثبت نام"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in registration_data:
        return
    
    reg_data = registration_data[user_id]
    step = reg_data.get("step")
    
    if step == "waiting_for_shares":
        try:
            shares_count = int(text)
            if 1 <= shares_count <= 10:
                reg_data["shares_count"] = shares_count
                reg_data["step"] = "waiting_for_names"
                reg_data["current_name_index"] = 1
                update.message.reply_text(f"✅ تعداد {shares_count} سهم ثبت شد.\n\nلطفاً نام شخص اول را وارد کنید:")
            else:
                update.message.reply_text("❌ تعداد سهام باید بین ۱ تا ۱۰ باشد.")
        except ValueError:
            update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید:")
    
    elif step == "waiting_for_names":
        current_index = reg_data["current_name_index"]
        total_shares = reg_data["shares_count"]
        
        if text.strip():
            reg_data["names"].append(text.strip())
            
            if current_index < total_shares:
                reg_data["current_name_index"] += 1
                update.message.reply_text(f"لطفاً نام شخص {current_index + 1} را وارد کنید:")
            else:
                complete_registration(update, reg_data)
                del registration_data[user_id]
        else:
            update.message.reply_text("❌ نام نمی‌تواند خالی باشد.")

def complete_registration(update, reg_data):
    """تکمیل ثبت نام"""
    user_id = update.effective_user.id
    group_id = reg_data["group_id"]
    names = reg_data["names"]
    
    for i, name in enumerate(names):
        member_id = f"{user_id}_{i}"
        data[group_id]["members"][member_id] = {
            "name": name,
            "shares": 1,
            "paid": False,
            "paid_by": None,
            "registered_by": user_id
        }
    
    save_data()
    
    names_list = "\n".join([f"{i+1}. {name}" for i, name in enumerate(names)])
    update.message.reply_text(f"✅ **ثبت نام تکمیل شد!**\n\n📋 اسامی ثبت شده:\n{names_list}")

def show_payment_menu(update, context):
    """منوی پرداخت"""
    user_id = update.effective_user.id
    group_id = update.effective_chat.id
    
    if group_id not in data:
        update.message.reply_text("❌ هیچ عضوی در این گروه ثبت نام نکرده است.")
        return
    
    # پیدا کردن سهام کاربر
    user_members = []
    for member_id, member_data in data[group_id]["members"].items():
        if member_data.get("registered_by") == user_id:
            user_members.append((member_id, member_data))
    
    if not user_members:
        update.message.reply_text("❌ شما در این صندوق عضو نیستید.")
        return
    
    # نمایش وضعیت پرداخت
    members_text = "📋 **لیست سهام شما:**\n\n"
    unpaid_count = 0
    
    for i, (member_id, member_data) in enumerate(user_members, 1):
        status = "✅ پرداخت شده" if member_data["paid"] else "❌ در انتظار پرداخت"
        members_text += f"{i}. {member_data['name']} - {status}\n"
        if not member_data["paid"]:
            unpaid_count += 1
    
    if unpaid_count > 0:
        members_text += f"\n💳 **تعداد پرداخت نشده:** {unpaid_count}"
        members_text += "\n\n📤 **لطفاً رسید پرداخت خود را آپلود کنید**"
    else:
        members_text += "\n✅ **همه سهام شما پرداخت شده است**"
    
    update.message.reply_text(members_text)

def show_members_list(update, context):
    """نمایش لیست اعضا"""
    group_id = update.effective_chat.id
    
    if group_id not in data or not data[group_id]["members"]:
        update.message.reply_text("📝 هنوز هیچ عضوی ثبت نام نکرده است.")
        return
    
    members_list = "📋 **لیست اعضا و وضعیت پرداخت**\n\n"
    total_members = 0
    total_paid = 0
    
    for i, (member_id, member_data) in enumerate(data[group_id]["members"].items(), 1):
        status = "✅" if member_data["paid"] else "❌"
        members_list += f"{i}. {status} {member_data['name']}\n"
        total_members += 1
        if member_data["paid"]:
            total_paid += 1
    
    members_list += f"\n📊 **آمار کلی:**\n"
    members_list += f"• تعداد کل اعضا: {total_members}\n"
    members_list += f"• پرداخت شده: {total_paid}\n"
    members_list += f"• در انتظار پرداخت: {total_members - total_paid}"
    
    update.message.reply_text(members_list)

def show_edit_menu(update, context):
    """منوی ویرایش"""
    update.message.reply_text("🔧 **منوی ویرایش**\n\nاین قابلیت به زودی اضافه می‌شود.")

def show_confirm_menu(update, context):
    """تایید پرداخت"""
    if not is_admin(update, context):
        update.message.reply_text("❌ فقط مدیران می‌توانند از این قابلیت استفاده کنند.")
        return
    
    group_id = update.effective_chat.id
    
    if group_id not in data:
        update.message.reply_text("❌ هیچ عضوی در این گروه ثبت نام نکرده است.")
        return
    
    # پیدا کردن اعضای پرداخت نشده
    unpaid_members = []
    for member_id, member_data in data[group_id]["members"].items():
        if not member_data["paid"]:
            unpaid_members.append(member_data["name"])
    
    if not unpaid_members:
        update.message.reply_text("✅ همه اعضا پرداخت خود را انجام داده‌اند.")
        return
    
    members_text = "📋 **اعضای در انتظار پرداخت:**\n\n"
    for i, name in enumerate(unpaid_members, 1):
        members_text += f"{i}. {name}\n"
    
    members_text += f"\n🔢 **تعداد:** {len(unpaid_members)} نفر"
    
    update.message.reply_text(members_text)

def show_help(update, context):
    """راهنما"""
    help_text = """
🤖 **راهنمای ربات صندوق همیاری**

📝 **ثبت عضویت** - ثبت نام خود یا اعضای خانواده در صندوق
💳 **پرداخت** - ثبت پرداخت و آپلود رسید
📋 **لیست اعضا** - مشاهده وضعیت پرداخت همه اعضا
🔄 **ویرایش اعضا** - مدیریت اعضای ثبت شده
✅ **تایید پرداخت** - فقط برای مدیران گروه
🗑️ **ریست کل اطلاعات** - شروع دوره جدید (فقط مدیران)

💡 **نکته:** برای استفاده، روی دکمه‌های منو کلیک کنید.
    """
    update.message.reply_text(help_text)

def button_handler(update, context):
    """مدیریت دکمه‌ها"""
    query = update.callback_query
    query.answer()
    
    if query.data.startswith("shares_"):
        shares_count = int(query.data.split("_")[1])
        user_id = query.from_user.id
        
        if user_id in registration_data:
            registration_data[user_id]["shares_count"] = shares_count
            registration_data[user_id]["step"] = "waiting_for_names"
            registration_data[user_id]["current_name_index"] = 1
            query.edit_message_text(f"✅ تعداد {shares_count} سهم ثبت شد.\n\nلطفاً نام شخص اول را وارد کنید:")
    
    elif query.data == "custom_shares":
        query.edit_message_text("لطفاً تعداد سهام مورد نظر را وارد کنید:")

def process_payment_receipt(update, context):
    """پردازش پرداخت"""
    user_id = update.effective_user.id
    group_id = update.effective_chat.id
    
    if group_id in data:
        # پیدا کردن سهام کاربر
        user_members = []
        for member_id, member_data in data[group_id]["members"].items():
            if member_data.get("registered_by") == user_id and not member_data["paid"]:
                user_members.append(member_data["name"])
                data[group_id]["members"][member_id]["paid"] = True
                data[group_id]["members"][member_id]["paid_by"] = user_id
        
        if user_members:
            save_data()
            names_text = "\n".join([f"• {name}" for name in user_members])
            update.message.reply_text(f"✅ **پرداخت ثبت شد!**\n\n📋 سهام پرداخت شده:\n{names_text}")
            
            # اعلام در گروه
            if len(user_members) == 1:
                announcement = f"🎉 {user_members[0]} پرداخت خود را انجام داد!"
            else:
                announcement = f"🎉 {update.effective_user.first_name} پرداخت {len(user_members)} سهم را انجام داد!"
            
            update.message.reply_text(announcement)
        else:
            update.message.reply_text("❌ همه سهام شما قبلاً پرداخت شده است.")

def main():
    """تابع اصلی"""
    try:
        updater = Updater(TOKEN, use_context=True)
        dp = updater.dispatcher
        
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
        dp.add_handler(CallbackQueryHandler(button_handler))
        dp.add_handler(MessageHandler(Filters.document, process_payment_receipt))
        dp.add_handler(MessageHandler(Filters.photo, process_payment_receipt))
        
        logging.info("🤖 ربات در حال اجرا است...")
        updater.start_polling()
        updater.idle()
        
    except Exception as e:
        logging.error(f"❌ خطا در اجرای ربات: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()