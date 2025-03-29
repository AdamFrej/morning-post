"""Pydantic models for configuration management."""
from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, HttpUrl, Field, validator
import os


class RSSFeedConfig(BaseModel):
    """Configuration for a single RSS feed."""
    name: str
    url: HttpUrl  # Validates URLs automatically
    max_articles: int = Field(gt=0, le=20)  # Ensures reasonable limits

    class Config:
        """Pydantic config options."""
        extra = "forbid"  # Prevent unexpected fields


class HackerNewsAPIEndpoints(BaseModel):
    """Configuration for HackerNews API endpoints."""
    top_stories: HttpUrl
    item: str  # Contains format placeholders
    discussion_url: str  # Contains format placeholders

    @validator("item", "discussion_url")
    def validate_format_string(cls, v):
        """Ensure strings contain format placeholders for IDs."""
        if "{}" not in v:
            raise ValueError("Must contain '{}' for ID placeholder")
        return v


class HackerNewsConfig(BaseModel):
    """Configuration for Hacker News integration."""
    include: bool = True
    max_articles: int = Field(gt=0, le=20)
    only_self_posts: bool = True
    api_endpoints: HackerNewsAPIEndpoints


class TemplatesConfig(BaseModel):
    """Configuration for HTML templates."""
    directory: str = "./templates"
    main_template: str = "paper_template.html"
    article_template: str = "article_template.html"

    @validator("directory")
    def directory_exists(cls, v):
        """Create directory if it doesn't exist."""
        os.makedirs(v, exist_ok=True)
        return v


class TimeoutConfig(BaseModel):
    """Configuration for various timeout settings."""
    request: int = Field(ge=1, le=60)  # 1-60 seconds
    extraction: int = Field(ge=1, le=120)  # 1-120 seconds


class AppConfig(BaseModel):
    """Main application configuration."""
    rss_feeds: List[RSSFeedConfig]
    hacker_news: HackerNewsConfig
    output_directory: str = "./papers"
    templates: TemplatesConfig = TemplatesConfig()
    extract_full_content: bool = True
    include_images: bool = False
    timeout: TimeoutConfig = TimeoutConfig(request=10, extraction=15)
    max_content_length: int = Field(ge=1000, le=500000, default=50000)
    newspaper_title: str = "Morning Paper"
    columns: int = Field(ge=1, le=3, default=1)
    site_specific_selectors: Dict[str, str] = {}
    fallback_selectors: List[str] = []
    elements_to_remove: List[str] = []
    class_selectors_to_remove: List[str] = []

    @validator("output_directory")
    def create_output_directory(cls, v):
        """Create output directory if it doesn't exist."""
        os.makedirs(v, exist_ok=True)
        return v

    class Config:
        """Pydantic config options."""
        extra = "ignore"  # Allow extra fields for backward compatibility
