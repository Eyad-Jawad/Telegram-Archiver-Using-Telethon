from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .. import Base, TimezoneAware


class Reaction(Base):
    __tablename__ = "reactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dialog_id: Mapped[int] = mapped_column(ForeignKey("dialogs.dialog_id"))
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.message_id"))
    reactors_id: Mapped[int | None] = mapped_column()
    reacting_date: Mapped[datetime | None] = mapped_column(TimezoneAware())
    reaction: Mapped[str] = mapped_column()
    count: Mapped[int | None] = mapped_column(default=1)