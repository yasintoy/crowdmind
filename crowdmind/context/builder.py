from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path
import json


@dataclass
class ProductContext:
    name: str = "Unknown Product"
    description: str = ""
    target_users: List[str] = field(default_factory=list)
    existing_features: List[str] = field(default_factory=list)
    tech_stack: List[str] = field(default_factory=list)
    architecture: str = ""
    extension_points: List[str] = field(default_factory=list)
    business_model: str = "unknown"  # b2b, b2c, opensource
    stage: str = "unknown"  # idea, mvp, growth, mature
    source_files_count: int = 0

    def to_prompt(self) -> str:
        """Convert to prompt context for EDSL"""
        features_str = '\n'.join(f'  - {f}' for f in self.existing_features[:15]) if self.existing_features else '  None detected'
        
        return f"""
Product: {self.name}
Description: {self.description[:500] if self.description else 'Not specified'}

Tech Stack: {', '.join(self.tech_stack) if self.tech_stack else 'Unknown'}
Source Files: {self.source_files_count}

EXISTING FEATURES (from codebase analysis):
{features_str}

Architecture: {self.architecture or 'Not analyzed'}
Business Model: {self.business_model}
"""


def build_context(
    path: Optional[Path] = None,
    description: Optional[str] = None,
    name: Optional[str] = None,
    analyze_code: bool = True,
    verbose: bool = False,
) -> ProductContext:
    """
    Build product context from path or description.
    
    If analyze_code=True (default), performs deep codebase analysis:
    - Scans all source files
    - Extracts functions, classes, exports
    - Uses LLM to detect features and architecture
    """

    context = ProductContext()

    if name:
        context.name = name

    if description:
        context.description = description

    if path:
        path = Path(path)

        # Read README.md for basic info
        readme_path = path / "README.md" if path.is_dir() else path
        if readme_path.exists() and readme_path.suffix == ".md":
            readme = readme_path.read_text()
            for line in readme.split("\n"):
                if line.startswith("# "):
                    context.name = line[2:].strip()
                    break
            if not context.description:
                context.description = readme[:1000]

        if path.is_dir():
            # Quick tech stack detection from config files
            _detect_tech_from_configs(path, context)
            
            # Deep codebase analysis
            if analyze_code:
                _analyze_codebase(path, context, verbose=verbose)

    # Detect business model from description
    context.business_model = detect_business_model(context)

    return context


def _detect_tech_from_configs(path: Path, context: ProductContext):
    """Quick detection from package.json, pyproject.toml, etc."""
    
    # package.json (Node.js)
    pkg_json = path / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            if not context.name or context.name == "Unknown Product":
                context.name = pkg.get("name", context.name)
            if not context.description:
                context.description = pkg.get("description", "")
            deps = list(pkg.get("dependencies", {}).keys())
            if "react" in deps:
                context.tech_stack.append("React")
            if "vue" in deps:
                context.tech_stack.append("Vue")
            if "next" in deps:
                context.tech_stack.append("Next.js")
            if "express" in deps:
                context.tech_stack.append("Express/Node.js")
            if "@tauri-apps/api" in deps:
                context.tech_stack.append("Tauri")
        except:
            pass

    # pyproject.toml (Python)
    pyproject = path / "pyproject.toml"
    if pyproject.exists():
        context.tech_stack.append("Python")
        try:
            content = pyproject.read_text()
            if "fastapi" in content.lower():
                context.tech_stack.append("FastAPI")
            if "django" in content.lower():
                context.tech_stack.append("Django")
            if "flask" in content.lower():
                context.tech_stack.append("Flask")
            if "typer" in content.lower():
                context.tech_stack.append("Typer CLI")
        except:
            pass

    # Cargo.toml (Rust)
    cargo = path / "Cargo.toml"
    if cargo.exists():
        context.tech_stack.append("Rust")
        if (path / "src-tauri").exists():
            context.tech_stack.append("Tauri")

    # go.mod (Go)
    if (path / "go.mod").exists():
        context.tech_stack.append("Go")


def _analyze_codebase(path: Path, context: ProductContext, verbose: bool = False):
    """
    Deep codebase analysis - scans actual source files.
    Uses crowdmind.research.codebase module.
    """
    try:
        from crowdmind.research.codebase import run_analysis, get_capabilities_summary
        
        if verbose:
            print(f"Analyzing codebase at {path}...")
        
        # Run full analysis (uses cache)
        analysis = run_analysis(path, use_cache=True, verbose=verbose)
        
        # Extract features from LLM analysis
        llm_analysis = analysis.get("llm_analysis", {})
        
        if llm_analysis.get("features"):
            context.existing_features = llm_analysis["features"]
        
        if llm_analysis.get("architecture"):
            context.architecture = llm_analysis["architecture"]
        
        if llm_analysis.get("extension_points"):
            context.extension_points = llm_analysis["extension_points"]
        
        # Add detected tech stack
        tech = analysis.get("tech_stack", {})
        for lang in tech.get("languages", []):
            if lang not in context.tech_stack:
                context.tech_stack.append(lang)
        for framework in tech.get("frameworks", []):
            if framework not in context.tech_stack:
                context.tech_stack.append(framework)
        
        # File count
        context.source_files_count = sum(analysis.get("source_files", {}).values())
        
        if verbose:
            print(f"  Found {context.source_files_count} source files")
            print(f"  Detected {len(context.existing_features)} features")
            
    except ImportError:
        if verbose:
            print("Warning: codebase analysis module not available")
    except Exception as e:
        if verbose:
            print(f"Warning: codebase analysis failed: {e}")


def detect_business_model(context: ProductContext) -> str:
    """Detect business model from context clues"""
    desc_lower = (context.description or "").lower()

    if "open source" in desc_lower or "mit license" in desc_lower:
        return "opensource"
    if "enterprise" in desc_lower or "team" in desc_lower:
        return "b2b"
    if "consumer" in desc_lower or "personal" in desc_lower:
        return "b2c"
    return "unknown"
