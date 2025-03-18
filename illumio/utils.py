import os
import configparser
from .exceptions import ConfigurationError

def load_config(config_file):
    """Charge la configuration depuis un fichier INI."""
    if not os.path.exists(config_file):
        create_default_config(config_file)
        raise ConfigurationError(
            f"Fichier de configuration créé: {config_file}. "
            "Veuillez éditer ce fichier avec vos paramètres et relancer le script."
        )
    
    config = configparser.ConfigParser()
    config.read(config_file)
    return config

def create_default_config(config_file):
    """Crée un fichier de configuration par défaut."""
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    
    config = configparser.ConfigParser()
    config['illumio'] = {
        'base_url': 'https://illumio.fr:8443',
        'org_id': '1',
        'verify_ssl': 'False',
        'csrf_token': '',
        'session_cookie': ''
    }
    
    with open(config_file, 'w') as f:
        config.write(f)