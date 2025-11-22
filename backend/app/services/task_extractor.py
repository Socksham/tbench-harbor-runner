import zipfile
import tempfile
from pathlib import Path
from typing import Optional
import toml
import shutil
from app.models.schemas import HarnessType

async def extract_and_validate_task(
    zip_path: Path,
    extract_dir: Path,
    harness: HarnessType
) -> Path:
    """Extract zip file and validate it's a valid Terminal-Bench task"""
    
    # Extract zip
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    # Find task directory (could be root or nested)
    task_path = None
    
    # Check if root contains task.toml (Terminal-Bench 2 format)
    if (extract_dir / "task.toml").exists():
        task_path = extract_dir
    else:
        # Look for subdirectories with task.toml
        for subdir in extract_dir.iterdir():
            if subdir.is_dir() and (subdir / "task.toml").exists():
                task_path = subdir
                break
    
    if not task_path:
        raise ValueError("Invalid task structure: task.toml not found")
    
    # Validate task.toml structure
    task_toml_path = task_path / "task.toml"
    with open(task_toml_path, 'r', encoding='utf-8') as f:
        task_config = toml.load(f)
    
    # Basic validation
    if not isinstance(task_config, dict):
        raise ValueError("Invalid task.toml: must be a dictionary")
    
    if harness == HarnessType.HARBOR:
        # Harbor/Terminal-Bench 2 validation
        # Terminal-Bench 2 tasks have task.toml with metadata
        pass  # Basic structure check is enough
    elif harness == HarnessType.TERMINUS:
        # Terminus-specific validation (to be implemented)
        pass
    
    return task_path

def extract_task_name(task_path: Path) -> str:
    """Extract task name from task.toml or directory name"""
    task_toml_path = task_path / "task.toml"
    
    if task_toml_path.exists():
        try:
            with open(task_toml_path, 'r', encoding='utf-8') as f:
                task_config = toml.load(f)
                # Terminal-Bench 2 task.toml might have name in different places
                if "name" in task_config:
                    return task_config["name"]
                elif "task" in task_config and isinstance(task_config["task"], dict):
                    if "name" in task_config["task"]:
                        return task_config["task"]["name"]
        except Exception:
            # If parsing fails, fall back to directory name
            pass
    
    # Fallback to directory name
    return task_path.name

