from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings


def get_app_settings(request: Request) -> Settings:
    # The instance the app was built with (tests pass their own), not the global get_settings().
    settings: Settings = request.app.state.settings
    return settings


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
