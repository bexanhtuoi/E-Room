from __future__ import annotations

from app.model import Subscription, SubscriptionTier, User
from app.service.base import BaseService


class UserService(BaseService[User]):
    def create_user(self, user: User) -> User:
        return self.save(user)

    def get_current_user(self) -> User | None:
        users = self.list_all()
        if not users:
            return None
        return users[0]

    def complete_profile(self, user_id: str, display_name: str, learning_goal: str | None) -> User | None:
        user = self.get_by_id(user_id)
        if user is None:
            return None
        user.display_name = display_name
        user.learning_goal = learning_goal
        user.profile_completed = True
        return self.save(user)


class SubscriptionService(BaseService[Subscription]):
    def get_user_tier(self, user_id: str) -> SubscriptionTier:
        for subscription in self.list_all():
            if subscription.user_id == user_id:
                return subscription.tier
        return SubscriptionTier.FREE

    def set_subscription(self, subscription: Subscription) -> Subscription:
        return self.save(subscription)
