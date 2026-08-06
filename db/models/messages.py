from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .. import Base, TimezoneAware


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dialog_id: Mapped[int] = mapped_column(ForeignKey("dialogs.dialog_id"))
    message_id: Mapped[int] = mapped_column()
    author_name: Mapped[str | None] = mapped_column()
    views: Mapped[int | None] = mapped_column(default=1)
    sender_id: Mapped[int] = mapped_column()
    forward_from_username: Mapped[int | None] = mapped_column()
    forward_from_user_id: Mapped[int | None] = mapped_column()
    replied_to_id: Mapped[int | None] = mapped_column()
    replied_to_entity_id: Mapped[int | None] = mapped_column()
    replied_to_text: Mapped[str | None] = mapped_column()
    text: Mapped[str] = mapped_column()
    date: Mapped[datetime] = mapped_column(TimezoneAware())
    edit_date: Mapped[datetime | None] = mapped_column(TimezoneAware())
    file_path: Mapped[str | None] = mapped_column()
    file_name: Mapped[str | None] = mapped_column()
    file_id: Mapped[str | None] = mapped_column()
    file_size: Mapped[float | None] = mapped_column(default=0.0)
    downloaded_file: Mapped[bool | None] = mapped_column(default=False)

    __table_args__ = (
        UniqueConstraint(
            "dialog_id", "message_id", sqlite_on_conflict="IGNORE"
        ),
    )
