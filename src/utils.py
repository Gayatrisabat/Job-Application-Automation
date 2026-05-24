import logging
import os
from configparser import ConfigParser


def setup_logging():
    """Configures logging for the application (file + console)."""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, 'app.log'), encoding='utf-8'),
            logging.StreamHandler(),
        ],
    )
    logging.info("Logging configured.")


def load_config(
    config_file_path: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'config', 'settings.ini'
    )
) -> ConfigParser:
    """Loads configuration from the INI file."""
    config = ConfigParser()
    if os.path.exists(config_file_path):
        config.read(config_file_path)
        logging.info(f"Configuration loaded from {config_file_path}")
    else:
        logging.warning(f"Config file not found: {config_file_path}. Using defaults.")
    return config


if __name__ == '__main__':
    setup_logging()
    cfg = load_config()
    logging.info("Utils module loaded successfully.")
    print("OpenAI Model:", cfg.get('API', 'openai_model', fallback='gpt-4o-mini'))
