import click
import subprocess
from pathlib import Path
import json
import shutil
import os
import platform
import logging

class EnvironmentManager:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.nix_portable_path = self.base_path / "nix-portable"
        self.environments_file = self.base_path / "environments.json"
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

if __name__ == '__main__':
    cli()