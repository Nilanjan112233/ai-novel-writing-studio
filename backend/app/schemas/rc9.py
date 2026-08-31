from pydantic import BaseModel, Field


class BackupCreateRequest(BaseModel):
    reason: str = Field(default="manual", max_length=120)


class BackupRestoreRequest(BaseModel):
    title: str = Field(default="", max_length=240)
    request_id: str = Field(default="", max_length=120)


class BetaFeedbackRequest(BaseModel):
    category: str = Field(default="general", max_length=60)
    message: str = Field(min_length=3, max_length=5000)
    include_diagnostics: bool = False
    include_story_content: bool = False
