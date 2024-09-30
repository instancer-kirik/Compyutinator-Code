import click
import subprocess
from pathlib import Path
import json
import shutil

class EnvironmentManager:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.environments_file = self.base_path / "environments.json"
        self.load_environments()

    def load_environments(self):
        if self.environments_file.exists():
            with open(self.environments_file, 'r') as f:
                self.environments = json.load(f)
        else:
            self.environments = {}

    def save_environments(self):
        with open(self.environments_file, 'w') as f:
            json.dump(self.environments, f, indent=2)

    def create_environment(self, name, language, version):
        if name in self.environments:
            click.echo(f"Environment {name} already exists.")
            return

        env_path = self.base_path / name
        env_path.mkdir(exist_ok=True)

        if language == "python":
            subprocess.run(["python", "-m", "venv", str(env_path)])
        elif language == "kotlin":
            # Use sdkman to install Kotlin
            subprocess.run(["sdk", "install", "kotlin", version])
        elif language == "csharp":
            # Use dotnet to create a new C# project
            subprocess.run(["dotnet", "new", "console", "-o", str(env_path)])
        elif language == "elixir":
            # Use kiex to install Elixir
            subprocess.run(["kiex", "install", version])
        else:
            click.echo(f"Unsupported language: {language}")
            return

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
        for name, env in self.environments.items():
            click.echo(f"{name}: {env['language']} {env['version']}")

    def get_environment_path(self, name):
        return self.environments.get(name, {}).get("path")

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