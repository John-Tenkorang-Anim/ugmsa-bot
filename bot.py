import os
import re
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from telegram.constants import ParseMode
from openai import OpenAI

# === CONFIGURATION ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# UGMSA/FGMSA document links
# Document ID extracted from: https://docs.google.com/document/d/1vyX3bAFBgX8QuaCCsNHdyltyLMZCzB6BtnELtmjlcd0/edit
UGMSA_DOC_IDS = [
    "1vyX3bAFBgX8QuaCCsNHdyltyLMZCzB6BtnELtmjlcd0",  # UGMSA/FGMSA Information Document
    # Add more document IDs here if you have additional documents
]

# Main bot link
MAIN_BOT_LINK = "https://t.me/UGMSA_bot"

if TELEGRAM_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN" or OPENAI_API_KEY == "YOUR_OPENAI_API_KEY":
    raise ValueError("Please set TELEGRAM_BOT_TOKEN and OPENAI_API_KEY environment variables")

# === INITIALIZE OPENAI ===
client = OpenAI(api_key=OPENAI_API_KEY)

# Store conversation history per user
user_conversations = {}

# Cache for document content
document_content_cache = None

# === DOCUMENT FETCHING ===
def fetch_google_doc_content(doc_id):
    """Fetch content from a public Google Doc"""
    try:
        # Export as plain text
        export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
        response = requests.get(export_url, timeout=10)
        
        if response.status_code == 200:
            return response.text
        else:
            print(f"⚠️ Failed to fetch document {doc_id}: Status {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️ Error fetching document {doc_id}: {e}")
        return None

def load_all_documents():
    """Load all UGMSA/FGMSA documents"""
    global document_content_cache
    
    if document_content_cache:
        return document_content_cache
    
    all_content = []
    
    for doc_id in UGMSA_DOC_IDS:
        if doc_id.startswith("YOUR_DOCUMENT_ID"):
            continue
        
        print(f"📄 Fetching document {doc_id}...")
        content = fetch_google_doc_content(doc_id)
        
        if content:
            all_content.append(content)
            print(f"✅ Loaded document ({len(content)} characters)")
    
    if all_content:
        document_content_cache = "\n\n--- DOCUMENT SEPARATOR ---\n\n".join(all_content)
        print(f"✅ Total documents loaded: {len(all_content)}")
        return document_content_cache
    else:
        print("⚠️ No documents loaded. Bot will work without document context.")
        return None

# === HELPER FUNCTIONS ===
def format_response(text):
    """
    Clean up markdown formatting from AI responses
    Remove asterisks and convert to proper Telegram formatting
    """
    if not text:
        return text
    
    # Replace markdown headers (###, ##, #) with bold
    text = re.sub(r'^###\s+(.+?)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    text = re.sub(r'^##\s+(.+?)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    text = re.sub(r'^#\s+(.+?)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    
    # Replace **bold** with <b>bold</b> (shows as bold)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    
    # Replace *italic* with <i>italic</i> (shows as italic)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    
    # Replace _underline_ with proper underline
    text = re.sub(r'_(.+?)_', r'<u>\1</u>', text)
    
    # Replace `code` with monospace (good for emphasis)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    
    # Add emoji bullets for better visual appeal
    text = re.sub(r'^\s*[-•]\s+', '  ✓ ', text, flags=re.MULTILINE)
    
    # Clean up any remaining stray asterisks
    text = text.replace('*', '')
    
    return text

def get_main_menu_keyboard():
    """Create main menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("🎓 UGMSA/FGMSA Info", callback_data="ugmsa_info")],
        [InlineKeyboardButton("💬 Ask Question", callback_data="ask_question")],
        [InlineKeyboardButton("🔄 Clear Chat History", callback_data="clear_history")],
        [InlineKeyboardButton("🏠 Return to Main Bot", url=MAIN_BOT_LINK)]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard():
    """Create back button keyboard with option to return to main bot"""
    keyboard = [
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_menu")],
        [InlineKeyboardButton("🏠 Return to Main Bot", url=MAIN_BOT_LINK)]
    ]
    return InlineKeyboardMarkup(keyboard)

async def send_formatted_message(update, context, text, keyboard=None):
    """Send a message with proper formatting"""
    formatted_text = format_response(text)
    
    if update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text(
            formatted_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    elif update.message:
        await update.message.reply_text(
            formatted_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

# === COMMAND HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command"""
    if update.message:
        welcome_text = (
            "👋 <b>Welcome to Student AI Assistant!</b>\n\n"
            "I'm here to help you with:\n"
            "  • UGMSA/FGMSA information\n"
            "  • Academic questions\n"
            "  • Schedule assistance\n"
            "  • General student advice\n\n"
            "Choose an option below to get started:"
        )
        await send_formatted_message(update, context, welcome_text, get_main_menu_keyboard())

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /menu command"""
    menu_text = "📋 <b>Main Menu</b>\n\nWhat would you like to do?"
    await send_formatted_message(update, context, menu_text, get_main_menu_keyboard())

# === CALLBACK HANDLERS ===
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    
    # Safety check for None
    if not query or not query.from_user:
        return
    
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == "back_to_menu":
        menu_text = "📋 <b>Main Menu</b>\n\nWhat would you like to do?"
        try:
            await query.edit_message_text(
                format_response(menu_text),
                parse_mode=ParseMode.HTML,
                reply_markup=get_main_menu_keyboard()
            )
        except Exception as e:
            # Ignore if message is not modified
            if "Message is not modified" not in str(e):
                print(f"Error editing message: {e}")
    
    elif query.data == "ugmsa_info":
        info_text = (
            "📚 <b>UGMSA/FGMSA Information</b>\n\n"
            "You can ask me anything about UGMSA or FGMSA!\n\n"
            "I have access to the official documentation and can provide information about:\n"
            "  • Programs and events\n"
            "  • Membership details\n"
            "  • Resources available\n"
            "  • Contact information\n"
            "  • And much more!\n\n"
            "Just type your question below!"
        )
        try:
            await query.edit_message_text(
                format_response(info_text),
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_keyboard(),
                disable_web_page_preview=True
            )
        except Exception as e:
            if "Message is not modified" not in str(e):
                print(f"Error editing message: {e}")
    
    elif query.data == "ask_question":
        question_text = (
            "💬 <b>Ask Me Anything!</b>\n\n"
            "I'm ready to help. Just type your question below.\n\n"
            "I can assist with academics, schedules, UGMSA/FGMSA info, or general advice."
        )
        try:
            await query.edit_message_text(
                format_response(question_text),
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_keyboard()
            )
        except Exception as e:
            if "Message is not modified" not in str(e):
                print(f"Error editing message: {e}")
    
    elif query.data == "clear_history":
        if user_id in user_conversations:
            user_conversations[user_id] = []
        success_text = (
            "✅ <b>Chat History Cleared</b>\n\n"
            "Your conversation history has been reset. Start fresh with a new question!"
        )
        try:
            await query.edit_message_text(
                format_response(success_text),
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_keyboard()
            )
        except Exception as e:
            if "Message is not modified" not in str(e):
                print(f"Error editing message: {e}")

# === CHAT HANDLER ===
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for text messages"""
    if not update.message or not update.message.text or not update.message.from_user:
        return
    
    user_id = update.message.from_user.id
    user_input = update.message.text
    
    # Initialize conversation history for new users
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    
    # Add user message to history
    user_conversations[user_id].append({"role": "user", "content": user_input})
    
    # Keep only last 10 messages to avoid token limits
    if len(user_conversations[user_id]) > 10:
        user_conversations[user_id] = user_conversations[user_id][-10:]

    try:
        # Load document content
        doc_content = load_all_documents()
        
        # System prompt with UGMSA/FGMSA context
        system_prompt = (
            "You are a friendly and knowledgeable AI assistant for university students. "
            "Provide clear, concise, and helpful responses. "
        )
        
        if doc_content:
            system_prompt += (
                f"When asked about UGMSA (Undergraduate Medical Students' Association) or "
                f"FGMSA (Future Generation Medical Students' Association), use the following official documents:\n\n"
                f"{doc_content}\n\n"
                f"Provide accurate information from these documents and supplement with any additional knowledge you have. "
                f"NEVER tell users to 'refer to the document' - instead, directly answer their questions using the information provided. "
            )
        else:
            system_prompt += (
                f"When asked about UGMSA or FGMSA, provide any relevant information you know. "
            )
        
        system_prompt += (
            "FORMATTING RULES: "
            "- Use **bold** for important terms and headings "
            "- Use *italic* for emphasis "
            "- Use bullet points with - for lists "
            "- Use `code` formatting for dates, numbers, or special terms "
            "- Keep responses well-structured with clear paragraphs "
            "- Use emojis sparingly for visual appeal"
        )
        
        messages = [{"role": "system", "content": system_prompt}] + user_conversations[user_id]
        
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            timeout=30
        )
        
        reply = completion.choices[0].message.content
        
        if not reply:
            reply = "I'm not sure how to respond to that. Could you rephrase your question?"
        
        # Add assistant response to history
        user_conversations[user_id].append({"role": "assistant", "content": reply})
        
        # Send formatted response with back button
        await send_formatted_message(update, context, reply, get_back_keyboard())

    except Exception as e:
        print(f"Error processing message: {e}")
        error_text = "⚠️ Sorry, I ran into an issue processing your request. Please try again later."
        await send_formatted_message(update, context, error_text, get_back_keyboard())

# === MAIN ===
def main():
    """Main function to run the bot"""
    try:
        # Load documents at startup
        print("📚 Loading UGMSA/FGMSA documents...")
        load_all_documents()
        
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

        # Add handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("menu", menu))
        app.add_handler(CallbackQueryHandler(button_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

        print("🤖 AI Chat Bot is running...")
        print("Press Ctrl+C to stop")
        
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"Failed to start bot: {e}")
        raise

if __name__ == "__main__":
    main()