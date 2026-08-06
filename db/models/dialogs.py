from sqlalchemy.orm import Mapped, mapped_column
from .. import Base


class Dialog(Base):
    __tablename__ = "dialogs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dialog_id: Mapped[int] = mapped_column(unique=True, sqlite_on_conflict_unique="IGNORE")
    name: Mapped[str | None] = mapped_column()
    type: Mapped[str] = mapped_column()
    total_number_of_messages: Mapped[int] = mapped_column(default=0)
    last_message_id: Mapped[int] = mapped_column(nullable=False, default=1)
    message_counter: Mapped[int] = mapped_column(nullable=False, default=0)
    archiving_time: Mapped[float] = mapped_column(nullable=False, default=0.0)