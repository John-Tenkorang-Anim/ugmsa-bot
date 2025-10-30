import os
import re
import requests
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from telegram.constants import ParseMode
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# === CONFIGURATION ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

UGMSA_DOC_IDS = [
    "1vyX3bAFBgX8QuaCCsNHdyltyLMZCzB6BtnELtmjlcd0",
]

MAIN_BOT_LINK = "https://t.me/UGMSA_bot"

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Please set TELEGRAM_TOKEN and OPENAI_API_KEY in your environment variables")

# === INITIALIZE OPENAI ===
client = OpenAI(api_key=OPENAI_API_KEY)

# Conversation history and document cache
user_conversations = {}
document_content_cache = None

# === DOCUMENT FETCHING ===
def fetch_google_doc_content(doc_id):
    try:
        export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
        response = requests.get(export_url, timeout=10)
        return response.text if response.status_code == 200 else None
    except Exception as e:
        print(f"⚠️ Error fetching document {doc_id}: {e}")
        return None

def load_all_documents():
    global document_content_cache
    if document_content_cache:
        return document_content_cache

    all_content = []
    for doc_id in UGMSA_DOC_IDS:
        if doc_id.startswith("YOUR_DOCUMENT_ID"):
            continue
        print(f"Fetching document {doc_id}...")
        content = fetch_google_doc_content(doc_id)
        if content:
            all_content.append(content)
            print(f" Loaded document ({len(content)} characters)")
    if all_content:
        document_content_cache = "\n\n--- DOCUMENT SEPARATOR ---\n\n".join(all_content)
        return document_content_cache
    return None

# === FORMATTING ===
def format_response(text):
    if not text:
        return text
    text = re.sub(r'^###\s+(.+?)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    text = re.sub(r'^##\s+(.+?)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    text = re.sub(r'^#\s+(.+?)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'_(.+?)_', r'<u>\1</u>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'^\s*[-•]\s+', '  ✓ ', text, flags=re.MULTILINE)
    text = text.replace('*', '')
    return text

def get_main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎓 UGMSA/FGMSA Info", callback_data="ugmsa_info")],
        [InlineKeyboardButton("💬 Ask Question", callback_data="ask_question")],
        [InlineKeyboardButton("🔄 Clear Chat History", callback_data="clear_history")],
        [InlineKeyboardButton("🏠 Return to Main Bot", url=MAIN_BOT_LINK)]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard():
    keyboard = [
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_menu")],
        [InlineKeyboardButton("🏠 Return to Main Bot", url=MAIN_BOT_LINK)]
    ]
    return InlineKeyboardMarkup(keyboard)

async def send_formatted_message(update, context, text, keyboard=None):
    formatted_text = format_response(text)
    if update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text(
            formatted_text, parse_mode=ParseMode.HTML, reply_markup=keyboard
        )
    elif update.message:
        await update.message.reply_text(
            formatted_text, parse_mode=ParseMode.HTML, reply_markup=keyboard
        )

# === COMMAND HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 <b>Welcome to Student AI Assistant!</b>\n\n"
        "Choose an option below to get started:"
    )
    await send_formatted_message(update, context, welcome_text, get_main_menu_keyboard())

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    menu_text = "📋 <b>Main Menu</b>\n\nWhat would you like to do?"
    await send_formatted_message(update, context, menu_text, get_main_menu_keyboard())

# === CALLBACK HANDLERS ===
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.from_user:
        return
    await query.answer()
    user_id = query.from_user.id

    if query.data == "back_to_menu":
        try:
            await query.edit_message_text(
                format_response("📋 <b>Main Menu</b>"),
                parse_mode=ParseMode.HTML,
                reply_markup=get_main_menu_keyboard()
            )
        except:
            pass

    elif query.data == "ugmsa_info":
        info_text = "📚 <b>UGMSA/FGMSA Information</b>\nAsk me anything about UGMSA/FGMSA!"
        try:
            await query.edit_message_text(format_response(info_text), parse_mode=ParseMode.HTML, reply_markup=get_back_keyboard())
        except:
            pass

    elif query.data == "ask_question":
        question_text = "💬 <b>Ask Me Anything!</b>\nType your question below."
        try:
            await query.edit_message_text(format_response(question_text), parse_mode=ParseMode.HTML, reply_markup=get_back_keyboard())
        except:
            pass

    elif query.data == "clear_history":
        user_conversations[user_id] = []
        success_text = "✅ <b>Chat History Cleared</b>"
        try:
            await query.edit_message_text(format_response(success_text), parse_mode=ParseMode.HTML, reply_markup=get_back_keyboard())
        except:
            pass

# === CHAT HANDLER ===
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or not update.message.from_user:
        return
    user_id = update.message.from_user.id
    user_input = update.message.text

    if user_id not in user_conversations:
        user_conversations[user_id] = []
    user_conversations[user_id].append({"role": "user", "content": user_input})
    if len(user_conversations[user_id]) > 10:
        user_conversations[user_id] = user_conversations[user_id][-10:]

    try:
        doc_content = load_all_documents()
        system_prompt = "You are a helpful AI assistant for students."
        if doc_content:
            system_prompt += f"\nUse these documents:\n{doc_content}"

        messages = [{"role": "system", "content": system_prompt}] + user_conversations[user_id]
        completion = client.chat.completions.create(model="gpt-4o-mini", messages=messages, timeout=30)
        reply = completion.choices[0].message.content or "I couldn't understand. Try again."
        user_conversations[user_id].append({"role": "assistant", "content": reply})
        await send_formatted_message(update, context, reply, get_back_keyboard())
    except Exception as e:
        print(f"Error: {e}")
        await send_formatted_message(update, context, "⚠️ Sorry, an error occurred.", get_back_keyboard())

# === MAIN ===
def main():
    print("📚 Loading documents...")
    load_all_documents()
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    print("🤖 Bot is polling... (background worker)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)  # NO await here

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")

