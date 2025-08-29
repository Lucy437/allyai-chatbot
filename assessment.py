# assessment.py
# AllyAI self-assessment: questions, state helpers, scoring, identity, feedback.

from typing import Dict, List, Optional

# ------------------------- Questions ------------------------- #
# Each question has: id, text, dimension, options (a-d), scores (a-d → 1..4)
assessment_questions: List[Dict] = [
    {
        "id": 1,
        "text": "You just got invited to speak briefly at your school or group meeting about a topic you’re passionate about. What’s your first reaction?",
        "dimension": "Confidence",
        "options": {
            "a": "I'm not good at public speaking. I’ll just pass.",
            "b": "I could do it if I have time to prepare, but I’m not sure I’ll be taken seriously.",
            "c": "I’ll try! Even if it’s not perfect, it’s a good learning experience.",
            "d": "Absolutely! I love speaking up and sharing my thoughts.",
        },
        "scores": {"a": 1, "b": 2, "c": 3, "d": 4},
    },
    {
        "id": 2,
        "text": "Your friend is upset because she feels left out after you spent more time with another group. She brings it up to you. How do you respond?",
        "dimension": "Empathy",
        "options": {
            "a": "Ugh, I didn’t do anything wrong — she’s overreacting.",
            "b": "I say sorry quickly, just to end the drama.",
            "c": "I try to understand where she’s coming from and talk it through.",
            "d": "I ask her more about how she feels and tell her I want us both to feel included.",
        },
        "scores": {"a": 1, "b": 2, "c": 3, "d": 4},
    },
    {
        "id": 3,
        "text": "After a fight with someone close to you, how do you usually reflect on it?",
        "dimension": "Self-Awareness",
        "options": {
            "a": "I don’t really think about it — I move on fast.",
            "b": "I overthink it for days and wonder what they must think of me.",
            "c": "I try to look at what triggered me and how I reacted.",
            "d": "I notice my emotions, patterns, and talk to someone to get perspective.",
        },
        "scores": {"a": 1, "b": 2, "c": 3, "d": 4},
    },
    {
        "id": 4,
        "text": "You’re dating someone who often makes jokes at your expense in front of others. How do you respond?",
        "dimension": "Self-Respect",
        "options": {
            "a": "It’s not a big deal — I laugh along to keep things cool.",
            "b": "It hurts, but I stay quiet and try to ignore it.",
            "c": "I bring it up later and say it made me uncomfortable.",
            "d": "I call it out calmly in the moment and let them know it’s not okay.",
        },
        "scores": {"a": 1, "b": 2, "c": 3, "d": 4},
    },
    {
        "id": 5,
        "text": "A classmate or coworker takes credit for your idea in a group project. What do you do?",
        "dimension": "Communication",
        "options": {
            "a": "I keep quiet — I don’t want to seem rude or jealous.",
            "b": "I hint that it was actually my idea, hoping others notice.",
            "c": "I talk to them one-on-one and explain how it made me feel.",
            "d": "I address it respectfully in front of the group to clarify.",
        },
        "scores": {"a": 1, "b": 2, "c": 3, "d": 4},
    },
    {
        "id": 6,
        "text": "A friend constantly calls late at night to vent, even when you’ve told them you’re tired or studying. What do you do?",
        "dimension": "Boundary-Setting",
        "options": {
            "a": "I always pick up — they need me.",
            "b": "I ignore the call but feel guilty after.",
            "c": "I let them know I care, but can’t talk at night anymore.",
            "d": "I set a firm boundary and suggest specific times to talk instead.",
        },
        "scores": {"a": 1, "b": 2, "c": 3, "d": 4},
    },
]

# ------------------------- Session helpers ------------------------- #
def get_next_assessment_question(
    user_sessions: Dict[str, dict],
    user_id: str,
    questions: Optional[List[Dict]] = None,
) -> Optional[str]:
    """
    Format and return the next question text for a user, or None if finished.
    Expects user_sessions[user_id] to have: {"current_q": int, "answers": list}
    """
    qs = questions or assessment_questions
    session = user_sessions[user_id]
    q_index = session["current_q"]
    if q_index < len(qs):
        q = qs[q_index]
        options_text = "\n".join([f"{opt.upper()}. {text}" for opt, text in q["options"].items()])
        return f"{q['text']}\n\n{options_text}"
    return None


def handle_assessment_answer(
    user_sessions: Dict[str, dict],
    user_id: str,
    answer_letter: str,
    questions: Optional[List[Dict]] = None,
) -> None:
    """
    Record the user's answer and advance the index.
    Stores {"dimension": <str>, "score": <int>} into session["answers"].
    """
    qs = questions or assessment_questions
    session = user_sessions[user_id]
    q_index = session["current_q"]
    q = qs[q_index]
    letter = (answer_letter or "").strip().lower()[:1]
    score = q["scores"].get(letter, 0)
    session["answers"].append({"dimension": q["dimension"], "score": score})
    session["current_q"] += 1

# ------------------------- Scoring & feedback ------------------------- #
def calculate_trait_scores(answers: List[Dict]) -> Dict[str, int]:
    """Aggregate scores per dimension."""
    scores: Dict[str, int] = {}
    for a in answers:
        scores[a["dimension"]] = scores.get(a["dimension"], 0) + a["score"]
    return scores


def assign_identity(scores: Dict[str, int]) -> str:
    """
    Pick an identity based on the top two dimensions.
    """
    if not scores:
        return "👑 The Growth Queen\nYou're growing — keep going!"
    top_two = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:2]
    combo = frozenset([t[0] for t in top_two])

    identity_map = {
        frozenset(["Confidence", "Communication"]): (
            "👑 The Empowered Queen\n"
            "You own your voice and lead with unapologetic strength."
        ),
        frozenset(["Self-Awareness", "Empathy"]): (
            "🪞 The Healer Oracle\n"
            "Your empathy is matched by deep inner wisdom."
        ),
        frozenset(["Boundary-Setting", "Self-Respect"]): (
            "🛡️ The Guardian Queen\n"
            "You defend your peace with grace and clarity."
        ),
    }
    return identity_map.get(
        combo,
        "👑 The Growth Queen\nYou're on a beautiful path of self-discovery — keep showing up!",
    )


def generate_feedback(scores: Dict[str, int], identity: str) -> str:
    """
    Produce the final feedback string with simple percent bars.
    (Each answer is 1–4, so 4 ≈ 100% for a single question per dimension.)
    """
    if not scores:
        return "Let’s try the assessment again — I didn’t catch any answers yet."

    bars = "\n".join([f"{trait}: {int(score * 25)}%" for trait, score in scores.items()])
    strongest = max(scores, key=scores.get)
    weakest = min(scores, key=scores.get)
    return (
        f"🌟 Your AllyAI Identity:\n{identity}\n\n"
        f"Here’s your growth profile:\n{bars}\n\n"
        f"Your current strength is **{strongest}**.\n"
        f"We’ll also build your **{weakest}** — that’s how you become unstoppable 💫"
    )
