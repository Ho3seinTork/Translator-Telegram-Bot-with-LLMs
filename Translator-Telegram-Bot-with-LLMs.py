import sys, io, os, time, logging, asyncio
import aiohttp, telebot
from dotenv import load_dotenv
from functools import wraps
from aiohttp import ClientTimeout

# Set the standard output encoding to UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
load_dotenv()  # Load environment variables from a .env file

# Retrieve the Telegram bot token and DeepSeek API key from environment variables
TELEGRAM_TOKEN = os.getenv('7603734689:AAFw4mhm6ry8pWG-HdFJF6RSXNneRAHwiUs')
DEEPSEEK_API_KEY = os.getenv('sk-5ab846902f054229bdb715cf2e00ae2b')
if not all([TELEGRAM_TOKEN, DEEPSEEK_API_KEY]):
    raise ValueError("Missing required environment variables")

# Set default timeout for HTTP requests and rate limit for bot responses
DEFAULT_TIMEOUT = ClientTimeout(total=30)
RATE_LIMIT = 1

# Configure logging to output to both console and a file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('bot.log')]
)
logger = logging.getLogger(__name__)

# Decorator to enforce rate limiting on bot functions
def rate_limit(func):
    last_call = 0
    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal last_call
        now = time.time()
        if now - last_call < RATE_LIMIT:
            time.sleep(RATE_LIMIT - (now - last_call))
        last_call = time.time()
        return func(*args, **kwargs)
    return wrapper

# Initialize the Telegram bot with the provided token
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Asynchronous function to call the DeepSeek language model API
async def call_language_model(prompt, session):
    try:
        async with session.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Act as a professional translation assistant specializing in English-Persian and Persian-English translations. Your task is to provide accurate and contextually appropriate translations while maintaining a formal tone. When translating, ensure the cultural nuances of both languages are preserved. If a word or phrase has multiple possible translations, choose the one that best fits the context. Always present your translations clearly and concisely. Explanation: Role and Specialization: Clearly defines the AI's role as a translation assistant with expertise in English and Persian. Accuracy and Context: Emphasizes the importance of accuracy and contextual relevance in translations. Cultural Nuances: Instructs the AI to consider cultural aspects, which is crucial in translation tasks. Multiple Translations: Provides guidance on handling words or phrases with multiple translations. Clarity and Conciseness: Ensures that the output is professional and easy to understand."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }
        ) as response:
            # Return the translated text if the request is successful, otherwise return an error message
            return (await response.json())["choices"][0]["message"]["content"].strip() if response.status == 200 else "Translation service error"
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return "An error occurred during translation"

# Handler for incoming messages to the bot
@bot.message_handler(func=lambda _: True)
def handle_message(message):
    try:
        # Process the translation asynchronously and send the response back to the user
        response = asyncio.run(process_translation(message.text))
        bot.reply_to(message, response[:4000] + "\n[...]" if len(response) > 4000 else response)
    except Exception as e:
        logger.error(f"Translation Error: {str(e)}")
        bot.reply_to(message, "Error in translation process")

# Asynchronous function to process the translation request
async def process_translation(text):
    async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
        response = await call_language_model(text, session)
        return response.encode('utf-8', 'ignore').decode('utf-8')

# Main entry point of the script
if __name__ == "__main__":
    try:
        logger.info("Starting Telegram Bot...")
        bot.infinity_polling(timeout=60)  # Start polling for new messages
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
