from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import alle modeller her så Alembic's autogenerate finder dem
from app.modules.calendar import models as _calendar_models  # noqa: F401, E402
