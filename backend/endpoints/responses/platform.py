from typing import Optional

from pydantic import BaseModel


class PlatformSchema(BaseModel):
    id: int
    slug: str
    fs_slug: str
    igdb_id: Optional[int] = None
    sgdb_id: Optional[int] = None
    moby_id: Optional[int] = None
    name: str
    logo_path: Optional[str] = ""
    rom_count: int

    class Config:
        from_attributes = True
