## Status

![E2E (Render)](https://github.com/Lucy437/allyai-chatbot/actions/workflows/e2e.yml/badge.svg)

![OpenAI Smoke](https://github.com/Lucy437/allyai-chatbot/actions/workflows/openai_smoke.yml/badge.svg)
![Twilio Smoke](https://github.com/Lucy437/allyai-chatbot/actions/workflows/twilio_smoke.yml/badge.svg)

![Tests](https://github.com/Lucy437/allyai-chatbot/actions/workflows/tests.yml/badge.svg)
![CI](https://github.com/Lucy437/allyai-chatbot/actions/workflows/ci.yml/badge.svg)





# AllyAI – Empowering Young Women with AI Coaching  

AllyAI is a **WhatsApp-based, gender-transformative AI coach** designed for girls and young women (ages 15–25) to build healthier relationships, boost confidence, and strengthen emotional wellbeing and resilience.  

It blends:  
-  **Supportive, safe AI coaching** that feel warm and relatable  
-  **Gamified learning tracks** to practice skills in a fun, engaging way  
-  **Built-in safety guardrails** that detect signs of emotional distress or crisis and ensure responsible, ethical use.


---

## Features  

- **Conversational Coaching**  
  - AllyAI speaks like a supportive big sister or mentor.  
  - Focused on relationships, confidence, boundaries, and self-worth.  

- **Assessment & Growth Identity**  
  - 6-question quiz maps users into “AllyAI Identities” (e.g., *Guardian Queen*, *Healer Oracle*).  
  - Provides personalized growth feedback.  

- **Gamified Learning (“What Would You Do?”)**  
  - 3 thematic tracks: *Confidence*, *Recognizing Red Flags*, *Setting Boundaries*.  
  - Scenario-based choices, mini-lessons, challenges, and point tracking.  

- **AI-Powered Advice**  
  - Context-sensitive coaching flow (validation → psychoeducation → empowerment → planning → closing).  
  - Smooth fallback to free-chat mode for open conversations.  

- **Safety Guardrail Agent (AI Watchdog)**  
  - Runs in parallel to all chats, scanning history + latest input.  
  - Classifies messages as `SAFE`, `DISTRESS`, or `CRISIS`.  
  - If distress is detected, AllyAI sends **gentle supportive nudges**.  
  - If crisis is detected (e.g. suicidal thoughts), AllyAI **connects users to local/global hotlines** (via [findahelpline.com](https://findahelpline.com)).  

- **Data Logging & Analytics**  
  - Tracks user journeys (category chosen, assessment scores, distress/crisis counts).  
  - Can generate aggregated insights for program evaluation (while respecting user privacy).  


---
```plaintext
allyai-chatbot/
├─ main.py            # Main Flask app: Twilio webhook handler, conversation flow, GPT integration
├─ helpers.py         # Utility functions: system prompt, intent detection, step progression, prompt generation
├─ assessment.py      # Self-assessment module: questions, scoring logic, identity assignment, feedback generation
├─ analytics.py       # Database + analytics: init, log events, create/update user profiles, fetch profile
├─ guardrail.py       # Safety layer: runs guardrail checks (flags harmful/distress content)
├─ scenarios.json     # Scenario library: predefined user situations grouped by category (e.g., partner, friends, family)
├─ tracks.json        # Growth tracks for "What Would You Do?" game: lessons, options, feedback, challenges
├─ requirements.txt   # Python dependencies for production (Flask, Twilio, OpenAI, Gunicorn, Postgres driver, etc.)
├─ pyproject.toml     # Project metadata + dependencies (modern packaging standard)
├─ uv.lock            # Lockfile for reproducible installs (used with `uv` / PEP 582 compatible tooling)
├─ README.md          # Project documentation (overview, setup, usage, contribution guide)

```
---

##  Tech Stack  

- **Backend Framework**: Flask (Python)  
- **AI Model**: OpenAI GPT (chat + classification)  
- **Messaging**: Twilio WhatsApp Sandbox  
- **Database**: SQLite (via `analytics.py`)  
- **Deployment**: Render  

---

## Quick Start  

### Connect via WhatsApp  
- Send `join deal-chest` to **+1 415 523 8886** (Twilio sandbox).  
- Then message your bot
- Type Hi to get started.
- At any time, type Restart to return to the main menu.
- When selecting options, reply only with the number (e.g., 1 or 2) — do not add commas, periods, or extra characters.

#### Troubleshooting 
- If you don’t get a reply right away, wait a few seconds and try again.
- Make sure you’re sending messages to the correct number (+1 415 523 8886).
- If the sandbox session expires, you may need to resend join deal-chest to reconnect.


---

##  Guardrail Agent  

- Lives in `guardrail.py`  
- Runs as an independent AI agent in a background thread.  
- Uses OpenAI to classify risk in **real time**.  
- **Response logic**:  

| Classification | Action |
|----------------|--------|
| SAFE | Do nothing |
| DISTRESS | Send supportive “you’re not alone” message |
| CRISIS | Send urgent message with hotline links |

---

##  Social Impact Alignment  

- **Empowerment**: Helps girls practice confidence, boundaries, and healthy relationships.  
- **Safety**: Detects distress early and connects youth to *human* support networks.  
- **Scalable**: Built on WhatsApp, already widely accessible to young women globally.  
- **Ethical AI**: Warm, non-judgmental design; explicit crisis guardrails; minimal data collection.  

---

##  Safeguards  

- No sensitive data stored beyond what’s needed for conversation continuity.  
- Distress/crisis classifications logged **only in aggregate** for reporting.  
- Clear user privacy boundaries (no data shared outside system).  

---

## License  

MIT License – open for nonprofits, social good, and research.  

---

AllyAI is not a replacement for therapy or crisis intervention.  
It is a **supportive AI coach** that empowers youth and connects them to real help when needed.  
