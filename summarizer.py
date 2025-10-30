import re
from transformers import pipeline

summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

def detect_track(task_text: str):
    text = task_text.lower()

    if any(word in text for word in ["react", "tailwind", "frontend", "ui ", "css", "chakra", "nextjs", "vue", "design system"]):
        return "frontend"
    if any(word in text for word in ["figma", "wireframe", "prototype", "ui/ux", "design", "user flow"]):
        return "uiux"
    if any(word in text for word in ["api", "database", "backend", "server", "django", "express", "fastapi", "spring", "endpoint"]):
        return "backend"
    if any(word in text for word in ["android", "flutter", "kotlin", "swift", "mobile"]):
        return "mobile"
    if any(word in text for word in ["docker", "deployment", "devops", "ci/cd", "kubernetes", "aws", "infrastructure"]):
        return "devops"
    if any(word in text for word in ["data", "machine learning", "dataset", "ai", "model"]):
        return "data"

    return "general"


def extract_structured_info(task_text: str):
    # Deadline keywords expanded
    deadline_match = re.search(
        r"(deadline|due|submission)\s*[:\-]*\s*(.*)",
        task_text,
        re.IGNORECASE
    )
    deadline = deadline_match.group(2).strip() if deadline_match else "Not specified"

    # Endpoint extraction is only useful for backend
    track = detect_track(task_text)
    endpoints = []
    if track == "backend":
        endpoints = re.findall(r"(GET|POST|DELETE|PUT|PATCH)\s+[^\s]+", task_text)

    return {"endpoints": endpoints, "deadline": deadline, "track": track}


def get_deliverables_for_track(track: str):
    deliverables = {
        "frontend": [
            "Build responsive UI components",
            "Implement state management",
            "Add loading & error states",
            "Deploy demo (Vercel/Netlify)",
            "Provide README + screenshots"
        ],
        "uiux": [
            "Create wireframes + UI mockups",
            "Develop responsive high-fidelity designs",
            "Share Figma link + prototype",
            "Deliver design system components",
            "Export assets + documentation"
        ],
        "backend": [
            "Implement API endpoints",
            "Add validation + DB persistence",
            "Include testing (if needed)",
            "Provide Postman/API docs",
            "Add setup instructions"
        ],
        "mobile": [
            "Build mobile screens and navigation",
            "Implement state handling",
            "Ensure responsiveness + offline mode",
            "Deploy build (APK/TestFlight)",
            "Provide demo video + README"
        ],
        "devops": [
            "Setup CI/CD pipeline",
            "Deploy scalable environment",
            "Add monitoring + logging",
            "Provide Docker/Terraform if needed",
            "Write deployment docs"
        ],
        "data": [
            "Prepare and clean dataset",
            "Train + evaluate model or pipeline",
            "Show performance metrics",
            "Provide notebooks/code",
            "Write insights report"
        ],
        "general": [
            "Understand requirements",
            "Deliver working solution",
            "Test thoroughly",
            "Write clear documentation"
        ],
    }
    return deliverables.get(track, deliverables["general"])


def summarize_task(task_text: str, forced_track: str = None):
    # Safety: avoid very long sequences
    if len(task_text.split()) > 700:
        task_text = " ".join(task_text.split()[:700])

    # Summarization with fallback safety
    try:
        ai_summary = summarizer(
            task_text,
            max_length=120,
            min_length=50,
            do_sample=False
        )[0]["summary_text"]
    except Exception:
        ai_summary = "Summary unavailable — task processed without AI model."

    structured = extract_structured_info(task_text)

    # Override detected track if Slack already sent one
    track = forced_track or structured["track"]

    deliverables = get_deliverables_for_track(track)
    deliverables_text = "\n".join([f"- {d}" for d in deliverables])

    # Handle endpoints only when relevant
    if track == "backend" and structured["endpoints"]:
        endpoints_text = "\n".join([f"- `{e}`" for e in structured["endpoints"]])
    else:
        endpoints_text = "_Not applicable_"

    return f"""
📢 *New {track.capitalize()} Task Summary*

*🧭 Summary:* {ai_summary}

*🗓 Deadline:* {structured['deadline']}

*🔑 Key Endpoints (if any):*
{endpoints_text}

*✅ Key Deliverables:*
{deliverables_text}
""".strip()

# import re
# from transformers import pipeline

# summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

# def detect_track(task_text: str):
#     task_text_lower = task_text.lower()

#     if any(word in task_text_lower for word in ["react", "tailwind", "frontend", "ui", "css", "chakra", "nextjs", "vue", "design system"]):
#         return "frontend"
#     if any(word in task_text_lower for word in ["figma", "wireframe", "prototype", "ui/ux", "design", "user flow"]):
#         return "uiux"
#     if any(word in task_text_lower for word in ["api", "database", "backend", "server", "django", "express", "fastapi", "spring", "endpoint"]):
#         return "backend"
#     if any(word in task_text_lower for word in ["android", "flutter", "kotlin", "swift", "mobile"]):
#         return "mobile"
#     if any(word in task_text_lower for word in ["docker", "deployment", "devops", "ci/cd", "kubernetes", "aws", "infrastructure"]):
#         return "devops"
#     if any(word in task_text_lower for word in ["data", "machine learning", "dataset", "ai", "model"]):
#         return "data"

#     # Default fallback
#     return "general"


# def extract_structured_info(task_text: str):
#     endpoints = re.findall(r"(GET|POST|DELETE|PUT|PATCH)\s+[^\s]+", task_text)
#     deadline_match = re.search(r"Deadline[:\-\s]*([A-Za-z0-9,:\s|]+)", task_text)
#     deadline = deadline_match.group(1).strip() if deadline_match else "Not specified"
    
#     track = detect_track(task_text)
#     return {"endpoints": endpoints, "deadline": deadline, "track": track}


# def get_deliverables_for_track(track: str):
#     deliverables = {
#         "frontend": [
#             "Build responsive UI components",
#             "Ensure proper state management",
#             "Add loading & error states",
#             "Deploy preview link (Vercel/Netlify)",
#             "Provide documentation & screenshots"
#         ],
#         "uiux": [
#             "Create wireframes and mockups",
#             "Design responsive UI screens",
#             "Provide design system / components",
#             "Share Figma link and prototype",
#             "Export assets/documentation"
#         ],
#         "backend": [
#             "Implement required API endpoints",
#             "Ensure validation & persistence",
#             "Write clear documentation",
#             "Add tests if applicable",
#             "Provide Postman or API docs"
#         ],
#         "mobile": [
#             "Build mobile UI screens",
#             "Implement navigation & state handling",
#             "Ensure responsiveness & offline handling",
#             "Deploy APK/TestFlight build",
#             "Provide demo video & docs"
#         ],
#         "devops": [
#             "Set up CI/CD pipeline",
#             "Configure hosting infrastructure",
#             "Ensure monitoring & logging",
#             "Provide Terraform/Docker files if needed",
#             "Write deployment documentation"
#         ],
#         "data": [
#             "Clean and preprocess data",
#             "Train/test ML model or analytics pipeline",
#             "Show evaluation metrics",
#             "Provide notebook/scripts",
#             "Write insights report"
#         ],
#         "general": [
#             "Understand task scope & goals",
#             "Produce working deliverable",
#             "Test functionality",
#             "Write clear documentation"
#         ]
#     }

#     return deliverables.get(track, deliverables["general"])


# def summarize_task(task_text: str):
#     if len(task_text.split()) > 700:
#         task_text = " ".join(task_text.split()[:700])

#     ai_summary = summarizer(
#         task_text,
#         max_length=120,
#         min_length=50,
#         do_sample=False
#     )[0]["summary_text"]

#     structured = extract_structured_info(task_text)
#     endpoints_text = "\n".join([f"- `{e}`" for e in structured["endpoints"]]) or "No endpoints listed"

#     deliverables_list = get_deliverables_for_track(structured["track"])
#     deliverables_text = "\n".join([f"- {d}" for d in deliverables_list])

#     return f"""
# 📢 *New {structured['track'].capitalize()} Task Summary*

# *🧭 Summary:* {ai_summary}

# *🗓 Deadline:* {structured['deadline']}

# *🔑 Key Endpoints (if any):*
# {endpoints_text}

# *✅ Key Deliverables:*
# {deliverables_text}
# """.strip()
