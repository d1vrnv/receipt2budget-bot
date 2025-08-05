# Receipt Parser Telegram Bot

A Telegram bot that processes receipt photos using OCR and LLM technology to automatically extract store information and
transaction amounts, then creates transactions in Actual Budget.

##  Screenshots

<div style="display: flex; justify-content: center; gap: 20px;">
  <img src="assets/photo_2025-07-27%2018.34.04.jpeg" alt="Main UI" width="200"/>
  <img src="assets/photo_2025-07-27%2018.34.06.jpeg" alt="LLM Response" width="200"/>
</div>

## Dependencies

This project uses the following key libraries:

- **[actualpy](https://github.com/bvanelli/actualpy)** : Python library for integrating with Actual Budget
- **[DocTR](https://github.com/mindee/doctr)**: OCR processing for extracting text from receipt images
- **[Llama 3.2](https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF)**: LLM for parsing store names and amounts from the receipt text
- **[aiogram](https://github.com/aiogram/aiogram)**: Telegram Bot API framework

## Features

- **Receipt OCR Processing**: Extract text from receipt images using DocTR
- **AI Analysis**: Uses Llama 3.2 LLM to parse store names and total amounts
- **Actual Budget Integration**: Automatically creates transactions in your Actual Budget
- **User Access Control**: Restricts bot usage to whitelisted Telegram user IDs
- **Confirmation Flow**: Interactive confirmation before adding transactions
- **Multi-format Support**: Accepts photos and image documents in various formats

## How It Works

1. **Authentication Check**: Bot verifies if the user is authorized to use the bot
2. **Image Reception**: Bot receives a photo or image document from the user
3. **OCR Processing**: DocTR extracts text from the receipt image
4. **AI Analysis**: Llama 3.2 model parses the text to identify:
    - Store/merchant name
    - Total transaction amount
5. **User Confirmation**: Bot displays parsed information and asks for confirmation
6. **Transaction Creation**: If confirmed, creates transaction in Actual Budget with:
    - Current date
    - Configured account
    - Store name as notes
    - Negative amount (expense)

## Prerequisites

- Docker and Docker Compose
- Telegram Bot Token (from @BotFather)
- Actual Budget server

## Quick Start

1. **Clone the repository:**

```bash
git clone https://github.com/d1vrnv/receipt2budget-bot.git
cd receipt_actual_budget
```

2. **Create the .env configuration file:**

```bash
cp .env.example .env
```

Edit the `.env` file with your specific configuration (see Configuration section below).

3. **Start the bot:**

```bash
docker-compose up -d
```

*Note: The first build will take some time as it downloads the Llama 3.2 model (~2GB)*

4. **Check the logs:**

```bash
docker-compose logs -f
```

## Configuration

Create a `.env` file in the project root with the following variables:

| Variable      | Description                             | Example                                         |
|---------------|-----------------------------------------|-------------------------------------------------|
| `BOT_TOKEN`   | Your Telegram bot token from @BotFather | `1234567890:ABCdef...`                          |
| `ALLOWED_USER_IDS`   | Comma-separated list of authorized Telegram user IDs | `111111111,222222222`                          |
| `MODEL_PATH`  | Path to the Llama model file            | `/app/models/Llama-3.2-3b-instruct-q4_k_m.gguf` |
| `AB_URL`      | Your Actual Budget server URL           | `http://localhost:5006`                         |
| `AB_PASSWORD` | Password for your Actual Budget server  | `your_password`                                 |
| `AB_FILE`     | Name of your Actual Budget file         | `My Budget`                                     |
| `AB_ACCOUNT`  | Account name in Actual Budget           | `Cash`                                          |
| `AB_PAYEE`    | Default payee name                      | `Starting Balance`                              |


### Getting Your Telegram User ID
To find your Telegram user ID for the configuration: `ALLOWED_USER_IDS`
1. Start a conversation with your bot
2. Send the command `/myid`
3. The bot will respond with your user ID
4. Add this ID to the environment variable `ALLOWED_USER_IDS`

**Note**: Only users whose IDs are listed in will be able to use the bot. All other users will receive an "unauthorized" message. `ALLOWED_USER_IDS`

## Usage

1. **In Telegram:**
    - Start a conversation with your bot
    - Send a photo of your receipt

2. **Bot workflow:**
    - Extracts text using OCR
    - Analyzes text with AI to identify store and total
    - Shows parsed information
    - Asks for confirmation before adding to Actual Budget

3. **Confirm or cancel:**
    - Click "✅ Yes" to add the transaction
    - Click "❌ No, cancel" to cancel
