from __future__ import annotations

from typing import TypedDict


class TagSeed(TypedDict):
    name: str
    slug: str
    category: str
    icon: str


DEFAULT_TAGS: list[TagSeed] = [
    {"name": "Vibe Coding", "slug": "vibe-coding", "category": "technology", "icon": "💻"},
    {"name": "AI/ML", "slug": "ai-ml", "category": "technology", "icon": "🤖"},
    {"name": "DevOps", "slug": "devops", "category": "technology", "icon": "⚙️"},
    {"name": "Blockchain", "slug": "blockchain", "category": "technology", "icon": "⛓️"},
    {"name": "Web3", "slug": "web3", "category": "technology", "icon": "🌐"},
    {"name": "Cybersecurity", "slug": "cybersecurity", "category": "technology", "icon": "🔒"},
    {"name": "Data Science", "slug": "data-science", "category": "technology", "icon": "📊"},
    {"name": "Cloud Computing", "slug": "cloud-computing", "category": "technology", "icon": "☁️"},
    {"name": "Open Source", "slug": "open-source", "category": "technology", "icon": "🐙"},
    {"name": "Product Management", "slug": "product-management", "category": "business", "icon": "📱"},
    {"name": "Marketing", "slug": "marketing", "category": "business", "icon": "📢"},
    {"name": "Finance", "slug": "finance", "category": "business", "icon": "💰"},
    {"name": "Startups", "slug": "startups", "category": "business", "icon": "🚀"},
    {"name": "Remote Work", "slug": "remote-work", "category": "business", "icon": "🏠"},
    {"name": "Leadership", "slug": "leadership", "category": "business", "icon": "👔"},
    {"name": "Physics", "slug": "physics", "category": "science", "icon": "⚛️"},
    {"name": "Math", "slug": "math", "category": "science", "icon": "📐"},
    {"name": "Biology", "slug": "biology", "category": "science", "icon": "🧬"},
    {"name": "Chemistry", "slug": "chemistry", "category": "science", "icon": "🧪"},
    {"name": "UX Design", "slug": "ux-design", "category": "creative", "icon": "🎨"},
    {"name": "Gaming", "slug": "gaming", "category": "creative", "icon": "🎮"},
    {"name": "Music", "slug": "music", "category": "creative", "icon": "🎵"},
    {"name": "Writing", "slug": "writing", "category": "creative", "icon": "✍️"},
    {"name": "Film", "slug": "film", "category": "creative", "icon": "🎬"},
    {"name": "Healthcare", "slug": "healthcare", "category": "lifestyle", "icon": "🏥"},
    {"name": "Education", "slug": "education", "category": "lifestyle", "icon": "📚"},
    {"name": "Travel", "slug": "travel", "category": "lifestyle", "icon": "✈️"},
    {"name": "Food", "slug": "food", "category": "lifestyle", "icon": "🍳"},
    {"name": "Fitness", "slug": "fitness", "category": "lifestyle", "icon": "💪"},
    {"name": "Psychology", "slug": "psychology", "category": "science", "icon": "🧠"},
    {"name": "Environment", "slug": "environment", "category": "science", "icon": "🌱"},
    {"name": "Electric Vehicles", "slug": "electric-vehicles", "category": "technology", "icon": "⚡"},
    {"name": "IoT", "slug": "iot", "category": "technology", "icon": "🔌"},
    {"name": "AR/VR", "slug": "ar-vr", "category": "technology", "icon": "🥽"},
    {"name": "Photography", "slug": "photography", "category": "creative", "icon": "📸"},
    {"name": "Digital Art", "slug": "digital-art", "category": "creative", "icon": "🖼️"},
    {"name": "Podcasting", "slug": "podcasting", "category": "creative", "icon": "🎙️"},
    {"name": "Sports", "slug": "sports", "category": "lifestyle", "icon": "⚽"},
    {"name": "Mental Health", "slug": "mental-health", "category": "lifestyle", "icon": "🧘"},
    {"name": "Public Speaking", "slug": "public-speaking", "category": "lifestyle", "icon": "🗣️"},
    {"name": "Negotiation", "slug": "negotiation", "category": "business", "icon": "🤝"},
    {"name": "Philosophy", "slug": "philosophy", "category": "science", "icon": "🤔"},
    {"name": "Astronomy", "slug": "astronomy", "category": "science", "icon": "🔭"},
    {"name": "Robotics", "slug": "robotics", "category": "technology", "icon": "🦾"},
    {"name": "Quantum Computing", "slug": "quantum-computing", "category": "technology", "icon": "💠"},
    {"name": "Biotech", "slug": "biotech", "category": "science", "icon": "🧫"},
    {"name": "Architecture", "slug": "architecture", "category": "creative", "icon": "🏗️"},
    {"name": "Fashion", "slug": "fashion", "category": "creative", "icon": "👗"},
]


def get_default_tags_by_category() -> dict[str, list[TagSeed]]:
    result: dict[str, list[TagSeed]] = {}
    for tag in DEFAULT_TAGS:
        result.setdefault(tag["category"], []).append(tag)
    return result


def get_tag_count() -> int:
    return len(DEFAULT_TAGS)
