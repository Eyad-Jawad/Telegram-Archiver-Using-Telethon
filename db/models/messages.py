from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .. import Base, TimezoneAware


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dialog_id: Mapped[int] = mapped_column(ForeignKey("dialogs.dialog_id"))
    message_id: Mapped[int] = mapped_column()
    author_name: Mapped[str | None] = mapped_column(default="")
    views: Mapped[int | None] = mapped_column(default=1)
    sender_id: Mapped[int] = mapped_column(default=0)
    forward_from_username: Mapped[int] = mapped_column(default="")
    forward_from_user_id: Mapped[int] = mapped_column(default=0)
    replied_to_id: Mapped[int] = mapped_column(default=0)
    replied_to_entity_id: Mapped[int] = mapped_column(default=0)
    replied_to_text: Mapped[str] = mapped_column(default="")
    text: Mapped[str] = mapped_column(default="")
    date: Mapped[datetime] = mapped_column(TimezoneAware())
    edit_date: Mapped[datetime | None] = mapped_column(TimezoneAware())
    file_path: Mapped[str] = mapped_column(default="")
    file_name: Mapped[str] = mapped_column(default="")
    file_id: Mapped[str] = mapped_column(default="")
    file_size: Mapped[float] = mapped_column(default=0.0)
    downloaded_file: Mapped[bool] = mapped_column(default=False)

    __table_args__ = (
        UniqueConstraint(
            "dialog_id", "message_id", sqlite_on_conflict="IGNORE"
        ),
    )
