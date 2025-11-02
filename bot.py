import os
import re
import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from telegram.constants import ParseMode
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# === CONFIGURATION ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Document IDs from Google Drive
UGMSA_DOC_IDS = ["1vyX3bAFBgX8QuaCCsNHdyltyLMZCzB6BtnELtmjlcd0"]

# UGMSA Website URL
UGMSA_WEBSITE_URL = "https://ugmsa.org/"

# Main bot link
MAIN_BOT_LINK = "https://t.me/UGMSA_bot"

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Missing environment variables: TELEGRAM_TOKEN and/or OPENAI_API_KEY")

# === INITIALIZE ===
client = OpenAI(api_key=OPENAI_API_KEY)
user_conversations = {}
knowledge_base_cache = None

# === KNOWLEDGE BASE LOADING ===
def fetch_google_doc(doc_id):
    """Fetch content from Google Doc"""
    try:
        url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print(f"✅ Loaded Google Doc ({len(response.text)} chars)")
            return response.text
    except Exception as e:
        print(f"⚠️ Error fetching doc {doc_id}: {e}")
    return None

def fetch_website_content(url):
    """Fetch and parse website content"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; UGMSABot/1.0)'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text(separator='\n', strip=True)
            # Clean up extra whitespace
            text = '\n'.join(line.strip() for line in text.splitlines() if line.strip())
            
            print(f"✅ Loaded website content ({len(text)} chars)")
            return text
    except Exception as e:
        print(f"⚠️ Error fetching website: {e}")
    return None

def load_knowledge_base():
    """Load all knowledge sources (documents + website)"""
    global knowledge_base_cache
    
    if knowledge_base_cache:
        return knowledge_base_cache
    
    print("📚 Loading UGMSA knowledge base...")
    sources = []
    
    # Load Google Docs
    for doc_id in UGMSA_DOC_IDS:
        content = fetch_google_doc(doc_id)
        if content:
            sources.append(f"=== OFFICIAL DOCUMENT ===\n{content}")
    
    # Load Website
    website_content = fetch_website_content(UGMSA_WEBSITE_URL)
    if website_content:
        sources.append(f"=== UGMSA WEBSITE (ugmsa.org) ===\n{website_content}")
    
    if sources:
        knowledge_base_cache = "\n\n".join(sources)
        print(f"✅ Knowledge base ready ({len(knowledge_base_cache)} total chars)")
        return knowledge_base_cache
    
    print("⚠️ No knowledge sources loaded")
    return None

# === TEXT FORMATTING ===
def format_response(text):
    """Convert markdown to Telegram HTML with enhanced styling"""
    if not text:
        return text
    
    # Headers to bold with emoji enhancement
    text = re.sub(r'^###\s+(.+?)$', r'<b>📌 \1</b>', text, flags=re.MULTILINE)
    text = re.sub(r'^##\s+(.+?)$', r'<b>▶️ \1</b>', text, flags=re.MULTILINE)
    text = re.sub(r'^#\s+(.+?)$', r'<b>🔹 \1</b>', text, flags=re.MULTILINE)
    
    # Markdown formatting
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'_(.+?)_', r'<u>\1</u>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    
    # Enhanced bullet points
    text = re.sub(r'^\s*[-•]\s+', r'  ✓ ', text, flags=re.MULTILINE)
    
    # Clean up
    text = text.replace('*', '')
    
    return text

# === KEYBOARDS ===
def get_main_menu_keyboard():
    """Main menu inline keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎓 UGMSA/FGMSA Info", callback_data="ugmsa_info")],
        [InlineKeyboardButton("💬 Ask Question", callback_data="ask_question")],
        [InlineKeyboardButton("🔄 Clear History", callback_data="clear_history")],
        [InlineKeyboardButton("🏠 Return to Main Bot", url=MAIN_BOT_LINK)]
    ])

def get_back_keyboard():
    """Back navigation keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_menu")],
        [InlineKeyboardButton("🏠 Return to Main Bot", url=MAIN_BOT_LINK)]
    ])

# === MESSAGE HELPERS ===
async def send_formatted_message(update, context, text, keyboard=None):
    """Send formatted message via callback or regular message"""
    formatted = format_response(text)
    
    if update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text(
            formatted, parse_mode=ParseMode.HTML, reply_markup=keyboard
        )
    elif update.message:
        await update.message.reply_text(
            formatted, parse_mode=ParseMode.HTML, reply_markup=keyboard
        )

# === COMMAND HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome = (
        "👋 <b>Welcome to UGMSA AI Assistant!</b>\n\n"
        "🎓 Your personal guide to the University of Ghana Medical Students' Association\n\n"
        "<b>How I Can Help:</b>\n"
        "  ✓ UGMSA/FGMSA information & programs\n"
        "  ✓ Events, meetings & important dates\n"
        "  ✓ Membership & resources\n"
        "  ✓ Academic support & advice\n\n"
        "💡 <i>Choose an option below to get started</i>"
    )
    await send_formatted_message(update, context, welcome, get_main_menu_keyboard())

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /menu command"""
    await send_formatted_message(
        update, context, 
        "📋 <b>Main Menu</b>\n\n"
        "What would you like to explore today?", 
        get_main_menu_keyboard()
    )

# === BUTTON HANDLERS ===
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses"""
    query = update.callback_query
    if not query or not query.from_user:
        return
    
    await query.answer()
    user_id = query.from_user.id
    
    handlers = {
        "back_to_menu": lambda: (
            "📋 <b>Main Menu</b>\n\n"
            "What would you like to explore today?",
            get_main_menu_keyboard()
        ),
        "ugmsa_info": lambda: (
            "📚 <b>UGMSA/FGMSA Knowledge Base</b>\n\n"
            "Ask me anything about the University of Ghana Medical Students' Association!\n\n"
            "<b>📖 My Knowledge Sources:</b>\n"
            "  ✓ Official UGMSA documents\n"
            "  ✓ Live website data (ugmsa.org)\n"
            "  ✓ Programs, events & activities\n"
            "  ✓ Membership guidelines\n"
            "  ✓ Leadership & contact info\n\n"
            "💬 <i>Type your question below and I'll provide detailed answers</i>",
            get_back_keyboard()
        ),
        "ask_question": lambda: (
            "💬 <b>Ask Me Anything!</b>\n\n"
            "I'm here to help with:\n\n"
            "<b>🎓 UGMSA Topics:</b>\n"
            "  • Events & programs\n"
            "  • Membership information\n"
            "  • Leadership structure\n"
            "  • Resources & opportunities\n\n"
            "<b>📚 Academic Support:</b>\n"
            "  • Study tips & guidance\n"
            "  • Course information\n"
            "  • Student life advice\n\n"
            "🎯 <i>Just type your question below!</i>",
            get_back_keyboard()
        ),
        "clear_history": lambda: (
            user_conversations.pop(user_id, None),
            "✅ <b>Chat History Cleared!</b>\n\n"
            "🔄 Your conversation has been reset.\n\n"
            "Ready for a fresh start? Ask me anything!",
            get_back_keyboard()
        )[1:]
    }
    
    if query.data in handlers:
        text, keyboard = handlers[query.data]()
        try:
            await query.edit_message_text(
                format_response(text),
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        except:
            pass  # Ignore "message not modified" errors

# === CHAT HANDLER ===
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user messages and generate AI responses"""
    if not update.message or not update.message.text or not update.message.from_user:
        return
    
    user_id = update.message.from_user.id
    user_input = update.message.text
    
    # Initialize conversation history
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    
    # Add user message
    user_conversations[user_id].append({"role": "user", "content": user_input})
    
    # Keep only last 10 messages
    if len(user_conversations[user_id]) > 10:
        user_conversations[user_id] = user_conversations[user_id][-10:]
    
    try:
        # Load knowledge base
        knowledge = load_knowledge_base()
        
        # Build system prompt
        system_prompt = (
            "You are a friendly and knowledgeable AI assistant for UGMSA "
            "(University of Ghana Medical Students' Association) students. "
            "Provide clear, accurate, and helpful responses.\n\n"
        )
        
        if knowledge:
            system_prompt += (
                f"Use this official information to answer questions:\n\n{knowledge}\n\n"
                "IMPORTANT: Answer questions directly using the information provided. "
                "Never tell users to 'check the document' or 'visit the website' - "
                "give them the answer directly.\n\n"
            )
        
        system_prompt += (
            "FORMATTING GUIDELINES:\n"
            "- Structure responses with clear sections\n"
            "- Use **bold** for headings and key terms\n"
            "- Use *italic* for emphasis and notes\n"
            "- Use bullet points (- ) for lists and multiple items\n"
            "- Use `code format` for dates, times, locations, and numbers\n"
            "- Add relevant emojis (🎓📚💡✨) to make content engaging\n"
            "- Keep paragraphs short (2-3 sentences max)\n"
            "- Use line breaks to improve readability\n"
            "- End with actionable next steps when relevant\n"
            "- Be warm, friendly, and encouraging in tone"
        )
        
        # Generate response
        messages = [{"role": "system", "content": system_prompt}] + user_conversations[user_id]
        
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            timeout=30
        )
        
        reply = completion.choices[0].message.content
        
        if not reply:
            reply = "I'm not sure how to respond. Could you rephrase your question?"
        
        # Add to history
        user_conversations[user_id].append({"role": "assistant", "content": reply})
        
        # Send response
        await send_formatted_message(update, context, reply, get_back_keyboard())
        
    except Exception as e:
        print(f"❌ Error in chat handler: {e}")
        await send_formatted_message(
            update, context,
            "⚠️ <b>Oops! Something went wrong</b>\n\n"
            "I encountered a temporary issue processing your request.\n\n"
            "💡 <i>Please try again, or rephrase your question</i>",
            get_back_keyboard()
        )

# === MAIN ===
import asyncio

async def main():
    """Run the bot safely inside Render background worker"""
    print("📚 Loading UGMSA knowledge base...")
    load_knowledge_base()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    print("🤖 UGMSA AI Bot is running in background mode...")
    await app.run_polling(allowed_updates=Update.ALL_TYPES)



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Bot stopped gracefully.")
