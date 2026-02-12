import os


def get_setting(env_name, setting_name, settings={}, default_value=None):
    """
    Gets a setting from an environment variable or configuration dictionary.
    If not blank, environment variables have precedence over the configuration dictionary.

    :param env_name: the name of the environment variable
    :param setting_name: the name of the setting in the configuration dictionary
    :param settings the dictionary containing settings
    :param default_value: the default setting value
    """
    env_val = os.environ.get(env_name)
    setting_val = settings.get(setting_name) if isinstance(settings, dict) else None
    if env_val is None and setting_val is not None:
        return setting_val
    elif env_val is not None and setting_val is None:
        return env_val if env_val != '' else default_value
    elif env_val is not None and setting_val is not None:
        return env_val if env_val != '' else setting_val
    # neither are defined
    return default_value
