from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from .. import Base, TimezoneAware

class DialogPhoto(Base):
    __tablename__ = "dialog_photos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dialog_id: Mapped[int] = mapped_column(ForeignKey("dialogs.dialog_id"))
    photo_id: Mapped[int] = mapped_column()
    photo_path: Mapped[str] = mapped_column()
    photo_date: Mapped[datetime] = mapped_column(TimezoneAware())
