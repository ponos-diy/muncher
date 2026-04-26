import os
import datetime
import logging

class BackupSave:
    def __init__(self, folder, basename, validator, max_tries=3, num_keep=5):
        self.folder = folder
        self.basename = basename
        self.validator = validator
        self.max_tries = max_tries
        self.num_keep = num_keep
        self._logger = logging.getLogger(__name__)
        self._ensure_dir(folder)

    def _ensure_dir(self, dirname):
        if not os.path.exists(dirname):
            self._logger.warning(f"directory {dirname} does not exist, creating it")
            os.makedirs(dirname)

    def _save(self, filename, data):
        self._logger.debug(f"saving to {filename}")
        with open(filename, "w") as f:
            f.write(data)
        self._logger.debug(f"saved to {filename}")

    def _load(self, filename):
        self._logger.debug(f"loading {filename}")
        try:
            with open(filename, "r") as f:
                data = f.read()
            result = self.validator(data)
            self._logger.info(f"loaded data from {filename}")
            return result
        except (RuntimeError, FileNotFoundError) as e:
            self._logger.warning(f"unable to load from {filename}: {e}")
            return None


    def _get_timestamp_file(self):
        return os.path.join(self.folder, f"{self.basename}_{datetime.datetime.now().isoformat()}")

    def _get_current_file(self):
        return os.path.join(self.folder, self.basename)

    def save(self, data):
        timestamp_file = self._get_timestamp_file()
        self._save(timestamp_file, data)
        self._load(timestamp_file)
        self._save(self._get_current_file(), data)
        self._cleanup()

    def _get_backup_files_in_order(self):
        return sorted((f for f in os.listdir(self.folder) if f.startswith(self.basename) and f != self.basename))

    def _cleanup(self):
        files = self._get_backup_files_in_order()
        for f in files[:-self.num_keep]:
            self._logger.debug(f"deleting {f}")
            os.remove(os.path.join(self.folder, f))


    def load(self):
        current = self._load(self._get_current_file())
        if current is not None:
            return current
        files = list(reversed(self._get_backup_files_in_order()))
        for i in range(min(self.max_tries, len(files))):
            data = self._load(os.path.join(self.folder, files[i]))
            if data is not None:
                return data
        else:
            raise RuntimeError(f"unable to load data from first {self.max_tries} backups, giving up")




