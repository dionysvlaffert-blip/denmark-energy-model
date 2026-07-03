from pathlib import Path
import yaml


class ProjectConfig:
    """
    Project configuration loaded from a YAML file.

    The YAML file is separated into paths and settings, but both are exposed as
    direct attributes, for example config.region_coordinates_file or config.weather_year.
    Path entries are converted to pathlib.Path objects during loading.
    """

    def __init__(self, config_file):
        self.config_file = Path(config_file)
        self._path_keys = set()
        self._setting_keys = set()
        self._load_config()

    def _load_config(self):
        """
        Read the YAML file and load paths and settings as object attributes.

        Input: self.config_file.
        Output: modifies this ProjectConfig instance.
        """
        if not self.config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")

        with open(self.config_file, "r", encoding="utf-8") as file:
            config_data = yaml.safe_load(file)

        self._load_paths(config_data["paths"])
        self._load_settings(config_data["settings"])
    
    def _load_paths(self, paths):
        """
        Store path entries from the YAML as pathlib.Path attributes.

        Input: dict from the YAML paths section.
        Output: updates attributes and internal path key list.
        """
        for key, value in paths.items():
            setattr(self, key, Path(value))
            self._path_keys.add(key)

    def _load_settings(self, settings):
        """
        Store scalar/list/dict settings from the YAML as attributes.

        Input: dict from the YAML settings section.
        Output: updates attributes and internal setting key list.
        """
        for key, value in settings.items():
            setattr(self, key, value)
            self._setting_keys.add(key)

    def print_settings(self):
        """
        Print all loaded config paths and settings.

        Input: this ProjectConfig instance.
        Output: prints to console; returns nothing.
        """
        for key in sorted(self._path_keys | self._setting_keys):
            print(f"{key}: {getattr(self, key)}")

    def update_setting(self, key, value):
        """
        Update one known path or setting value.

        Inputs: config key and new value.
        Output: modifies this ProjectConfig instance.
        """

        if key in self._path_keys:
            setattr(self, key, Path(value))
            return

        if key in self._setting_keys:
            setattr(self, key, value)
            return

        raise KeyError(f"Unknown config setting: {key}")

    def update_dict_setting(self, key, dict_key, value):
        """
        Update one value inside a dictionary setting.

        Inputs: config key, dictionary key and new value.
        Output: modifies this ProjectConfig instance.
        """
        if key not in self._setting_keys:
            raise KeyError(f"Unknown config setting: {key}")

        if dict_key not in getattr(self, key):
            raise KeyError(f"Unknown config setting: {key}.{dict_key}")

        getattr(self, key)[dict_key] = value

    def add_setting_name_suffix(self, suffix):
        """
        Append a suffix to setting_name for scenario-specific output files.

        Input: suffix string.
        Output: modifies self.setting_name.
        """
        self.setting_name = f"{self.setting_name}_{suffix}"

    @property
    def network_output_file(self):
        """
        Build the NetCDF output path for the current config.

        Input: region level, weather year and setting_name.
        Output: pathlib.Path to the network output file.
        """
        filename = f"denmark_basic_network_{self.region_level}_{self.weather_year}_{self.setting_name}.nc"
        return self.network_output_dir / filename