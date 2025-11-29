import yaml
from pathlib import Path
from typing import Any, Callable, List, Optional
from core.utils.singleton import Singleton
from core.logger.logger_manager import LoggerManager

class ConfigManager(Singleton):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__()
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)

    def load_config(self, config_file: str) -> None:
        self.config = self._load_config_file(config_file)

    def get_config(self, keys: str, default: Optional[Any] = None, converter: Optional[Callable] = None) -> Any:
        assert self.config is not None, "Config not loaded"

        key_list = keys.split('.')
        current = self.config

        for key in key_list:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                if default is None:
                    self.logger.error(f"Key {keys} not found in config")
                current = default
                break
        self.logger.debug(f"Config: {keys} = {current}")

        if current is not None and converter is not None:
            return converter(current)
        return current


    def _load_config_file(self, config_file: str) -> dict[str, Any]:
        file_path = Path(config_file)

        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path

        file_path = file_path.resolve()

        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        config_dict = self._load_yaml_file(file_path)
        self.logger.debug(f"Loaded file: {config_file}")
        resolved_config = self._resolve_dict(config_dict)

        return resolved_config

    def _resolve_dict(self, config_dict: dict[str, Any]) -> dict[str, Any]:
        resolved_config = {}

        for key, value in config_dict.items():
            if key == 'file':
                return self._load_config_file(value)

            if isinstance(value, dict):
                resolved_config[key] = self._resolve_dict(value)
            elif isinstance(value, list):
                resolved_config[key] = self._resolve_list(value)
            else:
                resolved_config[key] = value

        return resolved_config

    def _resolve_list(self, items: List[Any]) -> List[Any]:
        resolved_items = []

        for item in items:
            if isinstance(item, dict):
                resolved_items.append(self._resolve_dict(item))
            else:
                resolved_items.append(item)

        return resolved_items

    def _load_yaml_file(self, file_path: Path) -> dict[str, Any]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            if config is None:
                return {}

            return config

        except yaml.YAMLError as e:
            self.logger.error(f"YAML file parsing error {file_path}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"File loading error {file_path}: {e}")
            raise