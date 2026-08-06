from sqlalchemy import UniqueConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .. import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dialog_id: Mapped[int] = mapped_column(ForeignKey("dialogs.dialog_id"))
    user_id: Mapped[int] = mapped_column()

    __table_args__ = (
        UniqueConstraint("dialog_id", "user_id", sqlite_on_conflict="IGNORE"),
    )
