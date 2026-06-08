from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import alle modeller her så Alembic's autogenerate finder dem
from app.modules.calendar import models as _calendar_models  # noqa: F401, E402
from app.modules.calendar import source_models as _source_models  # noqa: F401, E402
from app.modules.calendar import google_session_models as _google_session_models  # noqa: F401, E402
