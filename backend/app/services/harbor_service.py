from harbor import Harbor
from pathlib import Path
import asyncio
import json
from typing import Dict, Any
from app.models.schemas import ModelType
from app.services.result_parser import parse_harbor_results, read_harbor_logs
from app.config import settings

class HarborService:
    """Native Python service for running Harbor tasks"""
    
    def __init__(self, openrouter_key: str):
        self.openrouter_key = openrouter_key
    
    async def run_task(
        self,
        task_path: Path,
        output_dir: Path,
        run_number: int,
        model: ModelType,
        timeout_multiplier: float = None
    ) -> Dict[str, Any]:
        """Run a single Harbor task execution"""
        
        if timeout_multiplier is None:
            timeout_multiplier = settings.harbor_timeout_multiplier
        
        # Create unique trial name
        import secrets
        trial_suffix = secrets.token_hex(4)
        trial_name = f"run_{run_number}__{trial_suffix}"
        
        # Create Harbor config
        config = {
            "job_name": f"job_run_{run_number}",
            "jobs_dir": str(output_dir),
            "n_attempts": 1,
            "timeout_multiplier": timeout_multiplier,
            "debug": False,
            "orchestrator": {
                "type": "local",
                "n_concurrent_trials": 1,  # One run at a time per worker
                "quiet": False,
                "retry": {
                    "max_retries": 0,
                    "include_exceptions": None,
                    "exclude_exceptions": [
                        "VerifierTimeoutError",
                        "AgentTimeoutError"
                    ],
                    "wait_multiplier": 1.0,
                    "min_wait_sec": 1.0,
                    "max_wait_sec": 60.0
                },
                "kwargs": {}
            },
            "environment": {
                "type": "docker",
                "force_build": False,
                "delete": True,
                "override_cpus": None,
                "override_memory_mb": None,
                "override_storage_mb": None,
                "kwargs": {}
            },
            "verifier": {
                "override_timeout_sec": None,
                "max_timeout_sec": None,
                "disable": False
            },
            "metrics": [],
            "agents": [{
                "name": "openrouter",
                "import_path": None,
                "model_name": model.value,
                "override_timeout_sec": None,
                "max_timeout_sec": None,
                "kwargs": {
                    "api_key": self.openrouter_key
                }
            }],
            "tasks": [{
                "path": str(task_path),
                "source": "uploaded",
                "overwrite": False,
                "download_dir": None
            }]
        }
        
        try:
            # Run Harbor
            harbor = Harbor(config)
            result = await harbor.run()
            
            # Find the result directory (Harbor creates it)
            # Look for the most recent trial directory
            result_path = self._find_result_path(output_dir, trial_name)
            
            if not result_path:
                # Try to find any recent trial directory
                trial_dirs = [d for d in output_dir.iterdir() if d.is_dir() and d.name.startswith("run_")]
                if trial_dirs:
                    result_path = max(trial_dirs, key=lambda p: p.stat().st_mtime)
                else:
                    result_path = output_dir / f"run_{run_number}"
            
            # Parse results
            test_results = parse_harbor_results(result_path)
            logs = read_harbor_logs(result_path)
            
            return {
                "run_number": run_number,
                "result": result,
                "tests_passed": test_results["passed"],
                "tests_total": test_results["total"],
                "tests_failed": test_results["failed"],
                "test_details": test_results.get("details", []),
                "logs": logs,
                "result_path": str(result_path),
                "status": "completed" if test_results["passed"] > 0 else "failed"
            }
            
        except Exception as e:
            # Return error information
            return {
                "run_number": run_number,
                "status": "failed",
                "error": str(e),
                "tests_passed": 0,
                "tests_total": 0,
                "logs": str(e),
                "result_path": None
            }
    
    def _find_result_path(self, output_dir: Path, trial_name: str) -> Path:
        """Find the Harbor result directory for a trial"""
        # Harbor creates directories with pattern: task_name__trial_suffix
        # We need to find the matching directory
        for item in output_dir.iterdir():
            if item.is_dir() and trial_name.split("__")[1] in item.name:
                return item
        return None

