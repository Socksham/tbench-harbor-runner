import asyncio
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from app.config import settings
from app.models.schemas import ModelType
from app.services.result_parser import parse_harbor_results, read_harbor_logs


class RemoteHarborService:
    """Service to run Harbor on a remote host via SSH"""
    
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
        """Run Harbor task on remote host"""
        
        if not settings.remote_execution_enabled:
            raise ValueError("Remote execution not enabled. Set REMOTE_EXECUTION_ENABLED=true")
        
        if not settings.remote_host:
            raise ValueError("Remote host not configured. Set REMOTE_HOST=user@hostname")
        
        timeout_multiplier = timeout_multiplier or settings.harbor_timeout_multiplier
        
        # Create unique job directory on remote host
        job_id = output_dir.name
        remote_job_dir = f"{settings.remote_work_dir}/{job_id}"
        
        try:
            # Step 1: Ensure remote directory exists
            await self._ensure_remote_directory(remote_job_dir)
            
            # Step 2: Copy task and output directory to remote host
            print(f"[RemoteHarborService] Copying files to {settings.remote_host}...")
            await self._copy_to_remote(task_path, output_dir, remote_job_dir)
            
            # Step 3: Run Harbor on remote host
            print(f"[RemoteHarborService] Running Harbor on {settings.remote_host}...")
            harbor_result = await self._run_harbor_remote(
                remote_job_dir, run_number, model, timeout_multiplier
            )
            
            # Step 4: Copy results back from remote host
            print(f"[RemoteHarborService] Copying results back from {settings.remote_host}...")
            await self._copy_from_remote(remote_job_dir, output_dir)
            
            # Step 5: Parse results (same as local version)
            result_path = self._find_result_path(output_dir, f"job_run_{run_number}")
            
            if result_path and result_path.exists():
                test_results = parse_harbor_results(result_path)
                logs = read_harbor_logs(result_path)
                
                # Combine stdout with logs
                combined_logs = harbor_result.get("stdout", "")
                if logs:
                    combined_logs += "\n\n--- Agent Execution Logs ---\n" + logs
                
                return {
                    "status": "completed" if test_results.get("total", 0) > 0 else "failed",
                    "tests_passed": test_results.get("passed", 0),
                    "tests_total": test_results.get("total", 0),
                    "logs": combined_logs,
                    "result_path": str(result_path),
                    "error": harbor_result.get("stderr") if harbor_result.get("returncode") != 0 else None
                }
            
            # No results found
            return {
                "status": "failed",
                "tests_passed": 0,
                "tests_total": 0,
                "logs": harbor_result.get("stdout", ""),
                "result_path": None,
                "error": harbor_result.get("stderr") or "No results found after Harbor execution"
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"[RemoteHarborService] Error: {error_msg}")
            return {
                "status": "failed",
                "tests_passed": 0,
                "tests_total": 0,
                "logs": "",
                "result_path": None,
                "error": f"Remote execution failed: {error_msg}"
            }
    
    async def _ensure_remote_directory(self, remote_dir: str):
        """Ensure remote directory exists"""
        ssh_cmd = self._build_ssh_command()
        mkdir_cmd = f"mkdir -p {remote_dir}"
        
        process = await asyncio.create_subprocess_shell(
            f"{ssh_cmd} '{mkdir_cmd}'",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise Exception(f"Failed to create remote directory: {stderr.decode('utf-8', errors='ignore')}")
    
    async def _copy_to_remote(
        self, task_path: Path, output_dir: Path, remote_job_dir: str
    ):
        """Copy task and job directory to remote host using rsync"""
        
        # Build rsync command with SSH options
        rsync_ssh_opts = self._build_rsync_ssh_options()
        
        # Copy task directory
        task_remote = f"{remote_job_dir}/task"
        rsync_task = [
            "rsync", "-avz", "--delete",
            "-e", f"ssh {rsync_ssh_opts}",
            f"{task_path}/",
            f"{settings.remote_host}:{task_remote}/"
        ]
        
        process = await asyncio.create_subprocess_exec(
            *rsync_task,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise Exception(f"Failed to copy task to remote: {stderr.decode('utf-8', errors='ignore')}")
        
        # Copy existing output directory structure (if any)
        rsync_output = [
            "rsync", "-avz",
            "-e", f"ssh {rsync_ssh_opts}",
            f"{output_dir}/",
            f"{settings.remote_host}:{remote_job_dir}/"
        ]
        
        process = await asyncio.create_subprocess_exec(
            *rsync_output,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        # Don't fail if output directory doesn't exist yet (first run)
        if process.returncode != 0 and "No such file or directory" not in stderr.decode('utf-8', errors='ignore'):
            print(f"[RemoteHarborService] Warning: Could not copy output directory: {stderr.decode('utf-8', errors='ignore')}")
    
    async def _run_harbor_remote(
        self, remote_job_dir: str, run_number: int, 
        model: ModelType, timeout_multiplier: float
    ) -> Dict[str, Any]:
        """Execute Harbor on remote host via SSH"""
        
        # Create Harbor config (same structure as local version)
        config = {
            "job_name": f"job_run_{run_number}",
            "jobs_dir": remote_job_dir,
            "n_attempts": 1,
            "timeout_multiplier": timeout_multiplier,
            "debug": False,
            "orchestrator": {
                "type": "local",
                "n_concurrent_trials": 1,
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
                "path": f"{remote_job_dir}/task",
                "source": "uploaded",
                "overwrite": False,
                "download_dir": None
            }]
        }
        
        # Write config to temporary file locally
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f, indent=2)
            local_config_path = f.name
        
        try:
            # Copy config to remote host
            config_remote = f"{remote_job_dir}/harbor_config_{run_number}.json"
            rsync_ssh_opts = self._build_rsync_ssh_options()
            
            rsync_config = [
                "rsync",
                "-e", f"ssh {rsync_ssh_opts}",
                local_config_path,
                f"{settings.remote_host}:{config_remote}"
            ]
            
            process = await asyncio.create_subprocess_exec(
                *rsync_config,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                raise Exception(f"Failed to copy config to remote: {stderr.decode('utf-8', errors='ignore')}")
            
            # Run Harbor on remote host
            ssh_cmd = self._build_ssh_command()
            
            # Escape the API key for shell
            escaped_key = self.openrouter_key.replace("'", "'\"'\"'")
            
            # Add ~/.local/bin to PATH for pipx installations (non-interactive SSH doesn't load .bashrc)
            harbor_cmd = (
                f"export PATH=\"$HOME/.local/bin:$PATH\" && "
                f"cd {remote_job_dir} && "
                f"export OPENROUTER_API_KEY='{escaped_key}' && "
                f"harbor run --config {config_remote}"
            )
            
            full_ssh_cmd = f"{ssh_cmd} '{harbor_cmd}'"
            
            process = await asyncio.create_subprocess_shell(
                full_ssh_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "stdout": stdout.decode('utf-8', errors='ignore'),
                "stderr": stderr.decode('utf-8', errors='ignore'),
                "returncode": process.returncode
            }
            
        finally:
            # Clean up local temp file
            Path(local_config_path).unlink(missing_ok=True)
    
    async def _copy_from_remote(
        self, remote_job_dir: str, output_dir: Path
    ):
        """Copy results back from remote host using rsync"""
        
        rsync_ssh_opts = self._build_rsync_ssh_options()
        
        rsync_cmd = [
            "rsync", "-avz",
            "-e", f"ssh {rsync_ssh_opts}",
            f"{settings.remote_host}:{remote_job_dir}/",
            f"{output_dir}/"
        ]
        
        process = await asyncio.create_subprocess_exec(
            *rsync_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            # Don't fail if directory doesn't exist (Harbor might have failed early)
            if "No such file or directory" not in error_msg:
                raise Exception(f"Failed to copy results from remote: {error_msg}")
    
    def _find_result_path(self, output_dir: Path, job_name: str) -> Optional[Path]:
        """Find the Harbor result directory for a job (same logic as HarborService)"""
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
    
    def _build_ssh_command(self) -> str:
        """Build SSH command with proper options"""
        host = settings.remote_host
        key_opt = f"-i {settings.remote_ssh_key_path}" if settings.remote_ssh_key_path else ""
        port_opt = f"-p {settings.remote_ssh_port}" if settings.remote_ssh_port != 22 else ""
        
        parts = ["ssh"]
        if key_opt:
            parts.append(key_opt)
        if port_opt:
            parts.append(port_opt)
        parts.append(host)
        
        return " ".join(parts)
    
    def _build_rsync_ssh_options(self) -> str:
        """Build SSH options for rsync"""
        opts = []
        if settings.remote_ssh_key_path:
            opts.append(f"-i {settings.remote_ssh_key_path}")
        if settings.remote_ssh_port != 22:
            opts.append(f"-p {settings.remote_ssh_port}")
        return " ".join(opts)

