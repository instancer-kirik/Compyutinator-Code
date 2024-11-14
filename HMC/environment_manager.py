import click
import subprocess
from pathlib import Path
import json
import shutil
import os
import platform
import logging
from typing import Dict, Any, List
import time
from .system_analyzer import SystemInfo
class EnvironmentManager:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.nix_portable_path = self.base_path / "nix-portable"
        self.environments_file = self.base_path / "environments.json"
        self.system_info = SystemInfo(name="Development Environment")
        self.load_environments()
        self.ensure_nix_portable()

    def load_environments(self):
        if self.environments_file.exists():
            with open(self.environments_file, 'r') as f:
                self.environments = json.load(f)
        else:
            self.environments = {}

    def save_environments(self):
        with open(self.environments_file, 'w') as f:
            json.dump(self.environments, f, indent=2)

    def ensure_nix_portable(self):
        if not self.nix_portable_path.exists():
            # Ensure the directory exists
            self.base_path.mkdir(parents=True, exist_ok=True)
            
            # Path to the nix-portable binary in your project resources
            arch = platform.machine()
            if arch == 'x86_64':
                source_filename = "nix-portable-x86_64"
            elif arch == 'aarch64':
                source_filename = "nix-portable-aarch64"
            elif arch == 'AMD64':
                source_filename = "nix-portable-x86_64"
           
                
            else:
                raise RuntimeError(f"Unsupported architecture: {arch}")
            
            source_path = Path(__file__).parent.parent / "NITTY_GRITTY" / source_filename
            
            if not source_path.exists():
                logging.error(f"nix-portable binary not found at {source_path}")
                raise FileNotFoundError(f"nix-portable binary not found at {source_path}")
            
            # Copy nix-portable from your project's resources to base_path
            shutil.copy(str(source_path), str(self.nix_portable_path))
            self.nix_portable_path.chmod(0o755)  # Make it executable
            logging.info(f"Copied nix-portable to {self.nix_portable_path}")

    def run_nix_command(self, command):
        full_command = f"{self.nix_portable_path} {command}"
        return subprocess.run(full_command, shell=True, check=True, capture_output=True, text=True)

    def create_environment(self, name, language, version):
        if name in self.environments:
            click.echo(f"Environment {name} already exists.")
            return

        env_path = self.base_path / name
        env_path.mkdir(exist_ok=True)

        # Use nix-shell to create an environment
        command = f"nix-shell -p {language} --run 'echo Environment created'"
        self.run_nix_command(command)

        self.environments[name] = {
            "path": str(env_path),
            "language": language,
            "version": version
        }
        self.save_environments()
        click.echo(f"Created {language} environment {name} with version {version}")

    def delete_environment(self, name):
        if name not in self.environments:
            click.echo(f"Environment {name} does not exist.")
            return

        env_path = Path(self.environments[name]["path"])
        shutil.rmtree(env_path)
        del self.environments[name]
        self.save_environments()
        click.echo(f"Deleted environment {name}")

    def list_environments(self):
        # List installed packages
        command = "nix-env -q"
        result = self.run_nix_command(command)
        print(result.stdout)
        for name, env in self.environments.items():
            click.echo(f"{name}: {env['language']} {env['version']}")

    def get_environment_path(self, name):
        return self.environments.get(name, {}).get("path")

    def ensure_nix_environment(self):
        # This is not needed with nix-portable
        pass

    def get_environment_info(self, env_name: str) -> Dict[str, Any]:
        """Get detailed environment information"""
        if env_name not in self.environments:
            return {}
            
        env_data = self.environments[env_name]
        env_path = Path(env_data["path"])
        
        # Update system info
        self.system_info.name = f"Environment: {env_name}"
        self.system_info.root_path = env_path
        self.system_info.technical_stack = [env_data["language"]]
        self.system_info.environment_variables = self._get_env_variables(env_name)
        
        return {
            "environment": env_data,
            "system": self.system_info.to_json(),
            "packages": self._get_installed_packages(env_name)
        }

    def _get_env_variables(self, env_name: str) -> Dict[str, str]:
        """Get environment variables for the environment"""
        try:
            env_path = self.get_environment_path(env_name)
            if not env_path:
                return {}
                
            result = self.run_nix_command(f"printenv")
            env_vars = {}
            for line in result.stdout.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
            return env_vars
            
        except Exception as e:
            logging.error(f"Error getting environment variables: {e}")
            return {}

    def _get_installed_packages(self, env_name: str) -> List[str]:
        """Get list of installed packages"""
        try:
            result = self.run_nix_command("nix-env -q")
            return [line.strip() for line in result.stdout.split('\n') if line.strip()]
        except Exception as e:
            logging.error(f"Error getting installed packages: {e}")
            return []

    def export_environment_info(self, env_name: str, format: str = 'md') -> bool:
        """Export environment information"""
        try:
            env_info = self.get_environment_info(env_name)
            output_path = self.base_path / env_name / 'environment_info'
            output_path.mkdir(parents=True, exist_ok=True)
            
            if format == 'md':
                with open(output_path / 'overview.md', 'w') as f:
                    f.write(self.system_info.to_markdown())
            elif format == 'json':
                with open(output_path / 'overview.json', 'w') as f:
                    json.dump(env_info, f, indent=2)
                    
            return True
            
        except Exception as e:
            logging.error(f"Error exporting environment info: {e}")
            return False

class EnvironmentMonitor:
    def __init__(self, env_manager):
        self.env_manager = env_manager
        self.update_interval = 300  # 5 minutes
        
    def start_monitoring(self):
        """Start periodic monitoring"""
        while True:
            self.update_environments()
            time.sleep(self.update_interval)
            
    def update_environments(self):
        """Update all environment information"""
        for env_name in self.env_manager.environments:
            self.env_manager.update_environment_info(env_name)

@click.group()
@click.option('--base-path', default='./environments', help='Base path for environments')
@click.pass_context
def cli(ctx, base_path):
    ctx.obj = EnvironmentManager(base_path)

@cli.command()
@click.argument('name')
@click.argument('language')
@click.argument('version')
@click.pass_obj
def create(env_manager, name, language, version):
    """Create a new environment"""
    env_manager.create_environment(name, language, version)

@cli.command()
@click.argument('name')
@click.pass_obj
def delete(env_manager, name):
    """Delete an environment"""
    env_manager.delete_environment(name)

@cli.command()
@click.pass_obj
def list(env_manager):
    """List all environments"""
    env_manager.list_environments()

@cli.command()
@click.argument('name')
@click.option('--format', type=click.Choice(['md', 'json']), default='md')
@click.pass_obj
def info(env_manager, name, format):
    """Get detailed environment information"""
    if env_manager.export_environment_info(name, format):
        click.echo(f"Environment info exported to {name}/environment_info")
    else:
        click.echo("Failed to export environment info")

if __name__ == '__main__':
    cli()