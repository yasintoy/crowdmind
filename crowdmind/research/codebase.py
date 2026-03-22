"""
Codebase Research Agent

Analyzes any codebase to understand:
- Current features and capabilities
- Tech stack and architecture
- What's feasible to add
- Integration points for new features
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Union

from crowdmind.config import get_config


def get_source_files(project_root: Path) -> Dict[str, List[str]]:
    """Get all source files organized by type."""
    files = {
        "python": [],
        "javascript": [],
        "typescript": [],
        "rust": [],
        "go": [],
        "java": [],
        "ruby": [],
        "other": [],
    }
    
    extensions = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".rb": "ruby",
    }
    
    skip_dirs = {
        "node_modules", ".git", "__pycache__", ".venv", "venv",
        "dist", "build", ".next", "target", ".cache"
    }
    
    for root, dirs, filenames in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for filename in filenames:
            filepath = Path(root) / filename
            ext = filepath.suffix.lower()
            
            if ext in extensions:
                files[extensions[ext]].append(str(filepath))
            elif ext in {".md", ".json", ".yaml", ".yml", ".toml"}:
                files["other"].append(str(filepath))
    
    return files


def read_file_content(filepath: str, max_lines: int = 100) -> str:
    """Read file content, truncated for analysis."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()[:max_lines]
            return ''.join(lines)
    except Exception:
        return ""


def extract_exports_and_functions(content: str, language: str = "auto") -> List[str]:
    """Extract exported functions and components from source files."""
    exports = []
    
    for line in content.split('\n'):
        line = line.strip()
        
        # Python
        if line.startswith('def ') and not line.startswith('def _'):
            name = line.split('def ')[1].split('(')[0].strip()
            exports.append(f"function: {name}")
        elif line.startswith('class ') and not line.startswith('class _'):
            name = line.split('class ')[1].split('(')[0].split(':')[0].strip()
            exports.append(f"class: {name}")
        
        # JavaScript/TypeScript
        elif line.startswith('export '):
            if 'function ' in line:
                name = line.split('function ')[1].split('(')[0].strip()
                exports.append(f"function: {name}")
            elif 'const ' in line:
                name = line.split('const ')[1].split('=')[0].split(':')[0].strip()
                exports.append(f"const: {name}")
            elif 'interface ' in line:
                name = line.split('interface ')[1].split('{')[0].split(' ')[0].strip()
                exports.append(f"interface: {name}")
            elif 'type ' in line:
                name = line.split('type ')[1].split('=')[0].strip()
                exports.append(f"type: {name}")
        
        # Rust
        elif line.startswith('pub fn '):
            name = line.split('pub fn ')[1].split('(')[0].strip()
            exports.append(f"function: {name}")
        elif line.startswith('pub struct '):
            name = line.split('pub struct ')[1].split('{')[0].split(' ')[0].strip()
            exports.append(f"struct: {name}")
    
    return exports


def analyze_file(filepath: str) -> Dict:
    """Analyze a source file."""
    content = read_file_content(filepath, max_lines=200)
    name = Path(filepath).stem
    ext = Path(filepath).suffix
    
    return {
        "name": name,
        "path": filepath,
        "extension": ext,
        "lines": len(content.split('\n')),
        "exports": extract_exports_and_functions(content),
    }


def detect_tech_stack(files: Dict[str, List[str]], project_root: Path) -> Dict:
    """Detect the technology stack from file patterns."""
    tech = {
        "languages": [],
        "frameworks": [],
        "build_tools": [],
        "databases": [],
    }
    
    # Detect languages
    for lang, file_list in files.items():
        if file_list and lang != "other":
            tech["languages"].append(lang)
    
    # Check for frameworks
    root_files = list(project_root.glob("*"))
    root_names = [f.name for f in root_files]
    
    # Python frameworks
    if "requirements.txt" in root_names or "pyproject.toml" in root_names:
        req_content = ""
        if (project_root / "requirements.txt").exists():
            req_content = (project_root / "requirements.txt").read_text()
        elif (project_root / "pyproject.toml").exists():
            req_content = (project_root / "pyproject.toml").read_text()
        
        if "fastapi" in req_content.lower():
            tech["frameworks"].append("FastAPI")
        if "django" in req_content.lower():
            tech["frameworks"].append("Django")
        if "flask" in req_content.lower():
            tech["frameworks"].append("Flask")
    
    # JS/TS frameworks
    if "package.json" in root_names:
        try:
            pkg = json.loads((project_root / "package.json").read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            
            if "react" in deps:
                tech["frameworks"].append("React")
            if "vue" in deps:
                tech["frameworks"].append("Vue")
            if "next" in deps:
                tech["frameworks"].append("Next.js")
            if "express" in deps:
                tech["frameworks"].append("Express")
        except Exception:
            pass
    
    # Rust
    if "Cargo.toml" in root_names:
        tech["build_tools"].append("Cargo")
        if (project_root / "src-tauri").exists():
            tech["frameworks"].append("Tauri")
    
    # Go
    if "go.mod" in root_names:
        tech["build_tools"].append("Go Modules")
    
    return tech


def call_llm_for_analysis(codebase_summary: Dict) -> Dict:
    """Use LLM to generate deeper analysis."""
    
    summary_text = json.dumps(codebase_summary, indent=2)[:8000]
    
    prompt = f"""Analyze this codebase summary and provide structured insights.

CODEBASE SUMMARY:
{summary_text}

Provide a structured analysis:

1. CURRENT FEATURES (list what the project can do based on the code)
2. TECH STACK (specific technologies and their roles)
3. ARCHITECTURE (how components interact)
4. EXTENSION POINTS (where new features could be added)
5. LIMITATIONS (what might be hard to add)

Output as JSON:
```json
{{
  "features": ["feature1", "feature2", ...],
  "tech_stack": {{"frontend": "...", "backend": "...", "key_libs": [...]}},
  "architecture": "brief description",
  "extension_points": ["point1", "point2", ...],
  "limitations": ["limitation1", ...]
}}
```"""

    try:
        result = subprocess.run(
            ["claude", "--print", prompt],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            response = result.stdout
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
    except Exception as e:
        print(f"LLM analysis failed: {e}")
    
    return {}


def run_analysis(
    project_path: Union[str, Path],
    use_cache: bool = True,
    verbose: bool = True
) -> Dict:
    """Run full codebase analysis on any project."""
    
    project_root = Path(project_path).resolve()
    
    if not project_root.exists():
        return {"error": f"Path does not exist: {project_root}"}
    
    config = get_config()
    cache_file = config.cache_dir / f"codebase_{project_root.name}.json"
    
    # Check cache
    if use_cache and cache_file.exists():
        try:
            with open(cache_file) as f:
                cached = json.load(f)
                if verbose:
                    print("Using cached codebase analysis")
                return cached
        except Exception:
            pass
    
    if verbose:
        print(f"Analyzing codebase: {project_root}...")
    
    files = get_source_files(project_root)
    tech_stack = detect_tech_stack(files, project_root)
    
    analysis = {
        "project_root": str(project_root),
        "source_files": {k: len(v) for k, v in files.items()},
        "tech_stack": tech_stack,
        "modules": [],
    }
    
    # Analyze key files
    total_files = sum(len(v) for v in files.values())
    if verbose:
        print(f"  Found {total_files} source files")
    
    # Analyze up to 50 files
    all_files = []
    for file_list in files.values():
        all_files.extend(file_list)
    
    for filepath in all_files[:50]:
        analysis["modules"].append(analyze_file(filepath))
    
    # Use LLM for deeper analysis
    if verbose:
        print("  Running LLM analysis...")
    llm_analysis = call_llm_for_analysis(analysis)
    analysis["llm_analysis"] = llm_analysis
    
    # Cache results
    config.cache_dir.mkdir(parents=True, exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    if verbose:
        print(f"\nCodebase Analysis Complete!")
        print(f"  Languages: {', '.join(tech_stack['languages'])}")
        print(f"  Frameworks: {', '.join(tech_stack['frameworks']) or 'None detected'}")
        print(f"  Total files: {total_files}")
        
        if llm_analysis.get('features'):
            print(f"\nDetected Features:")
            for f in llm_analysis['features'][:10]:
                print(f"  - {f}")
    
    return analysis


def get_capabilities_summary(project_path: Union[str, Path]) -> str:
    """Get a text summary of project capabilities for use in prompts."""
    
    analysis = run_analysis(project_path, use_cache=True, verbose=False)
    llm = analysis.get('llm_analysis', {})
    tech = analysis.get('tech_stack', {})
    
    features = llm.get('features', [])
    extensions = llm.get('extension_points', [])
    
    summary = f"""## Project Capabilities

**Tech Stack:**
- Languages: {', '.join(tech.get('languages', []))}
- Frameworks: {', '.join(tech.get('frameworks', [])) or 'None detected'}
- Build Tools: {', '.join(tech.get('build_tools', [])) or 'None detected'}

**Current Features:**
{chr(10).join(f'- {f}' for f in features[:15])}

**Extension Points (where new features can be added):**
{chr(10).join(f'- {e}' for e in extensions[:10])}

**Source Files:** {sum(analysis.get('source_files', {}).values())}
"""
    return summary


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze any codebase")
    parser.add_argument("path", help="Path to project")
    parser.add_argument("--no-cache", action="store_true", help="Skip cache")
    parser.add_argument("--summary", action="store_true", help="Print capabilities summary")
    args = parser.parse_args()
    
    if args.summary:
        print(get_capabilities_summary(args.path))
    else:
        analysis = run_analysis(args.path, use_cache=not args.no_cache)
        config = get_config()
        cache_file = config.cache_dir / f"codebase_{Path(args.path).name}.json"
        print(f"\nFull analysis saved to: {cache_file}")
