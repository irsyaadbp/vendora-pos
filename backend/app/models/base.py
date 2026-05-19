"""SQLAlchemy declarative Base class for all models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models.

    All models should inherit from this class to share
    the same metadata and registry.
    """

    pass
