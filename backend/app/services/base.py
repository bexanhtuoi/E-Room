from app.repositories.base import CRUDRepository, ORMModel

__all__ = ["CRUDRepository", "ORMModel", "ServiceBase"]


class ServiceBase:
    @staticmethod
    def one_or_404(fetcher, error, *args, **kwargs):
        obj = fetcher(*args, **kwargs)

        if obj is None:
            raise error()

        return obj
