import yaml
import os
from pathlib import Path

def load_config(config_path: str = 'config.yaml') -> dict:
    """Load project settings from a YAML configuration file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)

    return config

def print_hi(name):
    print(f'Hi, {name}')


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # Load configuration
    config = load_config()

    ## TODO - EXPAND : Add the other settings to be collected here
    ## TODO - GOAL : I want to keep the settings clear and ready for RUNNING DARK
    # Access settings from the config
    project_name = config['app']['name']
    greeting = config['greeting']
    settings = config['settings']

    print(greeting)
    print(f"Project: {project_name}")

    ## TODO - REMOVE : This is just for first method
    print_hi('Atropos')

