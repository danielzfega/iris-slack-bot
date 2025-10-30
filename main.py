# main.py — FastAPI + Slack Bolt (adapter) + Hugging Face summarizer
import os
import json
from typing import Optional, List
from fastapi import FastAPI, Request
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from sqlmodel import SQLModel, Field, create_engine, Session, select
from transformers import pipeline
from dotenv import load_dotenv
import asyncio

load_dotenv()
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
HUGGINGFACE_MODEL = os.environ.get("HUGGINGFACE_MODEL", "sshleifer/distilbart-cnn-12-6")
DATABASE_URL = os.environ.get("DATABASE_URL")
HOST_URL = os.environ.get("HOST_URL", "")

# ---------- DB models ----------
class UserTrack(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str  # Slack user id
    track: str
    contact: str = "slack"  # slack or email
    email: Optional[str] = None

engine = create_engine(DATABASE_URL, echo=False)
SQLModel.metadata.create_all(engine)

# ---------- load summarizer pipeline (single global) ----------
print("Loading summarization model:", HUGGINGFACE_MODEL)
summarizer = pipeline("summarization", model=HUGGINGFACE_MODEL, device=-1)  # CPU default

# ---------- Slack Async App ----------
app = AsyncApp(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
fastapi_app = FastAPI()
handler = AsyncSlackRequestHandler(app)

# ---------- helper functions ----------
TRACK_KEYWORDS = {
    "backend": ["backend", "backend wizards", "server", "api", "stage 0 backend", "profile endpoint"],
    "frontend": ["frontend", "ui", "react", "vue", "stage 1 frontend"],
    "design": ["design", "ui/ux", "ui-ux", "designers", "graphics", "ux"],
    "devops": ["devops", "nginx", "blue/green", "infrastructure"],
    "marketing": ["sales", "marketing"],
    "video": ["video", "editing", "video editing"],
    "pm": ["pm", "product", "project manager"],
    "no-code": ["no-code", "no code", "automation"]
}

def detect_track_by_keywords(text: str) -> Optional[str]:
    t = text.lower()
    for track, kwlist in TRACK_KEYWORDS.items():
        for kw in kwlist:
            if kw in t:
                return track
    return None

def summarize_text(text: str, max_length=140) -> str:
    # Hugging Face summarizer expects shorter inputs; truncate if needed
    # Use pipeline; handle exceptions
    try:
        # The distilbart model expects up to ~1024 tokens; so slicing characters is a safe simple approach
        if len(text) > 15000:
            text = text[:15000]
        summary_list = summarizer(text, max_length=max_length, min_length=30, do_sample=False)
        return summary_list[0]["summary_text"]
    except Exception as e:
        print("Summarization failed:", e)
        # fallback: naive extract (first 200 chars)
        return text.strip()[:400] + ("..." if len(text) > 400 else "")

async def notify_track_users(track: str, title: str, summary: str, original_text: str, slack_link: Optional[str]):
    with Session(engine) as session:
        users = session.exec(select(UserTrack).where(UserTrack.track == track)).all()
    for u in users:
        dm_text = f"*{title}*  \n{summary}\n\n"
        if slack_link:
            dm_text += f"<{slack_link}|View original announcement>\n"
        dm_text += "\n_This was sent by HNG Task Assistant_"
        try:
            res = await app.client.chat_postMessage(channel=u.user_id, text=dm_text)
            print("Sent DM to", u.user_id, res["ts"])
        except Exception as e:
            print("Failed to DM user", u.user_id, e)
            # TODO: fallback to email if contact == 'email'

# ---------- Slash command: /register-track ----------
@app.command("/register-track")
async def handle_register(ack, body, client, logger):
    await ack()
    trigger_id = body.get("trigger_id")
    # open a modal with a select
    await client.views_open(
        trigger_id=trigger_id,
        view={
            "type": "modal",
            "callback_id": "register_track_modal",
            "title": {"type": "plain_text", "text": "Register Track"},
            "submit": {"type": "plain_text", "text": "Save"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "track_select",
                    "element": {
                        "type": "static_select",
                        "action_id": "track_selected",
                        "placeholder": {"type": "plain_text", "text": "Choose your track"},
                        "options": [
                            {"text": {"type": "plain_text", "text": "Backend"}, "value": "backend"},
                            {"text": {"type": "plain_text", "text": "Frontend"}, "value": "frontend"},
                            {"text": {"type": "plain_text", "text": "Design"}, "value": "design"},
                            {"text": {"type": "plain_text", "text": "DevOps"}, "value": "devops"},
                            {"text": {"type": "plain_text", "text": "Marketing"}, "value": "marketing"},
                            {"text": {"type": "plain_text", "text": "Video"}, "value": "video"},
                            {"text": {"type": "plain_text", "text": "PM"}, "value": "pm"},
                            {"text": {"type": "plain_text", "text": "No-Code"}, "value": "no-code"},
                        ],
                    },
                    "label": {"type": "plain_text", "text": "Select track"}
                },
                {
                    "type": "input",
                    "block_id": "contact_input",
                    "element": {
                        "type": "static_select",
                        "action_id": "contact_selected",
                        "placeholder": {"type": "plain_text", "text": "How do you want to be contacted?"},
                        "options": [
                            {"text": {"type": "plain_text", "text": "Slack DM"}, "value": "slack"},
                            {"text": {"type": "plain_text", "text": "Email (provide below)"}, "value": "email"}
                        ]
                    },
                    "label": {"type": "plain_text", "text": "Contact method"}
                },
                {
                    "type": "input",
                    "block_id": "email_block",
                    "optional": True,
                    "element": {"type": "plain_text_input", "action_id": "email_input", "placeholder": {"type":"plain_text","text":"you@example.com"}},
                    "label": {"type": "plain_text", "text": "Email (optional)"}
                }
            ]
        }
    )

@app.view("register_track_modal")
async def handle_view_submission(ack, body, view, logger):
    await ack()
    user_id = body["user"]["id"]
    values = view["state"]["values"]
    track = values["track_select"]["track_selected"]["selected_option"]["value"]
    contact = values["contact_input"]["contact_selected"]["selected_option"]["value"]
    email = values.get("email_block", {}).get("email_input", {}).get("value")
    # save to DB
    with Session(engine) as session:
        stmt = select(UserTrack).where(UserTrack.user_id == user_id)
        existing = session.exec(stmt).first()
        if existing:
            existing.track = track
            existing.contact = contact
            existing.email = email
            session.add(existing)
        else:
            ut = UserTrack(user_id=user_id, track=track, contact=contact, email=email)
            session.add(ut)
        session.commit()
    # post ephemeral confirmation
    try:
        await app.client.chat_postEphemeral(
            channel=user_id,
            user=user_id,
            text=f"Saved: track={track}, contact={contact}"
        )
    except Exception:
        pass

# ---------- Event listener: message in channels ----------
@app.event("message")
async def handle_message_events(event, say, logger):
    # Only process messages posted in #announcements-projects (you can check channel id instead)
    text = event.get("text", "") or ""
    channel = event.get("channel")
    subtype = event.get("subtype")
    # ignore bot messages and edits
    if subtype is not None:
        return
    # TODO: replace with actual channel ID for #announcements-projects to avoid false positives
    # We'll accept any message that looks like an announcement (contains @channel or STAGE)
    is_announcement = ("@channel" in text) or ("stage" in text.lower()) or ("task" in text.lower())
    if not is_announcement:
        return
    # detect track
    track = detect_track_by_keywords(text)
    # fallback: ask humans or default to broadcast (we'll skip if None)
    if not track:
        # optional: you can try a simple ML classification here
        print("No track detected for message, skipping:", text[:80])
        return
    # summarise
    title = f"New {track.capitalize()} Announcement"
    summary = summarize_text(text, max_length=150)
    # build link to original message if available (Slack permalink API)
    try:
        permalink = await app.client.chat_getPermalink(channel=channel, message_ts=event.get("ts"))
        slack_link = permalink.get("permalink")
    except Exception:
        slack_link = None
    # notify users
    await notify_track_users(track, title, summary, text, slack_link)

# ---------- FastAPI routes for Slack events and health ----------
@fastapi_app.post("/slack/events")
async def endpoint(req: Request):
    # Try to parse JSON first
    try:
        data = await req.json()
    except Exception:
        data = None

    # Handle Slack's URL verification challenge (JSON)
    if data and data.get("type") == "url_verification":
        return {"challenge": data["challenge"]}

    # Otherwise, pass the raw request to Slack Bolt handler
    return await handler.handle(req)



@fastapi_app.get("/health")
async def health():
    return {"ok": True}

# If you want to run with 'uvicorn main:fastapi_app' or include startup/shutdown events
