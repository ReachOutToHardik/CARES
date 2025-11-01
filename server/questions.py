from typing import List, Dict

QUESTIONS: List[Dict] = [
    {
        "id": 1,
        "text": "When using an online tool that can write homework or answers, how likely is the child to use it to cheat?",
        "pillar": "E",
        "weight": 2,
        "rationale": "direct cheat-risk indicator."
    },
    {
        "id": 2,
        "text": "Does the child understand that online content (images/text) can be copyrighted and shouldn’t be reused without permission?",
        "pillar": "E",
        "weight": 1.5,
        "rationale": "copyright awareness"
    },
    {
        "id": 3,
        "text": "If an AI says something mean or false about someone, how likely is the child to believe and share it immediately?",
        "pillar": "CC",
        "weight": 2,
        "rationale": "impulse to share false info"
    },
    {
        "id": 4,
        "text": "Does the child know not to share passwords, OTPs, or private info online (including with \"friends\")?",
        "pillar": "DH",
        "weight": 2,
        "rationale": "direct privacy & safety"
    },
    {
        "id": 5,
        "text": "How often does the child use AI chatbots unsupervised (at home/phone) for entertainment or help?",
        "pillar": "TE",
        "weight": 1.5,
        "rationale": "exposure & unsupervised use"
    },
    {
        "id": 6,
        "text": "When given unclear instructions (e.g., \"Write this essay\"), can the child evaluate whether the result is appropriate or needs correction?",
        "pillar": "CC",
        "weight": 2,
        "rationale": "ability to assess generated content"
    },
    {
        "id": 7,
        "text": "If an online service asks for a photo or location, does the child ask an adult before sharing?",
        "pillar": "SG",
        "weight": 1.5,
        "rationale": "supervision before sharing sensitive data"
    },
    {
        "id": 8,
        "text": "Does the child understand that AI can be wrong and sometimes invent facts (\"hallucinate\")?",
        "pillar": "CC",
        "weight": 1.5,
        "rationale": "hallucination awareness"
    },
    {
        "id": 9,
        "text": "How frequently does the child post personal information (full name, school, address) on public platforms?",
        "pillar": "DH",
        "weight": 2,
        "rationale": "frequency of public sharing"
    },
    {
        "id": 10,
        "text": "Is there a family rule/time-limit about screen/AI use that the child follows?",
        "pillar": "SG",
        "weight": 1.5,
        "rationale": "presence and adherence to rules"
    },
    {
        "id": 11,
        "text": "If a chatbot gives steps that seem risky (e.g., \"hide something\" or \"bypass rules\"), would the child follow without question?",
        "pillar": "E",
        "weight": 2,
        "rationale": "willingness to follow risky instructions"
    },
    {
        "id": 12,
        "text": "Does the child know how to spot fake images or manipulated content?",
        "pillar": "CC",
        "weight": 1,
        "rationale": "visual literacy"
    },
    {
        "id": 13,
        "text": "How often does the child install apps/extensions without adult approval?",
        "pillar": "TE",
        "weight": 1.5,
        "rationale": "device risk from unvetted apps"
    },
    {
        "id": 14,
        "text": "Would the child share a private photo of someone else without permission?",
        "pillar": "E",
        "weight": 2,
        "rationale": "harassment/privacy risk"
    },
    {
        "id": 15,
        "text": "If an AI recommends a website/product, does the child check who made it or ask before using/buying?",
        "pillar": "DH",
        "weight": 1,
        "rationale": "checking source/trust"
    },
    {
        "id": 16,
        "text": "Does the child understand basic privacy settings on platforms they use (private account, blocking)?",
        "pillar": "DH",
        "weight": 1.5,
        "rationale": "platform privacy literacy"
    },
    {
        "id": 17,
        "text": "How well does the child manage attention when using AI tools (does use often disrupt homework/sleep)?",
        "pillar": "TE",
        "weight": 1.5,
        "rationale": "attention & disruption"
    },
    {
        "id": 18,
        "text": "Is the child able to follow a multi-step safety rule (e.g., check source → ask parent → only use accepted tool)?",
        "pillar": "CC",
        "weight": 1.5,
        "rationale": "multi-step rule following"
    },
    {
        "id": 19,
        "text": "Does the child know who to tell if they see something online that scares or confuses them?",
        "pillar": "SG",
        "weight": 1.5,
        "rationale": "knowing where to seek help"
    },
    {
        "id": 20,
        "text": "Does the child use AI to generate content and then pass it as their own work without disclosure?",
        "pillar": "E",
        "weight": 2,
        "rationale": "plagiarism/academic honesty"
    }
]

OPTIONS = [
    {"key": "A", "label": "A) 0 — High risk / Never / Yes (bad)", "score": 0},
    {"key": "B", "label": "B) 1 — Some concern / Rarely / Sometimes", "score": 1},
    {"key": "C", "label": "C) 2 — Mostly okay / Often / Usually", "score": 2},
    {"key": "D", "label": "D) 3 — Low risk / Good / Always / No", "score": 3},
]

PILLAR_WEIGHTS = {
    "E": 30,
    "DH": 25,
    "CC": 25,
    "TE": 10,
    "SG": 10,
}
