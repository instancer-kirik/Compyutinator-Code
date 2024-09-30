import os
import subprocess
import json
import logging

class BuildManager:
    def __init__(self, cccore):
        self.cccore = cccore
        self.build_configs = {}

    def load_build_config(self, project_name):
        project_path = self.cccore.project_manager.get_project_path(project_name)
        config_path = os.path.join(project_path, 'build_config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.build_configs[project_name] = json.load(f)
        else:
            self.build_configs[project_name] = {}

    def save_build_config(self, project_name):
        project_path = self.cccore.project_manager.get_project_path(project_name)
        config_path = os.path.join(project_path, 'build_config.json')
        with open(config_path, 'w') as f:
            json.dump(self.build_configs[project_name], f, indent=4)

    def build_project(self, project_name):
        if project_name not in self.build_configs:
            self.load_build_config(project_name)

        config = self.build_configs.get(project_name, {})
        build_command = config.get('build_command')
        if not build_command:
            logging.warning(f"No build command specified for project: {project_name}")
            return False

        project_path = self.cccore.project_manager.get_project_path(project_name)
        try:
            result = subprocess.run(build_command, cwd=project_path, shell=True, check=True, capture_output=True, text=True)
            logging.info(f"Build output for {project_name}:\n{result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Build failed for {project_name}. Error: {e.stderr}")
            return False

    def run_project(self, project_name):
        if project_name not in self.build_configs:
            self.load_build_config(project_name)

        config = self.build_configs.get(project_name, {})
        run_command = config.get('run_command')
        if not run_command:
            logging.warning(f"No run command specified for project: {project_name}")
            return False

        project_path = self.cccore.project_manager.get_project_path(project_name)
        try:
            result = subprocess.Popen(run_command, cwd=project_path, shell=True)
            logging.info(f"Started process for {project_name} with PID: {result.pid}")
            return True
        except Exception as e:
            logging.error(f"Failed to run project {project_name}. Error: {str(e)}")
            return False

    def set_build_command(self, project_name, command):
        if project_name not in self.build_configs:
            self.load_build_config(project_name)
        self.build_configs[project_name]['build_command'] = command
        self.save_build_config(project_name)

    def set_run_command(self, project_name, command):
        if project_name not in self.build_configs:
            self.load_build_config(project_name)
        self.build_configs[project_name]['run_command'] = command
        self.save_build_config(project_name)