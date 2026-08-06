from sqlalchemy import UniqueConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .. import Base

class StickerSet(Base):
    __tablename__ = "sticker_sets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dialog_id: Mapped[int] = mapped_column(ForeignKey("dialogs.dialog_id"))
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.message_id"))
    pack_name: Mapped[str] = mapped_column(nullable=False, default="")
    pack_link: Mapped[str] = mapped_column(nullable=False, default="")
    sticker_set_id: Mapped[int] = mapped_column(nullable=False, default=0)
    access_hash: Mapped[int] = mapped_column(nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("dialog_id", "message_id", sqlite_on_conflict="IGNORE"),
    )
