# summarizer.py
import re
from transformers import pipeline

summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

def extract_structured_info(task_text: str):
    endpoints = re.findall(r"(GET|POST|DELETE|PUT|PATCH)\s+[^\s]+", task_text)
    deadline_match = re.search(r"Deadline[:\-\s]*([A-Za-z0-9,:\s|]+)", task_text)
    deadline = deadline_match.group(1).strip() if deadline_match else "Not specified"
    return {"endpoints": endpoints, "deadline": deadline}


def summarize_task(task_text: str):
    # 🚧 truncate very long messages to avoid model crash
    if len(task_text.split()) > 700:
        task_text = " ".join(task_text.split()[:700])

    ai_summary = summarizer(task_text, max_length=120, min_length=50, do_sample=False)[0]["summary_text"]

    structured = extract_structured_info(task_text)
    endpoints_text = "\n".join([f"- `{e}`" for e in structured["endpoints"]]) or "No endpoints listed"

    return f"""
📢 *New Task Summary*

*🧭 Summary:* {ai_summary}

*🗓 Deadline:* {structured['deadline']}

*🔑 Key Endpoints:*
{endpoints_text}

*✅ Core Deliverables:* 
- Implement required API or logic
- Ensure validation & persistence
- Provide clear README and instructions
""".strip()

# import re
# from transformers import pipeline

# summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

# def extract_structured_info(task_text: str):
#     endpoints = re.findall(r"(GET|POST|DELETE|PUT|PATCH)\s+[^\s]+", task_text)
#     deadline_match = re.search(r"Deadline[:\-\s]*([A-Za-z0-9,:\s|]+)", task_text)
#     deadline = deadline_match.group(1).strip() if deadline_match else "Not specified"
#     return {"endpoints": endpoints, "deadline": deadline}

# def summarize_task(task_text: str):
#     ai_summary = summarizer(task_text, max_length=120, min_length=50, do_sample=False)[0]["summary_text"]
#     structured = extract_structured_info(task_text)
#     endpoints_text = "\n".join([f"- `{e}`" for e in structured["endpoints"]]) or "No endpoints listed"
#     return f"""
# 📢 *New Task Summary*

# *🧭 Summary:* {ai_summary}

# *🗓 Deadline:* {structured['deadline']}

# *🔑 Key Endpoints:*
# {endpoints_text}

# *✅ Core Deliverables:* 
# - Implement required API or logic
# - Ensure validation & persistence
# - Provide clear README and instructions
# """.strip()
