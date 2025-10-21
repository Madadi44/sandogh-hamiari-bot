import logging
import json
import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# تنظیمات لاگ پیشرفته
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)

# چک کردن توکن
TOKEN = os.environ.get('BOT_TOKEN')

if not TOKEN:
    logging.error("❌ BOT_TOKEN not found in environment variables!")
    logging.error("Available environment variables: %s", list(os.environ.keys()))
    sys.exit(1)

logging.info("✅ Bot token loaded successfully")
logging.info(f"✅ Bot is starting with token: {TOKEN[:10]}...")  # فقط ۱۰ کاراکتر اول نمایش داده شود

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
    try:
        chat_type = update.effective_chat.type
        
        if await is_admin(update, context):
            reply_markup = ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True, input_field_placeholder="گزینه مورد نظر را انتخاب کنید...")
        else:
            reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True, input_field_placeholder="گزینه مورد نظر را انتخاب کنید...")
        
        if chat_type == "private":
            welcome_text = "🤖 **ربات صندوق همیاری**\n\nبه ربات خوش آمدید!"
        else:
            welcome_text = "🤖 **ربات صندوق همیاری فعال شد!**\n\nلطفاً از دکمه‌های زیر استفاده کنید:"
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        logging.info(f"Start command executed by {update.effective_user.id}")
    except Exception as e:
        logging.error(f"Error in start command: {e}")

# بقیه توابع دقیقاً مانند کد قبلی...
# [کامل‌ترین نسخه کد از پیام قبلی اینجا قرار می‌گیرد]

async def show_members_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست اعضا با شماره ردیف"""
    try:
        group_id = update.effective_chat.id
        
        if group_id not in data or not data[group_id]["members"]:
            await update.message.reply_text("📝 هنوز هیچ عضوی ثبت نام نکرده است.")
            return
        
        members_list = "📋 **لیست اعضا و وضعیت پرداخت**\n\n"
        total_members = 0
        total_paid = 0
        
        members_items = list(data[group_id]["members"].items())
        
        for index, (member_id, member_data) in enumerate(members_items, 1):
            status = "✅" if member_data["paid"] else "❌"
            members_list += f"{index}. {status} {member_data['name']}\n"
            total_members += 1
            if member_data["paid"]:
                total_paid += 1
        
        members_list += f"\n📊 **آمار کلی:**\n"
        members_list += f"• تعداد کل اعضا: {total_members}\n"
        members_list += f"• پرداخت شده: {total_paid}\n"
        members_list += f"• در انتظار پرداخت: {total_members - total_paid}"
        
        await update.message.reply_text(members_list)
    except Exception as e:
        logging.error(f"Error showing members list: {e}")
        await update.message.reply_text("❌ خطا در نمایش لیست اعضا")

def main():
    """تابع اصلی"""
    try:
        logging.info("🚀 Starting bot application...")
        application = Application.builder().token(TOKEN).build()
        
        # هندلرها
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.Document.ALL, lambda u, c: process_payment_receipt(u, c, "فایل")))
        application.add_handler(MessageHandler(filters.PHOTO, lambda u, c: process_payment_receipt(u, c, "عکس")))
        
        logging.info("✅ Bot handlers registered successfully")
        logging.info("🤖 Bot is now running...")
        
        application.run_polling()
        
    except Exception as e:
        logging.error(f"❌ Failed to start bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
