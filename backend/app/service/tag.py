from __future__ import annotations

from app.model import Tag, UserTag
from app.service.base import BaseService


class TagService(BaseService[Tag]):
    def search_tags(self, query: str, limit: int = 10) -> list[Tag]:
        normalized_query = query.lower().strip()
        return [tag for tag in self.list_all() if normalized_query in tag.name.lower()][:limit]

    def get_popular_tags(self, limit: int = 10) -> list[Tag]:
        return sorted(self.list_all(), key=lambda tag: tag.usage_count, reverse=True)[:limit]


class UserTagService(BaseService[UserTag]):
    def list_user_tags(self, user_id: str) -> list[UserTag]:
        return [user_tag for user_tag in self.list_all() if user_tag.user_id == user_id]

    def attach_tag(self, user_tag: UserTag) -> UserTag:
        return self.save(user_tag)
