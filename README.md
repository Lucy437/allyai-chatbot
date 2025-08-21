# 📘 AllyAI – Empowering Young Women with AI Coaching  

AllyAI is a **WhatsApp-based AI coach** that supports girls and young women (15–25) with relationships, confidence, and emotional wellbeing.  
It combines **warm coaching conversations**, **gamified learning tracks**, and a **safety guardrail agent** that detects signs of emotional distress or crisis.  

This project is designed for social impact and is aligned with UNICEF’s goals for digital youth empowerment and protection.  

---

## 🌟 Features  

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

## 🛠️ Tech Stack  

- **Backend Framework**: Flask (Python)  
- **AI Model**: OpenAI GPT (chat + classification)  
- **Messaging**: Twilio WhatsApp Sandbox  
- **Database**: SQLite (via `analytics.py`)  
- **Deployment**: Render  

---

## 🚀 Quick Start  

### 5. Connect via WhatsApp  
- Send `join deal-chest` to **+1 415 523 8886** (Twilio sandbox).  
- Then message your bot 🎉  

---

## 🧠 Guardrail Agent  

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

## 🌍 Social Impact Alignment  

- **Empowerment**: Helps girls practice confidence, boundaries, and healthy relationships.  
- **Safety**: Detects distress early and connects youth to *human* support networks.  
- **Scalable**: Built on WhatsApp, already widely accessible to young women globally.  
- **Ethical AI**: Warm, non-judgmental design; explicit crisis guardrails; minimal data collection.  

---

## 🔒 Safeguards  

- No sensitive data stored beyond what’s needed for conversation continuity.  
- Distress/crisis classifications logged **only in aggregate** for reporting.  
- Clear user privacy boundaries (no data shared outside system).  

---

## 📜 License  

MIT License – open for nonprofits, social good, and research.  

---

✨ AllyAI is not a replacement for therapy or crisis intervention.  
It is a **supportive AI coach** that empowers youth and connects them to real help when needed.  
