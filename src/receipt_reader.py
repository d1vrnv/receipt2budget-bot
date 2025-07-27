import json
import logging

from doctr.io import DocumentFile
from doctr.models import ocr_predictor
from llama_cpp import Llama

logger = logging.getLogger(__name__)


def extract_text_from_receipt(image_path: str) -> str:
    """Extract text from the receipt image using DocTR"""
    logger.info(f"Starting OCR extraction from: {image_path}")
    try:
        doc = DocumentFile.from_images(image_path)
        model = ocr_predictor(pretrained=True)
        ocr_result = model(doc)

        full_text = ocr_result.render()
        logger.info(f"OCR extraction completed. Text length: {len(full_text)}")
        return full_text.strip()
    except Exception as exc:
        logger.error(f"OCR extraction failed: {exc=}")
        raise exc


def ask_llm(receipt_text: str, model_path: str) -> dict:
    """Ask the LLM to parse the receipt text"""
    logger.info(f"Initializing LLM with model: {model_path}")
    try:
        llm = Llama(
            model_path=model_path,
            n_ctx=2048,
            n_gpu_layers=0,
            verbose=False,
        )
        logger.info("LLM initialized successfully")

        prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are a receipt parser. Extract the store name and the TOTAL AMOUNT TO PAY from receipt text.

IMPORTANT: 
- The total is the amount the customer needs to pay for their purchases (often labeled as "Total", "Amount Due", "To Pay", etc.)
- Do NOT use "Cash Tendered", "Cash Given", "Amount Tendered" - these are what the customer paid, not what they owe
- Do NOT use "Change" or "Cash Due" - these are what the customer gets back
- Look for terms like: "Total", "Amount Due", "To Pay", "Sub Total", "Final Total"

Return ONLY valid JSON in this exact format:
{{"store": "STORE NAME", "total": "£XX.XX"}}

<|start_header_id|>user<|end_header_id|>
{receipt_text}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

        logger.info("Sending prompt to LLM...")
        response = llm(
            prompt, max_tokens=100, temperature=0.1, stop=["<|eot_id|>"]
        )
        completion = response["choices"][0]["text"].strip()
        logger.info(f"LLM response: {completion}")

        try:
            result = json.loads(completion)
            logger.info(f"Successfully parsed JSON: {result}")
            return result
        except Exception as json_error:
            logger.error(f"Failed to parse JSON: {completion}")
            logger.error(f"JSON error: {json_error}")
            return {"store": "Unknown", "total": "£0.00"}
        finally:
            if llm is not None:
                logger.info("Freeing LLM model memory...")
                del llm

    except Exception as e:
        logger.error(f"LLM processing failed: {e}")
        logger.error(f"Error type: {type(e)}")
        raise
