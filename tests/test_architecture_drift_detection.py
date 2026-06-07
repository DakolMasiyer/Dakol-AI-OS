import unittest
import subprocess
import os

class ArchitectureDriftDetectionTests(unittest.TestCase):
    
    def test_no_illegal_learning_imports(self):
        # TEST: Detect hidden imports/coupling
        # Run the freeze_check.py script which scans the codebase
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        script_path = os.path.join(base_dir, "scripts", "freeze_check.py")
        
        # Execute the freeze check
        result = subprocess.run(
            ["python3", script_path],
            cwd=base_dir,
            capture_output=True,
            text=True
        )
        
        # Expecting exit code 0 if architecture is frozen
        self.assertEqual(
            result.returncode, 0, 
            f"Architecture drift detected! Output:\n{result.stdout}\n{result.stderr}"
        )

if __name__ == "__main__":
    unittest.main()
