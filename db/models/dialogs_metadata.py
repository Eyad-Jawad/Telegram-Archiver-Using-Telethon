from datetime import UTC, datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .. import Base, TimezoneAware


class DialogMetadata(Base):
    __tablename__ = "dialogs_metadata"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dialog_id: Mapped[int] = mapped_column(ForeignKey("dialogs.dialog_id"))
    full_request: Mapped[str] = mapped_column()
    date_of_request: Mapped[datetime] = mapped_column(TimezoneAware(), default=lambda: datetime.now(tz=UTC))