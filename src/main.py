import asyncio
import datetime
import logging
import os
import sys
from typing import Literal

from actual import Actual, create_transaction
from aiogram import Bot, Dispatcher, F
from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from pydantic import SecretStr
from pydantic_settings import BaseSettings

from src.receipt_reader import extract_text_from_receipt, ask_llm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Supported image extensions for documents
SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".tiff",
}


class Settings(BaseSettings):
    model_path: str = "../models/Llama-3.2-3b-instruct-q4_k_m.gguf"
    bot_token: SecretStr
    ab_url: str
    ab_password: SecretStr
    ab_file: str
    ab_account: str = "Cash"
    ab_payee: str = "Starting Balance"


class ConfirmationCallback(CallbackData, prefix="confirm"):
    action: Literal["add", "cancel"]
    store: str
    total: float


app_settings = Settings()

dp = Dispatcher()
bot = Bot(token=app_settings.bot_token.get_secret_value())


async def process_receipt_file(
    message: Message, file_id: str, filename: str = "receipt.jpg"
):
    """Common function to process receipt files"""
    processing_msg = await message.answer("🔍 Processing your receipt...")

    try:
        file_info = await bot.get_file(file_id)
        file_path = file_info.file_path

        os.makedirs("../downloaded_images", exist_ok=True)

        file_extension = (
            os.path.splitext(filename)[1].lower() if filename else ".jpg"
        )
        if file_extension not in SUPPORTED_IMAGE_EXTENSIONS:
            await message.answer("❌ Please send image files only.\n")
        destination = f"../downloaded_images/{file_id}{file_extension}"

        await bot.download_file(file_path, destination)

        await processing_msg.edit_text(
            "📷 Receipt image downloaded. Running OCR..."
        )

        receipt_text = extract_text_from_receipt(destination)

        await processing_msg.edit_text(
            "🤖 Text extracted. Analyzing with LLM..."
        )

        # Process the receipt text with LLM
        result = ask_llm(receipt_text, app_settings.model_path)

        store = result.get("store", "Unknown")
        pay_total = result.get("total", None)

        if not pay_total:
            logger.warning(f"Could not parse total amount. {receipt_text=}")
            await processing_msg.edit_text("Could not parse total amount")
            return None

        pay_total = float(pay_total)
        response_text = (
            f"✅ Receipt Analysis Complete\n\n"
            f"🏪 Store: {store}\n"
            f"💰 Total: {pay_total}\n\n"
            f"Should I add this transaction to Actual?"
        )

        # Create the inline keyboard for confirmation
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Yes",
                        callback_data=ConfirmationCallback(
                            action="add", store=store, total=pay_total
                        ).pack(),
                    ),
                    InlineKeyboardButton(
                        text="❌ No, cancel",
                        callback_data=ConfirmationCallback(
                            action="cancel", store=store, total=pay_total
                        ).pack(),
                    ),
                ]
            ]
        )

        # Send the result with confirmation buttons
        await processing_msg.edit_text(response_text, reply_markup=keyboard)

        try:
            os.remove(destination)
        except Exception as cleanup_error:
            logger.warning(
                f"Failed to clean up file {destination}: {cleanup_error}"
            )

    except Exception as e:
        logger.error(f"Error processing receipt: {e}")
        await processing_msg.edit_text(
            f"❌ Error processing your receipt: {str(e)}"
        )


@dp.callback_query(ConfirmationCallback.filter())
async def handle_confirmation(
    callback: CallbackQuery, callback_data: ConfirmationCallback
) -> None:
    """Handle confirmation button clicks"""
    await callback.answer()

    if callback_data.action == "add":
        try:
            await callback.message.edit_text(
                "💾 Adding transaction to Actual..."
            )

            try:
                total_amount = float(callback_data.total)
            except ValueError:
                logger.error(
                    f"Could not parse total amount: {callback_data.total}"
                )
                await callback.message.edit_text(
                    "Could not parse total amount"
                )
                return None

            with Actual(
                base_url=app_settings.ab_url,
                password=app_settings.ab_password.get_secret_value(),
                file=app_settings.ab_file,
            ) as actual:
                actual_transaction = create_transaction(
                    actual.session,
                    datetime.date.today(),
                    app_settings.ab_account,
                    app_settings.ab_payee,
                    notes=callback_data.store,
                    amount=-total_amount,
                )
                actual.commit()
                logger.info(f"Added transaction to Actual: {actual_transaction.model_dump_json()}")

            success_text = (
                f"✅ Transaction Added Successfully!\n\n"
                f"🏪 Store: {callback_data.store}\n"
                f"💰 Total: {callback_data.total}\n"
                f"📅 Date: {datetime.date.today().strftime('%Y-%m-%d')}\n"
                f"👤 Account: {app_settings.ab_account}\n"
                f"💳 Payee: {app_settings.ab_payee}"
            )
            await callback.message.edit_text(success_text)

        except Exception as exc:
            logger.error(f"Error adding transaction to Actual: {exc}")
            error_text = (
                f"❌ Failed to add transaction to Actual\n\n"
                f"Error: {str(exc)}\n\n"
                f"🏪 Store: {callback_data.store}\n"
                f"💰 Total: {callback_data.total}"
            )
            await callback.message.edit_text(error_text)

    elif callback_data.action == "cancel":
        cancelled_text = (
            f"❌ Transaction Cancelled\n\n"
            f"🏪 Store: {callback_data.store}\n"
            f"💰 Total: {callback_data.total}\n\n"
            f"The transaction was not added to Actual."
        )
        await callback.message.edit_text(cancelled_text)
    return None


@dp.message(F.photo)
async def handle_photo(message: Message):
    """Handle photo messages"""
    photo = message.photo[-1]
    file_id = photo.file_id
    await process_receipt_file(message, file_id, "receipt.jpg")


@dp.message(F.document)
async def handle_document(message: Message):
    """Handle document attachments - only image files"""
    document = message.document
    file_name = document.file_name or "document"
    file_extension = os.path.splitext(file_name)[1].lower()

    if file_extension in SUPPORTED_IMAGE_EXTENSIONS:
        await process_receipt_file(message, document.file_id, file_name)
    else:
        await message.answer("❌ Please send image files only.\n")


@dp.message()
async def echo(message: Message):
    """Handle all other messages"""
    help_text = (
        "📸 Send me a photo of your receipt and I'll extract the store name and total amount!\n\n"
        "You can send:\n"
        "• Photos (regular telegram photos)\n"
        "• Image files as documents (for better quality)\n\n"
        "After processing, I'll ask for confirmation before adding the transaction to Actual."
    )
    await message.answer(help_text)


async def main():
    logger.info("Bot starting...")
    if not app_settings.bot_token.get_secret_value():
        logger.error("BOT_TOKEN environment variable is not set")
        sys.exit(1)

    if not os.path.exists(app_settings.model_path):
        logger.error(f"Model file not found at: {app_settings.model_path}")
        sys.exit(1)

    logger.info("Bot started successfully!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
