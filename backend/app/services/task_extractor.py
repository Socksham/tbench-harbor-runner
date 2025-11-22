import zipfile
import tempfile
from pathlib import Path
from typing import Optional
import yaml
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
    
    # Check if root contains task.yaml (Harbor format)
    if (extract_dir / "task.yaml").exists():
        task_path = extract_dir
    else:
        # Look for subdirectories with task.yaml
        for subdir in extract_dir.iterdir():
            if subdir.is_dir() and (subdir / "task.yaml").exists():
                task_path = subdir
                break
    
    if not task_path:
        raise ValueError("Invalid task structure: task.yaml not found")
    
    # Validate task.yaml structure
    task_yaml_path = task_path / "task.yaml"
    with open(task_yaml_path) as f:
        task_config = yaml.safe_load(f)
    
    # Basic validation
    if not isinstance(task_config, dict):
        raise ValueError("Invalid task.yaml: must be a dictionary")
    
    if harness == HarnessType.HARBOR:
        # Harbor-specific validation
        if "name" not in task_config:
            raise ValueError("Invalid Harbor task: missing 'name' field")
    elif harness == HarnessType.TERMINUS:
        # Terminus-specific validation (to be implemented)
        pass
    
    return task_path

def extract_task_name(task_path: Path) -> str:
    """Extract task name from task.yaml or directory name"""
    task_yaml_path = task_path / "task.yaml"
    
    if task_yaml_path.exists():
        with open(task_yaml_path) as f:
            task_config = yaml.safe_load(f)
            if "name" in task_config:
                return task_config["name"]
    
    # Fallback to directory name
    return task_path.name

