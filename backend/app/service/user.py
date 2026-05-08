from __future__ import annotations

from sqlmodel import Session, select

from app.model import Subscription, SubscriptionTier, User
from app.service.base import BaseService


class UserService(BaseService[User]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, User)

    def create_user(self, user: User) -> User:
        return self.save(user)

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return self.session.exec(statement).first()


class SubscriptionService(BaseService[Subscription]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Subscription)

    def get_user_tier(self, user_id: str) -> SubscriptionTier:
        statement = select(Subscription).where(Subscription.user_id == user_id)
        subscription = self.session.exec(statement).first()
        if subscription is None:
            return SubscriptionTier.FREE
        return subscription.tier

    def set_subscription(self, subscription: Subscription) -> Subscription:
        return self.save(subscription)
