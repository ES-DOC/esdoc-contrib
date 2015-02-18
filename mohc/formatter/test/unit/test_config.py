import os
import shutil
import tempfile
import unittest

import config


class TestConfig(unittest.TestCase):

    def setUp(self):
        self.base_dir = tempfile.mkdtemp()
        self.parser = config.FormatConfig(self.base_dir)
        self.config_path = os.path.join(self.base_dir, "format.cfg")
        fh = open(self.config_path, "w")
        fh.write("""[global]
institute: mohc

[database]
dbname: crememma
host: hal9000
user: dave
""")
        fh.close()

    def tearDown(self):
        shutil.rmtree(self.base_dir)

    def test_config_path(self):
        self.assertEqual(self.parser.config_path(), self.config_path)

    def test_default_config_path(self):
        base_dir = os.path.dirname(config.__file__)
        expected = os.path.join(base_dir, "..", "etc", "format.cfg")
        default = config.FormatConfig()
        self.assertEqual(default.config_path(), expected)

    def test_read_config(self):
        cfg = self.parser.read_config()
        self.assertEqual(len(cfg), 2)
        self.assertIn("database", cfg)
        self.assertEqual(cfg["database"]["host"], "hal9000")


if __name__ == "__main__":
    unittest.main()
