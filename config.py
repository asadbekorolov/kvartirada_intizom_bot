import os
import json
from typing import List, Union
import pytz
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
    GROUP_CHAT_ID: int = -1001234567890
    ADMIN_USER_IDS: Union[List[int], str] = [12345678]
    BOT_TZ: str = "Asia/Tashkent"
    TIMEZONE: str = "Asia/Tashkent"
    DB_PATH: str = "kvartira.db"
    PORT: int = 8080



    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("ADMIN_USER_IDS", mode="before")
    @classmethod
    def parse_admin_user_ids(cls, v):
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return []
            if v_str.startswith("[") and v_str.endswith("]"):
                try:
                    return [int(x) for x in json.loads(v_str)]
                except Exception:
                    pass
            return [int(uid.strip()) for uid in v_str.split(",") if uid.strip()]
        if isinstance(v, int):
            return [v]
        return v

    @property
    def admin_user_ids_list(self) -> List[int]:
        if isinstance(self.ADMIN_USER_IDS, list):
            return [int(x) for x in self.ADMIN_USER_IDS]
        return self.parse_admin_user_ids(self.ADMIN_USER_IDS)

    @property
    def timezone(self):
        tz_str = self.TIMEZONE if self.TIMEZONE else self.BOT_TZ
        return pytz.timezone(tz_str)



settings = Settings()

