from sqlalchemy import Column, Integer, String
from database import Base


class CatalogEntry(Base):
    __tablename__ = "catalog_entries"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    image_url = Column(String, nullable=True)

    def __repr__(self):
        return f"<CatalogEntry(id={self.id}, title={self.title})>"
