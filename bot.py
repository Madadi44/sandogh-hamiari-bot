import logging
import json
import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

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

logging.info("✅ Bot token loaded successfully")

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
        logging.error(f"Error loading data: {e}")
        return {}

def save_data():
    """ذخیره داده‌ها در فایل"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Error saving data: {e}")

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
    ["✅ تایید پرداخت", "ℹ️ راهنما"]
]

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """بررسی اینکه کاربر مدیر است یا نه"""
    try:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        if update.callback_query:
            user_id = update.callback_query.from_user.id
            chat_id = update.callback_query.message.chat.id
        
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except Exception as e:
        logging.error(f"Error checking admin: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع"""
    chat_type = update.effective_chat.type
    
    if await is_admin(update, context):
        reply_markup = ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True, input_field_placeholder="گزینه مورد نظر را انتخاب کنید...")
    else:
        reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True, input_field_placeholder="گزینه مورد نظر را انتخاب کنید...")
    
    if chat_type == "private":
        welcome_text = (
            "🤖 **ربات صندوق همیاری**\n\n"
            "به ربات مدیریت صندوق همیاری خوش آمدید!\n"
            "لطفاً از دکمه‌های زیر برای استفاده از امکانات ربات استفاده کنید:"
        )
    else:
        welcome_text = (
            "🤖 **ربات صندوق همیاری فعال شد!**\n\n"
            "✅ ربات با موفقیت به گروه اضافه شد\n\n"
            "📋 **برای شروع روی دکمه‌های زیر کلیک کنید:**"
        )
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش پیام‌ها"""
    if not update.message or not update.message.text:
        return
    
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "📝 ثبت عضویت":
        await start_registration(update, context)
    elif text == "💳 پرداخت":
        await show_payment_menu(update, context)
    elif text == "📋 لیست اعضا":
        await show_members_list(update, context)
    elif text == "🔄 ویرایش اعضا":
        await show_edit_menu(update, context)
    elif text == "✅ تایید پرداخت":
        await show_confirm_menu(update, context)
    elif text == "ℹ️ راهنما":
        await show_help(update, context)
    elif user_id in registration_data:
        await process_registration(update, context)

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ثبت نام"""
    user_id = update.effective_user.id
    group_id = update.effective_chat.id
    
    if group_id not in data:
        data[group_id] = {"members": {}, "winners": [], "current_month": "1403-02"}
    
    existing_members = [uid for uid in data[group_id]["members"] if data[group_id]["members"][uid].get("registered_by") == user_id]
    if existing_members:
        await update.message.reply_text("❌ شما قبلاً ثبت نام کرده‌اید.")
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
    
    await update.message.reply_text("📝 **ثبت نام جدید**\n\nلطفاً تعداد سهام را انتخاب کنید:", reply_markup=reply_markup)

async def process_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                await update.message.reply_text(f"✅ تعداد {shares_count} سهم ثبت شد.\n\nلطفاً نام شخص اول را وارد کنید:")
            else:
                await update.message.reply_text("❌ تعداد سهام باید بین ۱ تا ۱۰ باشد.")
        except ValueError:
            await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید:")
    
    elif step == "waiting_for_names":
        current_index = reg_data["current_name_index"]
        total_shares = reg_data["shares_count"]
        
        if text.strip():
            reg_data["names"].append(text.strip())
            
            if current_index < total_shares:
                reg_data["current_name_index"] += 1
                await update.message.reply_text(f"لطفاً نام شخص {current_index + 1} را وارد کنید:")
            else:
                await complete_registration(update, reg_data)
                del registration_data[user_id]
        else:
            await update.message.reply_text("❌ نام نمی‌تواند خالی باشد.")

async def complete_registration(update: Update, reg_data: dict):
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
    await update.message.reply_text(f"✅ **ثبت نام تکمیل شد!**\n\n📋 اسامی ثبت شده:\n{names_list}")

async def show_payment_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی پرداخت"""
    await update.message.reply_text("💳 **منوی پرداخت**\n\nلطفاً رسید پرداخت خود را آپلود کنید.")

async def show_members_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست اعضا"""
    group_id = update.effective_chat.id
    
    if group_id not in data or not data[group_id]["members"]:
        await update.message.reply_text("📝 هنوز هیچ عضوی ثبت نام نکرده است.")
        return
    
    members_list = "📋 **لیست اعضا**\n\n"
    for i, (member_id, member_data) in enumerate(data[group_id]["members"].items(), 1):
        status = "✅" if member_data["paid"] else "❌"
        members_list += f"{i}. {status} {member_data['name']}\n"
    
    await update.message.reply_text(members_list)

async def show_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی ویرایش"""
    await update.message.reply_text("🔧 **منوی ویرایش**\n\nاین قابلیت به زودی اضافه می‌شود.")

async def show_confirm_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تایید پرداخت"""
    if not await is_admin(update, context):
        await update.message.reply_text("❌ فقط مدیران می‌توانند از این قابلیت استفاده کنند.")
        return
    await update.message.reply_text("✅ **منوی تایید پرداخت**\n\nمخصوص مدیران")

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """راهنما"""
    help_text = """
🤖 **راهنمای ربات صندوق همیاری**

📝 **ثبت عضویت** - ثبت نام در صندوق
💳 **پرداخت** - ثبت پرداخت
📋 **لیست اعضا** - مشاهده وضعیت
🔄 **ویرایش اعضا** - مدیریت اعضا
✅ **تایید پرداخت** - فقط مدیران
"""
    await update.message.reply_text(help_text)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت دکمه‌ها"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("shares_"):
        shares_count = int(query.data.split("_")[1])
        user_id = query.from_user.id
        
        if user_id in registration_data:
            registration_data[user_id]["shares_count"] = shares_count
            registration_data[user_id]["step"] = "waiting_for_names"
            registration_data[user_id]["current_name_index"] = 1
            await query.edit_message_text(f"✅ تعداد {shares_count} سهم ثبت شد.\n\nلطفاً نام شخص اول را وارد کنید:")
    
    elif query.data == "custom_shares":
        await query.edit_message_text("لطفاً تعداد سهام مورد نظر را وارد کنید:")

async def process_payment_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE, receipt_type: str):
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
            await update.message.reply_text(f"✅ **پرداخت ثبت شد!**\n\n📋 سهام پرداخت شده:\n{names_text}")
        else:
            await update.message.reply_text("❌ همه سهام شما قبلاً پرداخت شده است.")

def main():
    """تابع اصلی"""
    try:
        application = Application.builder().token(TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.Document.ALL, lambda u, c: process_payment_receipt(u, c, "فایل")))
        application.add_handler(MessageHandler(filters.PHOTO, lambda u, c: process_payment_receipt(u, c, "عکس")))
        
        logging.info("🤖 ربات در حال اجرا است...")
        application.run_polling()
        
    except Exception as e:
        logging.error(f"❌ خطا در اجرای ربات: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
