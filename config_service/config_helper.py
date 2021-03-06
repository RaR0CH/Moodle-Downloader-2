import os
import json

from pathlib import Path


class ConfigHelper:
    """
    Handles the saving, formatting and loading of the local configuration.
    """

    def __init__(self, storage_path: str):
        self._whole_config = {}
        self.config_path = str(Path(storage_path) / 'config.json')

    def is_present(self) -> bool:
        # Tests if a configuration file exists
        return os.path.isfile(self.config_path)

    def load(self):
        # Opens the configuration file and parse it to a JSON object
        try:
            with open(self.config_path, 'r') as f:
                config_raw = f.read()
                self._whole_config = json.loads(config_raw)
        except IOError:
            raise ValueError('No config found!')

    def _save(self):
        # Saves the JSON object back to file
        with open(self.config_path, 'w+', encoding='utf-8') as f:
            config_formatted = json.dumps(self._whole_config, indent=4)
            f.write(config_formatted)

    def get_property(self, key: str) -> any:
        # returns a property if configured
        try:
            return self._whole_config[key]
        except KeyError:
            raise ValueError('The %s-Property is not yet configured!' % (key))

    def set_property(self, key: str, value: any):
        # sets a property in the JSON object
        self._whole_config.update({key: value})
        self._save()

    def remove_property(self, key):
        # removes a property from the JSON object
        self._whole_config.pop(key, None)
        #                           ^ behavior if the key is not present
        self._save()

    def set_default_filename_character_map(self, default_windows_map: bool):
        # Sets the default filename_character_map for Windows or Empty
        if default_windows_map:
            windows_map = {'\\': '＼', '/': '／', ':': '꞉', '?': '？', '*': '＊', '<': '＜', '>': '＞', '|': '｜', '"': '＂'}

            self.set_property("filename_character_map", windows_map)
        else:
            linux_map = {'/': '|'}
            self.set_property("filename_character_map", linux_map)

    # ---------------------------- GETTERS ------------------------------------

    def get_download_submissions(self) -> str:
        # returns a stored boolean if submissions should be downloaded
        try:
            return self.get_property('download_submissions')
        except ValueError:
            return False

    def get_download_descriptions(self) -> bool:
        # returns a stored boolean if descriptions should be downloaded
        try:
            return self.get_property('download_descriptions')
        except ValueError:
            return False

    def get_download_databases(self) -> bool:
        # returns a stored boolean if databases should be downloaded
        try:
            return self.get_property('download_databases')
        except ValueError:
            return False

    def get_download_course_ids(self) -> str:
        # returns a stored list of course ids hat should be downloaded
        try:
            return self.get_property('download_course_ids')
        except ValueError:
            return []

    def get_token(self) -> str:
        # returns a stored token
        try:
            return self.get_property('token')
        except ValueError:
            raise ValueError('Not yet configured!')

    def get_moodle_domain(self) -> str:
        # returns a stored moodle_domain
        try:
            return self.get_property('moodle_domain')
        except ValueError:
            raise ValueError('Not yet configured!')

    def get_moodle_path(self) -> str:
        # returns a stored moodle_path
        try:
            return self.get_property('moodle_path')
        except ValueError:
            raise ValueError('Not yet configured!')

    def get_options_of_courses(self) -> str:
        # returns a stored dictionary of options for courses
        try:
            return self.get_property('options_of_courses')
        except ValueError:
            return {}

    def get_dont_download_course_ids(self) -> str:
        # returns a stored list of ids that should not be downloaded
        try:
            return self.get_property('dont_download_course_ids')
        except ValueError:
            return []

    def get_download_linked_files(self) -> {}:
        # returns if linked files should be downloaded
        try:
            return self.get_property('download_linked_files')
        except ValueError:
            return False

    def get_download_options(self) -> {}:
        # returns the option dictionary for downloading files
        options = {}
        try:
            options.update({'download_linked_files': self.get_property('download_linked_files')})
        except ValueError:
            options.update({'download_linked_files': False})

        try:
            options.update({'download_domains_whitelist': self.get_property('download_domains_whitelist')})
        except ValueError:
            options.update({'download_domains_whitelist': []})

        try:
            options.update({'download_domains_blacklist': self.get_property('download_domains_blacklist')})
        except ValueError:
            options.update({'download_domains_blacklist': []})

        return options

    def get_filename_character_map(self) -> {}:
        # returns the filename_character_map for PathTools
        try:
            return self.get_property('filename_character_map')
        except ValueError:
            self.set_default_filename_character_map(True)
            return self.get_property('filename_character_map')
