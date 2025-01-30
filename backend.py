
from config import gemini_model  # Import Gemini AI model
from config import API_KEY  # Import API key from config.py
import google.generativeai as genai
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import datetime  # To store timestamps
import requests  # For web search

# Initialize Gemini AI
genai.configure(api_key=API_KEY)

uri = "mongodb+srv://mybtp:mybtp@clusterss.wyh4e.mongodb.net/?retryWrites=true&w=majority&appName=Clusterss"

from typing import Final
from pymongo import MongoClient
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# MongoDB setup
client = MongoClient(uri)
db = client['Telegram']
users_collection = db['Task']

# Bot details
TOKEN = '7547487684:AAGlPhuP3Lm7Otv4pQM4T4NY4PBQ0AyZKbc'
BOT_USERNAME: Final = '@Triehf_bot'


# Commands
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    # Check if the user is already in the database
    if not users_collection.find_one({"chat_id": user.id}):
        user_data = {
            "first_name": user.first_name,
            "username": user.username,
            "chat_id": user.id,
        }
        users_collection.insert_one(user_data)
        await update.message.reply_text("Welcome! Your details have been saved.")
    else:
        await update.message.reply_text("Welcome back!")

    await update.message.reply_text("Hello! Thanks for chatting with me. I am a Kela!")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("I am a Banana! Here to assist you!")


async def custom_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("This is a custom command.")


# Feature 2: Request and Save Phone Number
async def request_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact_button = KeyboardButton("Share your phone number", request_contact=True)
    custom_keyboard = [[contact_button]]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard, one_time_keyboard=True)

    await update.message.reply_text(
        "Please share your phone number to complete registration:",
        reply_markup=reply_markup,
    )


async def save_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone_number = update.message.contact.phone_number
        chat_id = update.message.from_user.id
        # Update user data in MongoDB
        users_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"phone_number": phone_number}},
        )
        await update.message.reply_text("Thank you! Your phone number has been saved.")
    else:
        await update.message.reply_text("Please use the contact button to share your phone number.")


# Message Responses

# 🚀 KEEP ONLY THIS `handle_message` FUNCTION (Uses Gemini AI)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.message.chat.id

    # Ensure Gemini AI is configured correctly
    genai.configure(api_key=API_KEY)

    # Use Gemini AI to generate a response
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(user_text)

    # Check if response exists and get the text
    if response and hasattr(response, 'text'):
        ai_response = response.text
    else:
        ai_response = "Sorry, I couldn't process that."

    # Save chat history to MongoDB
    users_collection.update_one(
        {"chat_id": chat_id},
        {"$push": {"chat_history": {
            "user": user_text,
            "bot": ai_response,
            "timestamp": datetime.datetime.utcnow()
        }}},
        upsert=True
    )

    await update.message.reply_text(ai_response)

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} caused error {context.error}")

#for images
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    photo = update.message.photo[-1]  # Get the highest resolution photo
    file = await photo.get_file()
    file_path = file.file_path  # URL of the image

    # Use Gemini AI for image analysis
    model = genai.GenerativeModel("gemini-pro-vision")
    response = model.generate_content([{"type": "image_url", "url": file_path}])
    ai_description = response.text if response else "Couldn't analyze the image."

    # Save image metadata in MongoDB
    users_collection.update_one(
        {"chat_id": chat_id},
        {"$push": {"image_analysis": {"file_url": file_path, "description": ai_description, "timestamp": datetime.datetime.utcnow()}}},
        upsert=True
    )

    await update.message.reply_text(f"Image Analysis:\n{ai_description}")
    
#FOR WEB SEARCH
# # Add this at the top if not already imported
async def web_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a search query. Example: /websearch AI trends")
        return

    query = ' '.join(context.args)
    import config
    url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={config.GOOGLE_SEARCH_API_KEY}&cx={config.SEARCH_ENGINE_ID}"

    try:
        response = requests.get(url)
        data = response.json()

        if "items" in data:
            search_results = [
                f"{i+1}. [{item['title']}]({item['link']})\n_{item.get('snippet', 'No description available.')}_"
                for i, item in enumerate(data["items"][:5])
            ]

            # Prepare text for AI summary
            search_text = "\n".join([f"{item['title']}: {item.get('snippet', '')}" for item in data["items"][:5]])

            # Generate summary using Gemini AI
            response = gemini_model.generate_content(f"Summarize the following search results:\n{search_text}")
            summary = response.text if response.text else "No summary available."

            # Send the response
            message = f"🔎 **Search Summary:**\n_{summary}_\n\n**Top Search Results for:** `{query}`\n\n" + "\n".join(search_results)
            await update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=True)

        else:
            await update.message.reply_text("No results found.")
    
    except Exception as e:
        await update.message.reply_text("⚠️ Error fetching search results.")
        print(f"Web Search Error: {e}")

if __name__ == '__main__':
    print("Starting bot...")

    app = Application.builder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("custom", custom_command))
    app.add_handler(CommandHandler("get_phone", request_phone_number))
    app.add_handler(CommandHandler("websearch", web_search))  # Web search command
    app.add_handler(MessageHandler(filters.CONTACT, save_phone_number))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))  # Gemini chat (Fixed)
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))  # Image analysis
    app.add_error_handler(error)


    # Polling (Indented properly)
    print("Polling...")
    app.run_polling(poll_interval=3)


