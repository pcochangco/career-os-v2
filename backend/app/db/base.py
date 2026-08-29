from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.db import models as models  # noqa: E402, F401
