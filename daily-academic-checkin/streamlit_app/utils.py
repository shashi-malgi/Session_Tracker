import json
import os
import io
import csv
import yaml
from datetime import datetime
from typing import Dict, Any, List, Optional

from loguru import logger
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

# Optional imports
try:
	import openai
except Exception:
	openai = None

try:
	import whisper
except Exception:
	whisper = None

try:
	from twilio.rest import Client as TwilioClient
except Exception:
	TwilioClient = None

CONFIG: Dict[str, Any] = {}
TRANSLATIONS: Dict[str, Dict[str, str]] = {}


def load_config(config_path: str) -> Dict[str, Any]:
	global CONFIG
	with open(config_path, "r", encoding="utf-8") as f:
		CONFIG = yaml.safe_load(f)
	return CONFIG


def load_translations(translations_path: str) -> Dict[str, Dict[str, str]]:
	global TRANSLATIONS
	with open(translations_path, "r", encoding="utf-8") as f:
		TRANSLATIONS = json.load(f)
	return TRANSLATIONS


def t(key: str, lang: str = "en") -> str:
	return TRANSLATIONS.get(lang, {}).get(key, key)


# Notification utilities (mockable)

def send_email(to_email: str, subject: str, body: str) -> bool:
	logger.info(f"Sending email to {to_email}: {subject}")
	# Stub: integrate with real email provider as needed
	return True


def send_sms(to_number: str, message: str) -> bool:
	if not TwilioClient:
		logger.warning("Twilio not available; skipping SMS")
		return False
	try:
		account_sid = os.getenv("TWILIO_ACCOUNT_SID")
		auth_token = os.getenv("TWILIO_AUTH_TOKEN")
		from_number = os.getenv("TWILIO_FROM_NUMBER")
		client = TwilioClient(account_sid, auth_token)
		client.messages.create(body=message, from_=from_number, to=to_number)
		return True
	except Exception as e:
		logger.error(f"Failed to send SMS: {e}")
		return False


# AI utilities (stubs with optional OpenAI)

def generate_explanation(prompt: str) -> str:
	if openai and os.getenv("OPENAI_API_KEY"):
		try:
			client = openai.OpenAI()
			resp = client.chat.completions.create(
				model="gpt-4o-mini",
				messages=[{"role": "user", "content": prompt}],
				max_tokens=300,
			)
			return resp.choices[0].message.content or ""
		except Exception as e:
			logger.error(f"OpenAI error: {e}")
	# Demo fallback
	return "This topic can be challenging. Focus on key concepts, practice with examples, and review mistakes."


def generate_mcqs(topic: str, num_questions: int = 5) -> List[Dict[str, Any]]:
	if openai and os.getenv("OPENAI_API_KEY"):
		try:
			client = openai.OpenAI()
			resp = client.chat.completions.create(
				model="gpt-4o-mini",
				messages=[
					{"role": "system", "content": "Generate JSON array of MCQs with fields: question, options (A-D), answer (A-D)."},
					{"role": "user", "content": f"Topic: {topic}. Questions: {num_questions}."},
				],
				response_format={"type": "json_object"},
				max_tokens=800,
			)
			content = resp.choices[0].message.content
			parsed = json.loads(content)
			return parsed.get("mcqs", [])
		except Exception as e:
			logger.error(f"OpenAI error: {e}")
	# Demo MCQs
	mcqs = []
	for i in range(num_questions):
		mcqs.append({
			"question": f"Sample question {i+1} on {topic}?",
			"options": {"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"},
			"answer": "A",
		})
	return mcqs


# Audio transcription (Whisper optional)

def transcribe_audio(file_path: str) -> str:
	if whisper is None:
		logger.warning("Whisper not available; returning empty transcript")
		return ""
	try:
		model = whisper.load_model("base")
		result = model.transcribe(file_path)
		return result.get("text", "").strip()
	except Exception as e:
		logger.error(f"Whisper transcription failed: {e}")
		return ""


# Export utilities

def export_to_csv(filename: str, rows: List[Dict[str, Any]], headers: Optional[List[str]] = None) -> bytes:
	output = io.StringIO()
	if not headers and rows:
		headers = list(rows[0].keys())
	writer = csv.DictWriter(output, fieldnames=headers or [])
	writer.writeheader()
	for row in rows:
		writer.writerow(row)
	return output.getvalue().encode("utf-8")


def export_to_pdf(title: str, sections: List[Dict[str, Any]]) -> bytes:
	buffer = io.BytesIO()
	c = canvas.Canvas(buffer, pagesize=letter)
	width, height = letter
	c.setTitle(title)
	y = height - inch
	c.setFont("Helvetica-Bold", 16)
	c.drawString(inch, y, title)
	y -= 0.5 * inch
	c.setFont("Helvetica", 10)
	for section in sections:
		c.drawString(inch, y, str(section.get("heading", "")))
		y -= 0.25 * inch
		for line in section.get("lines", []):
			c.drawString(inch, y, str(line))
			y -= 0.2 * inch
		if y < inch:
			c.showPage()
			y = height - inch
	c.save()
	buffer.seek(0)
	return buffer.read()