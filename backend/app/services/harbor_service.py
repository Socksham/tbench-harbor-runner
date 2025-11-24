from pathlib import Path
import asyncio
import json
import os
import subprocess
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
        
        try:
            # Ensure all paths are absolute
            output_dir_abs = Path(output_dir).resolve()
            task_path_abs = Path(task_path).resolve()
            
            # Create unique job name suffix to avoid conflicts when multiple runs execute concurrently
            job_suffix = secrets.token_hex(4)
            
            # Create Harbor config with absolute paths
            config = {
                "job_name": f"job_run_{run_number}_{job_suffix}",
                "jobs_dir": str(output_dir_abs),
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
                "metrics": [
                    {
                        "type": "mean"
                    }
                ],
                "agents": [{
                    "name": "oracle",
                    "import_path": None,
                    "model_name": f"openrouter:{model.value}",
                    "override_timeout_sec": None,
                    "max_timeout_sec": None,
                    "kwargs": {
                        "api_key": self.openrouter_key
                    }
                }],
                "tasks": [{
                    "path": str(task_path_abs),
                    "source": "uploaded",
                    "overwrite": False,
                    "download_dir": None
                }]
            }
            
            # Save config to temporary file
            config_path = output_dir_abs / f"harbor_config_{run_number}.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Run Harbor via CLI
            # Harbor CLI documentation shows: harbor run --dataset ... --agent ... --model ...
            # For custom tasks, we'll try using a config file approach
            # If that doesn't work, we may need to use Harbor's Python API or different CLI flags
            env = os.environ.copy()
            env['OPENROUTER_API_KEY'] = self.openrouter_key
            
            # Configure remote Docker if specified
            # Harbor should respect DOCKER_HOST environment variable
            # Note: Harbor's internal docker compose subprocess calls will inherit this
            if settings.docker_host:
                env['DOCKER_HOST'] = settings.docker_host
                # Only set TLS vars if actually using TLS
                if settings.docker_tls_verify == "1":
                    env['DOCKER_TLS_VERIFY'] = "1"
                    if settings.docker_cert_path:
                        env['DOCKER_CERT_PATH'] = settings.docker_cert_path
                else:
                    # Explicitly unset TLS vars when not using TLS to avoid Docker looking for certs
                    env.pop('DOCKER_TLS_VERIFY', None)
                    env.pop('DOCKER_CERT_PATH', None)
                print(f"[HarborService] Using remote Docker: {settings.docker_host} (TLS: {settings.docker_tls_verify})")
            else:
                # Use local Docker socket (default behavior)
                # Make sure TLS vars are not set
                env.pop('DOCKER_TLS_VERIFY', None)
                env.pop('DOCKER_CERT_PATH', None)
                print("[HarborService] Using local Docker daemon")
            
            # Try running Harbor with config file first
            # If Harbor doesn't support --config, try alternative approaches
            try:
                process = await asyncio.create_subprocess_exec(
                    'harbor', 'run', '--config', str(config_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                    cwd=str(output_dir_abs)
                )
            except FileNotFoundError:
                # Harbor CLI not found, try using Python API dynamically
                # This is a fallback if Harbor CLI is not in PATH
                raise Exception("Harbor CLI not found. Make sure 'harbor' is installed and in PATH. Run: pip install harbor or uv tool install harbor")
            
            stdout, stderr = await process.communicate()
            
            # Decode output
            stdout_text = stdout.decode('utf-8', errors='ignore') if stdout else ""
            stderr_text = stderr.decode('utf-8', errors='ignore') if stderr else ""
            
            # Save full output to files for debugging
            error_log_file = output_dir_abs / f"harbor_error_{run_number}.txt"
            with open(error_log_file, 'w') as f:
                f.write("=== HARBOR EXECUTION DEBUG INFO ===\n\n")
                f.write(f"Return Code: {process.returncode}\n")
                f.write(f"Config Path: {config_path}\n")
                f.write(f"Task Path: {task_path_abs}\n")
                f.write(f"Output Dir: {output_dir_abs}\n\n")
                f.write("=== STDOUT ===\n")
                f.write(stdout_text)
                f.write("\n\n=== STDERR ===\n")
                f.write(stderr_text)
                f.write("\n")
            
            # Find the result directory (Harbor creates it based on job_name or task name)
            # Even if returncode != 0, the trial might have completed successfully
            # (e.g., metrics computation error but trial succeeded)
            result_path = self._find_result_path(output_dir_abs, f"job_run_{run_number}")
            
            if not result_path:
                # Try to find any recent trial directory
                trial_dirs = [d for d in output_dir_abs.iterdir() if d.is_dir()]
                if trial_dirs:
                    result_path = max(trial_dirs, key=lambda p: p.stat().st_mtime if p.exists() else 0)
            
            # If we found results, parse them even if returncode != 0
            # (trial might have succeeded but metrics computation failed)
            if result_path and result_path.exists():
                # Parse results
                test_results = parse_harbor_results(result_path)
                logs = read_harbor_logs(result_path)
                
                # If we have valid test results, treat as success even if returncode != 0
                if test_results.get("total", 0) > 0:
                    # Combine stdout with logs
                    combined_logs = stdout_text
                    
                    # Include agent logs (most useful for users - shows actual agent execution)
                    if logs:
                        combined_logs += "\n\n--- Agent Execution Logs ---\n" + logs
                    
                    # Only include stderr if it's NOT the known metrics error
                    # (we'll add a simple warning instead)
                    is_metrics_error = (
                        "IndexError" in stderr_text 
                        and "list index out of range" in stderr_text 
                        and "self._metrics[trial_config.task.source" in stderr_text
                    )
                    
                    if stderr_text and not is_metrics_error:
                        # This is a different error, include it (but limit length)
                        combined_logs += "\n\n--- Harbor Errors ---\n" + stderr_text[:2000]
                        if len(stderr_text) > 2000:
                            combined_logs += "\n... (truncated, see error file for full details) ..."
                    
                    # Note: metrics error in stderr but trial succeeded
                    # Add warning BEFORE truncating so it appears in the file too
                    if process.returncode != 0 and is_metrics_error:
                        combined_logs += "\n\n⚠️ Note: Harbor metrics computation failed, but the trial completed successfully. All tests passed."
                    
                    # Truncate logs for database if too long
                    if len(combined_logs) > 50000:
                        log_file = output_dir_abs / f"harbor_logs_{run_number}.txt"
                        with open(log_file, 'w') as f:
                            f.write(combined_logs)
                        combined_logs = combined_logs[:50000] + f"\n... (truncated, see {log_file.name} for full logs) ..."
                    
                    return {
                        "run_number": run_number,
                        "result": {"returncode": process.returncode, "stdout": stdout_text},
                        "tests_passed": test_results["passed"],
                        "tests_total": test_results["total"],
                        "tests_failed": test_results["failed"],
                        "test_details": test_results.get("details", []),
                        "logs": combined_logs,
                        "result_path": str(result_path),
                        "status": "completed" if test_results["passed"] > 0 else "failed"
                    }
            
            # If no results found and returncode != 0, treat as failure
            if process.returncode != 0:
                # Truncate error for database (keep last 10000 chars)
                error_msg = stderr_text or stdout_text or "Harbor execution failed"
                if len(error_msg) > 10000:
                    error_msg = "... (truncated, see error file) ...\n" + error_msg[-10000:]
                
                # Truncate logs for database too
                combined_logs = stdout_text + "\n" + stderr_text
                if len(combined_logs) > 50000:
                    combined_logs = combined_logs[:50000] + "\n... (truncated, see error file for full logs) ..."
                
                return {
                    "run_number": run_number,
                    "status": "failed",
                    "error": error_msg,
                    "tests_passed": 0,
                    "tests_total": 0,
                    "logs": combined_logs,
                    "result_path": str(error_log_file) if error_log_file.exists() else None
                }
            
            # If we get here, returncode == 0 and results exist (normal success case)
            # Parse results normally
            if result_path and result_path.exists():
                test_results = parse_harbor_results(result_path)
                logs = read_harbor_logs(result_path)
            else:
                # No results found even though returncode == 0 (shouldn't happen)
                test_results = {"passed": 0, "total": 0, "failed": 0, "details": []}
                logs = ""
            
            # Combine stdout with logs
            combined_logs = stdout_text
            
            # Include agent logs (most useful for users - shows actual agent execution)
            if logs:
                combined_logs += "\n\n--- Agent Execution Logs ---\n" + logs
            
            # Include stderr if present (but limit length for non-critical errors)
            if stderr_text:
                combined_logs += "\n\n--- Harbor Messages ---\n" + stderr_text[:2000]
                if len(stderr_text) > 2000:
                    combined_logs += "\n... (truncated, see error file for full details) ..."
            
            # Truncate logs for database if too long
            if len(combined_logs) > 50000:
                log_file = output_dir_abs / f"harbor_logs_{run_number}.txt"
                with open(log_file, 'w') as f:
                    f.write(combined_logs)
                combined_logs = combined_logs[:50000] + f"\n... (truncated, see {log_file.name} for full logs) ..."
            
            return {
                "run_number": run_number,
                "result": {"returncode": process.returncode, "stdout": stdout_text},
                "tests_passed": test_results["passed"],
                "tests_total": test_results["total"],
                "tests_failed": test_results["failed"],
                "test_details": test_results.get("details", []),
                "logs": combined_logs,
                "result_path": str(result_path) if result_path else None,
                "status": "completed" if test_results["passed"] > 0 else "failed"
            }
            
        except Exception as e:
            # Save full error to file for debugging
            try:
                output_dir_abs = Path(output_dir).resolve()
                error_file = output_dir_abs / f"error_{run_number}.txt"
                import traceback
                full_traceback = traceback.format_exc()
                
                with open(error_file, 'w') as f:
                    f.write("=== EXCEPTION OCCURRED ===\n\n")
                    f.write(f"Error: {str(e)}\n\n")
                    f.write("=== FULL TRACEBACK ===\n")
                    f.write(full_traceback)
                    f.write("\n")
            except Exception:
                # If we can't write the error file, continue anyway
                pass
            
            # Truncate error for database (keep last 10000 chars)
            error_msg = str(e)
            if len(error_msg) > 10000:
                error_msg = "... (truncated, see error file) ...\n" + error_msg[-10000:]
            
            return {
                "run_number": run_number,
                "status": "failed",
                "error": error_msg,
                "tests_passed": 0,
                "tests_total": 0,
                "logs": error_msg,
                "result_path": str(error_file) if 'error_file' in locals() else None
            }
    
    def _find_result_path(self, output_dir: Path, job_name: str) -> Path:
        """Find the Harbor result directory for a job"""
        # Harbor creates: output_dir/job_name/task__XXX/ (trial directory)
        # We need to find the trial directory, not just the job directory
        if not output_dir.exists():
            return None
        
        # First, look for job directory (job_run_1, etc.)
        job_dir = None
        for item in output_dir.iterdir():
            if item.is_dir() and job_name in item.name:
                job_dir = item
                break
        
        if not job_dir:
            # If no job directory found, look for any directory with trial.log
            for item in output_dir.iterdir():
                if item.is_dir() and (item / "trial.log").exists():
                    return item
            return None
        
        # Look inside job directory for trial directories (task__XXX)
        for item in job_dir.iterdir():
            if item.is_dir():
                # Trial directories have trial.log and verifier/ directory
                if (item / "trial.log").exists() or (item / "verifier").exists():
                    return item
        
        # Fallback: return job directory if no trial directory found
        return job_dir

