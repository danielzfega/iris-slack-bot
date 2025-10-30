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
from summarizer import summarize_task

load_dotenv()
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
HUGGINGFACE_MODEL = os.environ.get("HUGGINGFACE_MODEL", "sshleifer/distilbart-cnn-12-6")
DATABASE_URL = os.environ.get("DATABASE_URL")
HOST_URL = os.environ.get("HOST_URL", "")


class UserTrack(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str
    tracks: str  # comma-separated list: "backend,frontend"
    contact: str = "slack"
    email: Optional[str] = None

    def track_list(self) -> List[str]:
        return [t.strip() for t in self.tracks.split(",") if t.strip()]


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


async def notify_track_users(tracks: List[str], title: str, summary: str, original_text: str, slack_link: Optional[str]):
    with Session(engine) as session:
        all_users = session.exec(select(UserTrack)).all()

    for u in all_users:
        user_tracks = u.track_list()
        if not any(t in tracks for t in user_tracks):
            continue  # skip users not in any selected track

        dm_text = f"*{title}*\n{summary}\n"
        if slack_link:
            dm_text += f"\n<{slack_link}|View original announcement>"
        dm_text += "\n\n_This was sent by Iris_"

        try:
            await app.client.chat_postMessage(channel=u.user_id, text=dm_text)
        except Exception as e:
            print("DM failed for", u.user_id, e)



@app.command("/register-track")
async def handle_register(ack, body, client, logger):
    await ack()
    trigger_id = body.get("trigger_id")
    await client.views_open(
        trigger_id=trigger_id,
        view={
            "type": "modal",
            "callback_id": "register_track_modal",
            "title": {"type": "plain_text", "text": "Register Tracks"},
            "submit": {"type": "plain_text", "text": "Save"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "track_select",
                    "element": {
                        "type": "multi_static_select",
                        "action_id": "tracks_selected",
                        "placeholder": {"type": "plain_text", "text": "Choose one or more tracks"},
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
                    "label": {"type": "plain_text", "text": "Select your tracks"},
                },
                {
                    "type": "input",
                    "block_id": "contact_input",
                    "element": {
                        "type": "static_select",
                        "action_id": "contact_selected",
                        "placeholder": {"type": "plain_text", "text": "Preferred contact method"},
                        "options": [
                            {"text": {"type": "plain_text", "text": "Slack DM"}, "value": "slack"},
                            {"text": {"type": "plain_text", "text": "Email (provide below)"}, "value": "email"},
                        ],
                    },
                    "label": {"type": "plain_text", "text": "Contact method"},
                },
                {
                    "type": "input",
                    "block_id": "email_block",
                    "optional": True,
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "email_input",
                        "placeholder": {"type": "plain_text", "text": "you@example.com"},
                    },
                    "label": {"type": "plain_text", "text": "Email (optional)"},
                },
            ],
        },
    )


@app.view("register_track_modal")
async def handle_view_submission(ack, body, view, logger):
    await ack()
    user_id = body["user"]["id"]
    values = view["state"]["values"]
    selected_tracks = values["track_select"]["tracks_selected"].get("selected_options", [])
    tracks = [opt["value"] for opt in selected_tracks]
    contact = values["contact_input"]["contact_selected"]["selected_option"]["value"]
    email = values.get("email_block", {}).get("email_input", {}).get("value")

    with Session(engine) as session:
        existing = session.exec(select(UserTrack).where(UserTrack.user_id == user_id)).first()
        if existing:
            existing.tracks = ",".join(tracks)
            existing.contact = contact
            existing.email = email
            session.add(existing)
        else:
            ut = UserTrack(user_id=user_id, tracks=",".join(tracks), contact=contact, email=email)
            session.add(ut)
        session.commit()

    await app.client.chat_postEphemeral(
        channel=user_id,
        user=user_id,
        text=f"✅ Saved: tracks={', '.join(tracks)}, contact={contact}"
    )


# ---------- Event listener: message in channels ----------
@app.event("message")
async def handle_message_events(event, say, logger):
    text = event.get("text", "")
    channel = event.get("channel")
    subtype = event.get("subtype")
    if subtype:  # ignore bots/edits
        return

    if not ("@channel" in text or "task" in text.lower() or "stage" in text.lower()):
        return

    detected_track = detect_track_by_keywords(text)
    if not detected_track:
        return

    summary = summarize_task(text)
    title = f"New {detected_track.capitalize()} Task"
    try:
        permalink = await app.client.chat_getPermalink(channel=channel, message_ts=event.get("ts"))
        slack_link = permalink.get("permalink")
    except Exception:
        slack_link = None

    await notify_track_users([detected_track], title, summary, text, slack_link)


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
