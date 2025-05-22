import importlib
import sys
import traceback
from pathlib import Path

def run_test_module(module_name):
    try:
        mod = importlib.import_module(module_name)
        if hasattr(mod, 'main'):
            print(f"\n===== Running {module_name} =====")
            mod.main()
            print(f"===== {module_name} PASSED =====\n")
            return True
        else:
            print(f"No main() in {module_name}")
            return False
    except Exception as e:
        print(f"===== {module_name} FAILED =====")
        traceback.print_exc()
        return False

def main():
    test_dir = Path(__file__).parent
    test_files = sorted(test_dir.glob('test_*.py'))
    results = {}
    for test_file in test_files:
        if test_file.name == 'test_all.py':
            continue
        module_name = f"tests.{test_file.stem}"
        result = run_test_module(module_name)
        results[test_file.name] = result
    print("\n===== TEST SUMMARY =====")
    for name, passed in results.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
    if all(results.values()):
        print("\nALL TESTS PASSED")
        sys.exit(0)
    else:
        print("\nSOME TESTS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main() 