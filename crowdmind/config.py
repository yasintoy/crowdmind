"""
CrowdMind Configuration

Loads configuration from:
1. ~/.crowdmind/config.yaml
2. Environment variables
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


CONFIG_DIR = Path.home() / ".crowdmind"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


@dataclass
class CrowdMindConfig:
    """Configuration for CrowdMind."""
    
    # API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    github_token: Optional[str] = None
    
    # Default settings
    default_model: str = "claude-sonnet-4-6"
    default_personas: int = 10
    default_provider: str = "anthropic"
    
    # Cache settings
    cache_dir: Path = field(default_factory=lambda: CONFIG_DIR / "cache")
    cache_hours: int = 12
    
    # Output settings
    output_dir: Path = field(default_factory=lambda: Path.cwd() / "crowdmind_output")
    
    # Research settings
    reddit_subreddits: list = field(default_factory=lambda: [
        "programming", "webdev", "devops", "startups", "SaaS"
    ])
    
    @classmethod
    def load(cls) -> "CrowdMindConfig":
        """Load configuration from file and environment variables."""
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass

        config = cls()
        
        # Load from YAML if available
        if HAS_YAML and CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    yaml_config = yaml.safe_load(f) or {}
                config = cls._from_dict(yaml_config)
            except Exception:
                pass
        
        # Override with environment variables
        config.openai_api_key = os.getenv("OPENAI_API_KEY", config.openai_api_key)
        config.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", config.anthropic_api_key)
        config.google_api_key = os.getenv("GOOGLE_API_KEY", config.google_api_key)
        config.groq_api_key = os.getenv("GROQ_API_KEY", config.groq_api_key)
        config.github_token = os.getenv("GITHUB_TOKEN", config.github_token)
        
        # CrowdMind-specific env vars
        if os.getenv("CROWDMIND_MODEL"):
            config.default_model = os.getenv("CROWDMIND_MODEL")
        if os.getenv("CROWDMIND_PERSONAS"):
            try:
                config.default_personas = int(os.getenv("CROWDMIND_PERSONAS"))
            except ValueError:
                pass
        if os.getenv("CROWDMIND_PROVIDER"):
            config.default_provider = os.getenv("CROWDMIND_PROVIDER")
        
        return config
    
    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> "CrowdMindConfig":
        """Create config from dictionary."""
        config = cls()
        
        # API keys
        api_keys = data.get("api_keys", {})
        config.openai_api_key = api_keys.get("openai")
        config.anthropic_api_key = api_keys.get("anthropic")
        config.google_api_key = api_keys.get("google")
        config.groq_api_key = api_keys.get("groq")
        config.github_token = api_keys.get("github")
        
        # Defaults
        defaults = data.get("defaults", {})
        config.default_model = defaults.get("model", config.default_model)
        config.default_personas = defaults.get("personas", config.default_personas)
        config.default_provider = defaults.get("provider", config.default_provider)
        
        # Cache
        cache = data.get("cache", {})
        if cache.get("dir"):
            config.cache_dir = Path(cache["dir"]).expanduser()
        config.cache_hours = cache.get("hours", config.cache_hours)
        
        # Output
        if data.get("output_dir"):
            config.output_dir = Path(data["output_dir"]).expanduser()
        
        # Research
        research = data.get("research", {})
        if research.get("subreddits"):
            config.reddit_subreddits = research["subreddits"]
        
        return config
    
    def save(self) -> None:
        """Save configuration to YAML file."""
        if not HAS_YAML:
            raise ImportError("PyYAML is required to save config. Install with: pip install pyyaml")
        
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        data = {
            "api_keys": {
                "openai": self.openai_api_key,
                "anthropic": self.anthropic_api_key,
                "google": self.google_api_key,
                "groq": self.groq_api_key,
                "github": self.github_token,
            },
            "defaults": {
                "model": self.default_model,
                "personas": self.default_personas,
                "provider": self.default_provider,
            },
            "cache": {
                "dir": str(self.cache_dir),
                "hours": self.cache_hours,
            },
            "output_dir": str(self.output_dir),
            "research": {
                "subreddits": self.reddit_subreddits,
            },
        }
        
        with open(CONFIG_FILE, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
    
    def ensure_dirs(self) -> None:
        """Ensure required directories exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


def get_config() -> CrowdMindConfig:
    """Get the current configuration."""
    return CrowdMindConfig.load()


def get_api_key(provider: str) -> Optional[str]:
    """Get API key for a provider."""
    config = get_config()
    key_map = {
        "openai": config.openai_api_key,
        "anthropic": config.anthropic_api_key,
        "google": config.google_api_key,
        "groq": config.groq_api_key,
        "github": config.github_token,
    }
    return key_map.get(provider.lower())
