import logging
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# توکن ربات از متغیر محیطی
TOKEN = os.environ.get('BOT_TOKEN')

if not TOKEN:
    logging.error("❌ BOT_TOKEN not found in environment variables!")
    exit(1)

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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

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
    """دستور شروع - همیشه منو نمایش داده می‌شود"""
    chat_type = update.effective_chat.type
    
    # همیشه منو نمایش داده می‌شود
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
            "📋 **امکانات ربات:**\n"
            "• 📝 ثبت عضویت - ثبت نام خود یا اعضای خانواده\n"
            "• 💳 پرداخت - ثبت پرداخت و آپلود رسید\n"
            "• 📋 لیست اعضا - مشاهده وضعیت پرداخت همه\n"
            "• 🔄 ویرایش اعضا - مدیریت اعضای ثبت شده\n"
            "• ✅ تایید پرداخت - فقط برای مدیران\n\n"
            "💡 **برای شروع روی یکی از دکمه‌های زیر کلیک کنید**"
        )
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def process_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش مراحل ثبت نام"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in registration_data:
        return
    
    reg_data = registration_data[user_id]
    step = reg_data.get("step")
    
    if step == "waiting_for_shares":
        try:
            shares_count = int(text)
            if shares_count <= 0:
                await update.message.reply_text("❌ تعداد سهام باید عددی مثبت باشد. لطفاً مجدداً وارد کنید:")
                return
            if shares_count > 10:
                await update.message.reply_text("❌ حداکثر می‌توانید 10 سهم ثبت کنید. لطفاً عدد کمتری وارد کنید:")
                return
            
            reg_data["shares_count"] = shares_count
            reg_data["step"] = "waiting_for_names"
            reg_data["current_name_index"] = 1
            
            await update.message.reply_text(
                f"✅ تعداد {shares_count} سهم ثبت شد.\n\n"
                f"لطفاً نام شخص **اول** را وارد کنید:"
            )
            
        except ValueError:
            await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید:")
    
    elif step == "waiting_for_names":
        current_index = reg_data["current_name_index"]
        total_shares = reg_data["shares_count"]
        
        if text.strip() == "":
            await update.message.reply_text("❌ نام نمی‌تواند خالی باشد. لطفاً مجدداً وارد کنید:")
            return
        
        reg_data["names"].append(text.strip())
        
        if current_index < total_shares:
            reg_data["current_name_index"] += 1
            await update.message.reply_text(f"لطفاً نام شخص **{current_index + 1}** را وارد کنید:")
        else:
            # تکمیل ثبت نام
            await complete_registration(update, reg_data)
            del registration_data[user_id]

async def complete_registration(update: Update, reg_data: dict):
    """تکمیل فرآیند ثبت نام"""
    user_id = update.effective_user.id
    group_id = reg_data["group_id"]
    names = reg_data["names"]
    shares_count = reg_data["shares_count"]
    
    # ثبت تمام افراد در دیتابیس
    for i, name in enumerate(names):
        member_id = f"{user_id}_{i}"
        
        if group_id not in data:
            data[group_id] = {"members": {}, "winners": [], "current_month": "1403-02"}
        
        data[group_id]["members"][member_id] = {
            "name": name,
            "shares": 1,
            "paid": False,
            "paid_by": None,
            "registered_by": user_id,
            "username": update.effective_user.username
        }
    
    # ذخیره داده‌ها
    save_data()
    
    # ایجاد پیام خلاصه ثبت نام
    names_list = "\n".join([f"{i+1}. {name}" for i, name in enumerate(names)])
    
    keyboard = [[InlineKeyboardButton("💳 پرداخت الآن", callback_data="pay_now")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ **ثبت نام با موفقیت تکمیل شد!**\n\n"
        f"📊 **خلاصه ثبت نام:**\n"
        f"• تعداد سهام: {shares_count}\n"
        f"• اسامی ثبت شده:\n{names_list}\n\n"
        f"💳 **مبلغ قابل پرداخت:** {shares_count} × [مبلغ ماهانه]",
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش پیام‌ها در گروه"""
    if not update.message or not update.message.text:
        return
    
    text = update.message.text
    user_id = update.effective_user.id
    
    logging.info(f"Received message: {text} from user: {user_id} in chat: {update.effective_chat.id}")
    
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
    
    elif context.user_data.get('waiting_for_confirm_name'):
        await process_payment_confirmation(update, context)

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ثبت نام"""
    user_id = update.effective_user.id
    group_id = update.effective_chat.id
    
    if group_id not in data:
        data[group_id] = {"members": {}, "winners": [], "current_month": "1403-02"}
    
    # بررسی ثبت نام قبلی
    existing_members = [uid for uid in data[group_id]["members"] if data[group_id]["members"][uid].get("registered_by") == user_id]
    if existing_members:
        keyboard = [[InlineKeyboardButton("🔄 ویرایش اعضا", callback_data="edit_members")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "❌ شما قبلاً ثبت نام کرده‌اید.",
            reply_markup=reply_markup
        )
        return
    
    # شروع ثبت نام
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
    
    await update.message.reply_text(
        "📝 **ثبت نام جدید**\n\nلطفاً تعداد سهام را انتخاب کنید:",
        reply_markup=reply_markup
    )

async def show_payment_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی پرداخت"""
    user_id = update.effective_user.id
    group_id = update.effective_chat.id
    
    if group_id not in data:
        await update.message.reply_text("❌ هیچ عضوی در این گروه ثبت نام نکرده است.")
        return
    
    # پیدا کردن تمام سهام متعلق به این کاربر
    user_members = []
    for member_id, member_data in data[group_id]["members"].items():
        if member_data.get("registered_by") == user_id:
            user_members.append((member_id, member_data))
    
    if not user_members:
        keyboard = [[InlineKeyboardButton("📝 ثبت عضویت", callback_data="register")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "❌ شما در این صندوق عضو نیستید.",
            reply_markup=reply_markup
        )
        return
    
    # بررسی وضعیت پرداخت
    all_paid = all(member["paid"] for _, member in user_members)
    
    if all_paid:
        await update.message.reply_text("✅ شما قبلاً تمام پرداخت‌های خود را انجام داده‌اید.")
        return
    
    # نمایش لیست سهام کاربر
    members_text = "📋 **لیست سهام شما:**\n\n"
    unpaid_count = 0
    
    for i, (member_id, member_data) in enumerate(user_members, 1):
        status = "✅ پرداخت شده" if member_data["paid"] else "❌ در انتظار پرداخت"
        members_text += f"{i}. {member_data['name']} - {status}\n"
        if not member_data["paid"]:
            unpaid_count += 1
    
    members_text += f"\n💳 **تعداد پرداخت نشده:** {unpaid_count}"
    
    keyboard = [
        [InlineKeyboardButton("📤 آپلود رسید پرداخت", callback_data="upload_receipt")],
        [InlineKeyboardButton("📋 مشاهده لیست کامل", callback_data="view_full_list")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(members_text, reply_markup=reply_markup)

async def show_members_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست اعضا با شماره ردیف"""
    group_id = update.effective_chat.id
    
    if group_id not in data or not data[group_id]["members"]:
        await update.message.reply_text("📝 هنوز هیچ عضوی ثبت نام نکرده است.")
        return
    
    members_list = "📋 **لیست اعضا و وضعیت پرداخت**\n\n"
    total_members = 0
    total_paid = 0
    
    # تبدیل دیکشنری به لیست برای شماره‌گذاری
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
    members_list += f"• در انتظار پرداخت: {total_members - total_paid}\n"
    members_list += f"• وضعیت: {'✅ کامل' if total_paid == total_members else '⏳ در حال تکمیل'}"
    
    await update.message.reply_text(members_list)

async def show_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی ویرایش اعضا"""
    user_id = update.effective_user.id
    group_id = update.effective_chat.id
    
    if group_id not in data:
        await update.message.reply_text("❌ هیچ عضوی در این گروه ثبت نام نکرده است.")
        return
    
    # پیدا کردن تمام سهام متعلق به این کاربر
    user_members = []
    for member_id, member_data in data[group_id]["members"].items():
        if member_data.get("registered_by") == user_id:
            user_members.append((member_id, member_data))
    
    if not user_members:
        keyboard = [[InlineKeyboardButton("📝 ثبت عضویت", callback_data="register")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "❌ شما در این صندوق عضو نیستید.",
            reply_markup=reply_markup
        )
        return
    
    # نمایش لیست برای ویرایش
    members_text = "📝 **اعضای ثبت شده توسط شما:**\n\n"
    
    for i, (member_id, member_data) in enumerate(user_members, 1):
        status = "✅ پرداخت شده" if member_data["paid"] else "❌ در انتظار پرداخت"
        members_text += f"{i}. {member_data['name']} - {status}\n"
    
    members_text += "\n🔧 **امکانات ویرایش به زودی اضافه خواهد شد**"
    
    await update.message.reply_text(members_text)

async def show_confirm_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی تایید پرداخت برای مدیران"""
    if not await is_admin(update, context):
        await update.message.reply_text("❌ فقط مدیران می‌توانند از این قابلیت استفاده کنند.")
        return
    
    group_id = update.effective_chat.id
    
    if group_id not in data:
        await update.message.reply_text("❌ هیچ عضوی در این گروه ثبت نام نکرده است.")
        return
    
    # پیدا کردن اعضای پرداخت نشده
    unpaid_members = []
    for member_id, member_data in data[group_id]["members"].items():
        if not member_data["paid"]:
            unpaid_members.append((member_id, member_data))
    
    if not unpaid_members:
        await update.message.reply_text("✅ همه اعضا پرداخت خود را انجام داده‌اند.")
        return
    
    members_text = "📋 **اعضای در انتظار پرداخت:**\n\n"
    
    for i, (member_id, member_data) in enumerate(unpaid_members, 1):
        members_text += f"{i}. {member_data['name']}\n"
    
    members_text += f"\n🔢 **تعداد:** {len(unpaid_members)} نفر\n"
    members_text += "🔧 **امکانات تایید به زودی اضافه خواهد شد**"
    
    await update.message.reply_text(members_text)

async def process_payment_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش تایید پرداخت توسط مدیر"""
    await update.message.reply_text("🔧 این قابلیت به زودی اضافه خواهد شد.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی دکمه‌های اینلاین"""
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split('_')
    action = data_parts[0]
    
    if action == "shares":
        shares_count = int(data_parts[1])
        user_id = query.from_user.id
        
        if user_id in registration_data:
            registration_data[user_id]["shares_count"] = shares_count
            registration_data[user_id]["step"] = "waiting_for_names"
            registration_data[user_id]["current_name_index"] = 1
            
            await query.edit_message_text(
                f"✅ تعداد {shares_count} سهم ثبت شد.\n\nلطفاً نام شخص اول را وارد کنید:"
            )
    
    elif action == "custom":
        await query.edit_message_text("لطفاً تعداد سهام مورد نظر خود را وارد کنید:")
    
    elif action == "pay":
        await query.edit_message_text("لطفاً از دکمه 💳 پرداخت در منوی اصلی استفاده کنید.")
    
    elif action == "upload":
        await query.edit_message_text("📤 لطفاً عکس یا فایل رسید پرداخت خود را ارسال کنید.")
    
    elif action == "register":
        await query.edit_message_text("لطفاً از دکمه 📝 ثبت عضویت در منوی اصلی استفاده کنید.")

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش راهنما"""
    help_text = """
🤖 **راهنمای ربات صندوق همیاری**

📝 **ثبت عضویت** 
- ثبت نام خود یا اعضای خانواده در صندوق
- امکان ثبت تا 10 سهم
- وارد کردن نام هر شخص به صورت جداگانه

💳 **پرداخت** 
- ثبت پرداخت و آپلود رسید
- مشاهده وضعیت پرداخت سهام خود
- آپلود عکس یا فایل رسید بانکی

📋 **لیست اعضا** 
- مشاهده لیست کامل همه اعضا
- وضعیت پرداخت هر شخص
- آمار کلی صندوق

🔄 **ویرایش اعضا** 
- مدیریت اعضای ثبت شده توسط شما
- مشاهده وضعیت پرداخت

✅ **تایید پرداخت** 
- فقط برای مدیران گروه
- مشاهده لیست پرداخت‌نکرده‌ها

💡 **نکته:** برای استفاده، روی دکمه‌های منو کلیک کنید.
    """
    
    await update.message.reply_text(help_text)

async def process_payment_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE, receipt_type: str):
    """پردازش رسید پرداخت"""
    user_id = update.effective_user.id
    group_id = update.effective_chat.id
    
    if group_id not in data:
        return
    
    # پیدا کردن سهام پرداخت نشده کاربر
    unpaid_members = []
    for member_id, member_data in data[group_id]["members"].items():
        if member_data.get("registered_by") == user_id and not member_data["paid"]:
            unpaid_members.append((member_id, member_data))
    
    if not unpaid_members:
        await update.message.reply_text("❌ همه سهام شما قبلاً پرداخت شده است.")
        return
    
    # ثبت پرداخت
    paid_names = []
    for member_id, member_data in unpaid_members:
        data[group_id]["members"][member_id]["paid"] = True
        data[group_id]["members"][member_id]["paid_by"] = user_id
        paid_names.append(member_data["name"])
    
    # ذخیره داده‌ها
    save_data()
    
    paid_names_text = "\n".join([f"• {name}" for name in paid_names])
    
    await update.message.reply_text(
        f"✅ **پرداخت با موفقیت ثبت شد!**\n\n"
        f"📋 **سهام پرداخت شده:**\n{paid_names_text}\n\n"
        f"📤 **نوع رسید:** {receipt_type}"
    )
    
    # اعلام در گروه
    if len(paid_names) == 1:
        announcement = f"🎉 {paid_names[0]} پرداخت خود را انجام داد!"
    else:
        announcement = f"🎉 {update.effective_user.first_name} پرداخت {len(paid_names)} سهم را انجام داد!"
    
    await update.message.reply_text(announcement)
    await show_members_list(update, context)

def main():
    """تابع اصلی"""
    application = Application.builder().token(TOKEN).build()
    
    # هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.Document.ALL, lambda u, c: process_payment_receipt(u, c, "فایل")))
    application.add_handler(MessageHandler(filters.PHOTO, lambda u, c: process_payment_receipt(u, c, "عکس")))
    
    # راه‌اندازی ربات
    print("🤖 ربات صندوق همیاری در حال اجرا روی Render...")
    print("✅ منوهای شیشه‌ای فعال شده‌اند")
    print("✅ لیست اعضا با شماره ردیف نمایش داده می‌شود")
    print("✅ دکمه‌ها همیشه قابل مشاهده هستند")
    print("✅ داده‌ها به طور خودکار ذخیره می‌شوند")
    application.run_polling()

if __name__ == "__main__":
    main()