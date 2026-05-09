from src.tools.settings import Settings


def print_hi(name):
    print(f'Hi, {name}')


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # Load configuration
    settings = Settings()

    ## TODO - EXPAND : Add the other settings to be collected here
    ## TODO - GOAL : I want to keep the settings clear and ready for RUNNING DARK
    # Access settings from the config
    project_name = settings['app']['name']
    project_description = settings['app']['description']
    app_settings = settings['settings']

    print(f"Project: {project_name}")
    print(f"Description: {project_description}")
    print(f"Settings: {app_settings}")

    ## TODO - REMOVE : This is just for first method
    print_hi('Atropos')

