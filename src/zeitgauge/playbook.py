"""Phase and stability to product playbook.

Each entry names the feeling to design for, a one-line description and examples.
Sources of the mapping: the lipstick / affordable-treat literature, Rory
Sutherland's psychological value, Faith Popcorn's 'cocooning', and observed
category behaviour in past UK downturns and recoveries (docs/frameworks.md).
"""

from __future__ import annotations

PHASES: dict[str, list[tuple[str, str, str]]] = {
    "expansion": [
        ("Status", "Things people enjoy showing off.", "limited drops, personalised goods, travel extras"),
        ("Time saved", "Pay to skip chores.", "done-for-you services, delivery add-ons, subscriptions"),
        ("Novelty", "New experiences and gadgets.", "experience boxes, events, new tech accessories"),
    ],
    "slowdown": [
        ("Affordable premium", "Cheaper versions of things people already love.", "dupes, own-label premium, refill packs"),
        ("Flexible spending", "Let people pause or downsize rather than cancel.", "pausable subscriptions, smaller pack sizes"),
        ("Planning ahead", "Help people prepare for tighter times.", "budgeting tools, bulk-buy and batch-cook kits"),
    ],
    "downturn": [
        ("Small rewards", "Affordable treats that feel premium.", "minis, press-on nails, at-home cafe and salon rituals"),
        ("Make do and mend", "Fix, cook and make at home.", "repair kits, air fryer accessories, energy-saving home kits"),
        ("Money control", "Help people feel in charge of spending.", "budgeting templates, resale tools, cheaper swaps"),
    ],
    "recovery": [
        ("Treat yourself again", "Step up from small treats to mid-priced ones.", "affordable luxury, beauty and fragrance upgrades"),
        ("Catch-up purchases", "Replace what people put off.", "clothing basics, budget home upgrades, refurbished tech"),
        ("Getting out again", "Cheap experiences and socialising.", "clubs, local events, budget days out"),
    ],
}

OVERLAY: dict[str, list[tuple[str, str, str]]] = {
    "stable": [
        ("Belonging through fun", "Society feels steady, so social and playful products travel well.", "group activities, shareable products, hobbies"),
    ],
    "strained": [
        ("Safety and self-reliance", "Trust is low, so people want to feel prepared.", "home security, at-home health tests, power banks, savings products"),
        ("Comfort and nostalgia", "Familiar, warm things for an uneasy time.", "heated throws, comfort food, retro and vinyl, pet care"),
    ],
}

TECH_WAVE: dict[str, tuple[str, str]] = {
    "install": ("Build and hype phase", "Sell picks and shovels: templates, courses and tools that help ordinary people use the new technology."),
    "turn": ("Shake-out", "Prices fall and weak players vanish. Bundle the cheap technology into simple everyday products."),
    "deploy": ("Everyday phase", "The technology is cheap and trusted. Build mass-market products that use it quietly inside familiar things."),
}

# The phase that usually follows each phase: used to test idea robustness.
NEXT_PHASE = {"expansion": "slowdown", "slowdown": "downturn", "downturn": "recovery", "recovery": "expansion"}


def playbook(phase: str, stability: str, tech_wave: str | None = None) -> dict:
    out = {
        "phase": [dict(feeling=f, why=w, examples=e) for f, w, e in PHASES[phase]],
        "overlay": [dict(feeling=f, why=w, examples=e) for f, w, e in OVERLAY[stability]],
        "next_phase": NEXT_PHASE[phase],
    }
    if tech_wave:
        name, advice = TECH_WAVE[tech_wave]
        out["tech_wave"] = {"phase": name, "advice": advice}
    return out
