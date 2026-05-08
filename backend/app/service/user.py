from __future__ import annotations

from sqlmodel import Session, select

from app.model import Subscription, SubscriptionTier, User
from app.service.base import CRUDRepository


class UserService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = CRUDRepository(User)

    def get_by_id(self, id):
        return self.session.get(self.repo._model, id)

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return self.session.exec(statement).first()

    def create_user(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user


class SubscriptionService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = CRUDRepository(Subscription)

    def get_by_id(self, id):
        return self.session.get(self.repo._model, id)

    def get_user_tier(self, user_id: str) -> SubscriptionTier:
        statement = select(Subscription).where(Subscription.user_id == user_id)
        subscription = self.session.exec(statement).first()
        if subscription is None:
            return SubscriptionTier.FREE
        return subscription.tier

    def set_subscription(self, subscription: Subscription) -> Subscription:
        self.session.add(subscription)
        self.session.commit()
        self.session.refresh(subscription)
        return subscription
