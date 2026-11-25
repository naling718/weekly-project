"""Rule-based first-pass triage of an AI system description into EU AI Act risk tiers."""
import re
from dataclasses import dataclass

TIERS = ["minimal", "limited", "high", "unacceptable"]  # lowest to highest


@dataclass(frozen=True)
class Rule:
    tier: str
    ref: str
    title: str
    patterns: tuple
    unless: tuple = ()


# shortcut: keyword regexes miss paraphrases and negation ("does NOT score citizens"); swap in a trained text classifier once there is labelled data.
RULES = [
    # Article 5: prohibited practices
    Rule("unacceptable", "Art. 5(1)(a)", "Subliminal or manipulative techniques",
         (r"sublimina", r"manipulat\w* (user|people|person|behaviou?r)", r"dark pattern")),
    Rule("unacceptable", "Art. 5(1)(b)", "Exploiting vulnerabilities of age, disability or social situation",
         (r"exploit\w* .{0,40}(child|elderly|vulnerab|disab|poverty|debt)",)),
    Rule("unacceptable", "Art. 5(1)(c)", "Social scoring",
         (r"social scor", r"trustworthiness scor", r"citizen scor")),
    Rule("unacceptable", "Art. 5(1)(d)", "Predicting crime from profiling or personality",
         (r"predict\w* .{0,40}(crime|criminal|offen[cd]|reoffend)", r"crime prediction")),
    Rule("unacceptable", "Art. 5(1)(e)", "Untargeted scraping of facial images",
         (r"scrap\w* .{0,40}fac(e|ial)", r"fac(e|ial) .{0,30}scrap")),
    Rule("unacceptable", "Art. 5(1)(f)", "Emotion recognition at work or in education",
         (r"emotion\w* .{0,60}(employee|worker|workplace|staff|student|classroom|pupil)",
          r"(employee|worker|workplace|staff|student|classroom|pupil)\w* .{0,60}emotion")),
    Rule("unacceptable", "Art. 5(1)(g)", "Biometric categorisation inferring sensitive traits",
         (r"(infer|categori[sz]|deduc|predict)\w* .{0,60}(race|ethnic|religio|political|sexual orientation|trade union)",)),
    Rule("unacceptable", "Art. 5(1)(h)", "Real-time remote biometric identification in public for policing",
         (r"real[- ]time .{0,40}(facial recognition|biometric identification)",)),
    # Annex III and Article 6(1): high-risk
    Rule("high", "Annex III(1)", "Biometric identification or categorisation",
         (r"facial recognition", r"biometric (identification|categori[sz]ation|verification)", r"emotion recognition")),
    Rule("high", "Annex III(2)", "Critical infrastructure safety component",
         (r"(electricity|power grid|water supply|gas supply|heating|road traffic|digital infrastructure)",)),
    Rule("high", "Annex III(3)", "Education and vocational training",
         (r"(admission|\bexams?\b|proctor|grading|grade\w* (student|essay)|learning outcome)",)),
    Rule("high", "Annex III(4)", "Employment and worker management",
         (r"(recruit|\bcvs?\b|resume|résumé|job applica|candidate|hiring|promotion|termination|task allocation|employee monitoring|worker monitoring)",)),
    Rule("high", "Annex III(5)", "Access to essential private and public services",
         (r"(credit ?worth|credit scor|loan (approv|applica|decision)|public benefit|welfare|social security)",
          r"(life|health) insurance .{0,40}(pric|risk)", r"emergency (call|dispatch)"),
         unless=(r"fraud",)),
    Rule("high", "Annex III(6)", "Law enforcement",
         (r"(police|law enforcement|criminal investigation|evidence reliability)",)),
    Rule("high", "Annex III(7)", "Migration, asylum and border control",
         (r"(asylum|visa applica|border control|migrant|immigration|residence permit)",)),
    Rule("high", "Annex III(8)", "Justice and democratic processes",
         (r"(judicial|court ruling|judge|sentencing|election|voting behaviou?r)",)),
    Rule("high", "Art. 6(1) + Annex I", "Safety component of a regulated product",
         (r"(medical device|diagnos|surgical|machinery|\btoys?\b|vehicle|aviation|lift safety)",)),
    # Article 50: transparency
    Rule("limited", "Art. 50(1)", "Interacts directly with people",
         (r"chat ?bot", r"virtual assistant", r"conversational", r"talks? to (customers|users)")),
    Rule("limited", "Art. 50(2)", "Generates synthetic content",
         (r"generat\w* .{0,40}(image|video|audio|voice|text|content)", r"text[- ]to[- ](image|speech|video)")),
    Rule("limited", "Art. 50(4)", "Deepfakes",
         (r"deep ?fake", r"face swap", r"voice clon")),
]

OBLIGATIONS = {
    "unacceptable": [
        "Banned in the EU since 2 February 2025 (Art. 5). It cannot be placed on the market or used.",
        "Fines up to EUR 35m or 7% of worldwide annual turnover (Art. 99(3)).",
    ],
    "high": [
        "Risk management system (Art. 9)",
        "Data governance for training, validation and test data (Art. 10)",
        "Technical documentation (Art. 11) and automatic event logging (Art. 12)",
        "Instructions and transparency for deployers (Art. 13)",
        "Human oversight (Art. 14)",
        "Accuracy, robustness and cybersecurity (Art. 15)",
        "Conformity assessment (Art. 43) and registration in the EU database (Art. 49)",
        "Annex III systems: applies from 2 December 2027; Annex I products: 2 August 2028 (Regulation (EU) 2026/1744).",
    ],
    "limited": [
        "Tell people they are interacting with an AI system (Art. 50(1))",
        "Mark generated audio, image, video or text as machine-generated (Art. 50(2))",
        "Disclose deepfakes as artificially generated (Art. 50(4))",
    ],
    "minimal": [
        "No mandatory requirements beyond AI literacy for staff (Art. 4).",
        "Voluntary codes of conduct are encouraged (Art. 95).",
    ],
}

MAX_CHARS = 5000


def classify(description: str) -> dict:
    if not isinstance(description, str) or not description.strip():
        raise ValueError("description must be a non-empty string")
    if len(description) > MAX_CHARS:
        raise ValueError(f"description must be at most {MAX_CHARS} characters")
    text = description.lower()
    matches = []
    for rule in RULES:
        hit = next((m.group(0) for p in rule.patterns if (m := re.search(p, text))), None)
        if hit and not any(re.search(u, text) for u in rule.unless):
            matches.append({"tier": rule.tier, "ref": rule.ref, "title": rule.title, "evidence": hit})
    tier = max((m["tier"] for m in matches), key=TIERS.index, default="minimal")
    matches.sort(key=lambda m: -TIERS.index(m["tier"]))
    return {"tier": tier, "matches": matches, "obligations": OBLIGATIONS[tier]}
