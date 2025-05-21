"""
Unit tests for exampleUse.py (import and docstring only)

This test ensures that exampleUse.py can be imported and contains a module docstring.
"""
import unittest
import importlib.util
import os

class TestExampleUseImport(unittest.TestCase):
    def test_import_and_docstring(self):
        path = os.path.join(os.path.dirname(__file__), '../src/exampleUse.py')
        spec = importlib.util.spec_from_file_location('exampleUse', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(module.__doc__ is not None)

if __name__ == "__main__":
    unittest.main()
