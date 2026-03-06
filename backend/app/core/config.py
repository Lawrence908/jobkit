"""Pydantic Settings loaded from environment."""
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_env: str = Field(default="prod", alias="APP_ENV")
    app_url: str = Field(default="https://jobs.chrislawrence.ca", alias="APP_URL")
    session_secret: str = Field(default="change_me_long_random", alias="SESSION_SECRET")
    admin_username: str = Field(default="chris", alias="ADMIN_USERNAME")
    admin_password: str = Field(default="change_me_strong", alias="ADMIN_PASSWORD")
    cors_extra_origins: str = Field(default="", alias="CORS_EXTRA_ORIGINS")  # comma-separated, e.g. http://100.x.x.x:8123

    # Storage paths (env can be string; Pydantic coerces to Path)
    jobkit_data_dir: Path = Field(default=Path("/app/data"), alias="JOBKIT_DATA_DIR")
    jobkit_jobs_dir: Path = Field(default=Path("/app/jobs"), alias="JOBKIT_JOBS_DIR")
    jobkit_outputs_dir: Path = Field(default=Path("/app/outputs"), alias="JOBKIT_OUTPUTS_DIR")

    # LLM provider (OpenAI-compatible)
    llm_base_url: str = Field(default="https://api.openai.com/v1", alias="LLM_BASE_URL")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_model: str = Field(default="gpt-4.1-mini", alias="LLM_MODEL")
    llm_temperature: float = Field(default=0.2, alias="LLM_TEMPERATURE")

    # Google OAuth
    google_oauth_client_id: str = Field(default="", alias="GOOGLE_OAUTH_CLIENT_ID")
    google_oauth_client_secret: str = Field(default="", alias="GOOGLE_OAUTH_CLIENT_SECRET")
    google_oauth_redirect_uri: str = Field(
        default="https://jobs.chrislawrence.ca/api/google/oauth/callback",
        alias="GOOGLE_OAUTH_REDIRECT_URI",
    )
    google_token_encryption_key: str = Field(
        default="change_me_32bytes_base64", alias="GOOGLE_TOKEN_ENCRYPTION_KEY"
    )

    # Drive/Sheets
    google_drive_root_folder_id: str | None = Field(
        default=None, alias="GOOGLE_DRIVE_ROOT_FOLDER_ID"
    )
    google_sheets_spreadsheet_id: str = Field(default="", alias="GOOGLE_SHEETS_SPREADSHEET_ID")
    google_sheets_tab_name: str = Field(default="Job Applications", alias="GOOGLE_SHEETS_TAB_NAME")
    google_sheets_url_column: str = Field(default="Job URL", alias="GOOGLE_SHEETS_URL_COLUMN")
    # Optional: map JobKit fields to your sheet column headers (case-insensitive match). Unset = use default order.
    google_sheets_column_company: str = Field(default="", alias="GOOGLE_SHEETS_COLUMN_COMPANY")
    google_sheets_column_role: str = Field(default="", alias="GOOGLE_SHEETS_COLUMN_ROLE")
    google_sheets_column_status: str = Field(default="", alias="GOOGLE_SHEETS_COLUMN_STATUS")
    google_sheets_column_job_url: str = Field(default="", alias="GOOGLE_SHEETS_COLUMN_JOB_URL")
    google_sheets_column_link_to_job_req: str = Field(default="", alias="GOOGLE_SHEETS_COLUMN_LINK_TO_JOB_REQ")
    google_sheets_column_date_submitted: str = Field(default="", alias="GOOGLE_SHEETS_COLUMN_DATE_SUBMITTED")
    google_sheets_column_resume_link: str = Field(default="", alias="GOOGLE_SHEETS_COLUMN_RESUME_LINK")
    google_sheets_column_cover_link: str = Field(default="", alias="GOOGLE_SHEETS_COLUMN_COVER_LINK")
    google_sheets_column_notes_link: str = Field(default="", alias="GOOGLE_SHEETS_COLUMN_NOTES_LINK")

    @field_validator("jobkit_data_dir", "jobkit_jobs_dir", "jobkit_outputs_dir", mode="before")
    @classmethod
    def coerce_path(cls, v):
        if isinstance(v, str):
            return Path(v)
        return v

    @property
    def db_path(self) -> Path:
        return self.jobkit_data_dir / "jobkit.db"

    def ensure_dirs(self) -> None:
        self.jobkit_data_dir.mkdir(parents=True, exist_ok=True)
        self.jobkit_jobs_dir.mkdir(parents=True, exist_ok=True)
        self.jobkit_outputs_dir.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    return Settings()
