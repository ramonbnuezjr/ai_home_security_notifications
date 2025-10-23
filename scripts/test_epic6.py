#!/usr/bin/env python3
"""
Epic 6 Test Runner
Runs all unit and integration tests for Epic 6: Security & Privacy Controls
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import unittest
import logging
from datetime import datetime
import json

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Suppress info logs during tests
    format='%(levelname)s - %(message)s'
)

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text):
    """Print formatted header"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'=' * 80}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{text:^80}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'=' * 80}{Colors.END}\n")


def print_section(text):
    """Print formatted section"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{text}{Colors.END}")
    print(f"{Colors.BLUE}{'-' * len(text)}{Colors.END}")


def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def run_test_suite(suite_name, test_path):
    """Run a test suite and return results"""
    print_section(f"Running {suite_name}")
    
    # Discover and run tests
    loader = unittest.TestLoader()
    suite = loader.discover(test_path, pattern='test_*.py')
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{Colors.BOLD}Results for {suite_name}:{Colors.END}")
    print(f"  Tests run: {result.testsRun}")
    print_success(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    
    if result.failures:
        print_error(f"Failures: {len(result.failures)}")
    if result.errors:
        print_error(f"Errors: {len(result.errors)}")
    if result.skipped:
        print_warning(f"Skipped: {len(result.skipped)}")
    
    return result


def run_cli_tests():
    """Run CLI functionality tests"""
    print_section("Testing Epic 6 CLI")
    
    cli_tests = []
    
    # Test 1: CLI help
    print("Testing CLI help...")
    exit_code = os.system(f"cd {project_root} && python scripts/epic6_cli.py --help > /dev/null 2>&1")
    cli_tests.append(("CLI Help", exit_code == 0))
    
    # Test 2: Version command
    print("Testing version command...")
    exit_code = os.system(f"cd {project_root} && python scripts/epic6_cli.py version > /dev/null 2>&1")
    cli_tests.append(("Version Command", exit_code == 0))
    
    # Test 3: Status command
    print("Testing status command...")
    exit_code = os.system(f"cd {project_root} && python scripts/epic6_cli.py status --config config/system_config.yaml > /dev/null 2>&1")
    cli_tests.append(("Status Command", exit_code == 0))
    
    # Test 4: Encryption init
    print("Testing encryption init...")
    test_key_file = "/tmp/test_epic6_key"
    if os.path.exists(test_key_file):
        os.unlink(test_key_file)
    exit_code = os.system(f"cd {project_root} && python scripts/epic6_cli.py encryption init --key-file {test_key_file} > /dev/null 2>&1")
    cli_tests.append(("Encryption Init", exit_code == 0 and os.path.exists(test_key_file)))
    if os.path.exists(test_key_file):
        os.unlink(test_key_file)
    
    # Print results
    print(f"\n{Colors.BOLD}CLI Test Results:{Colors.END}")
    passed = 0
    for test_name, success in cli_tests:
        if success:
            print_success(test_name)
            passed += 1
        else:
            print_error(test_name)
    
    print(f"\nCLI Tests: {passed}/{len(cli_tests)} passed")
    
    return passed == len(cli_tests)


def generate_test_report(results, cli_success, start_time, end_time):
    """Generate test report"""
    duration = (end_time - start_time).total_seconds()
    
    # Calculate totals
    total_tests = sum(r.testsRun for r in results.values())
    total_failures = sum(len(r.failures) for r in results.values())
    total_errors = sum(len(r.errors) for r in results.values())
    total_skipped = sum(len(r.skipped) for r in results.values())
    total_passed = total_tests - total_failures - total_errors - total_skipped
    
    print_header("EPIC 6 TEST REPORT")
    
    print(f"{Colors.BOLD}Test Execution Summary{Colors.END}")
    print(f"  Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Duration: {duration:.2f} seconds")
    print()
    
    print(f"{Colors.BOLD}Overall Results{Colors.END}")
    print(f"  Total Tests: {total_tests}")
    print_success(f"Passed: {total_passed} ({total_passed/total_tests*100:.1f}%)")
    
    if total_failures > 0:
        print_error(f"Failures: {total_failures}")
    if total_errors > 0:
        print_error(f"Errors: {total_errors}")
    if total_skipped > 0:
        print_warning(f"Skipped: {total_skipped}")
    
    print()
    print(f"{Colors.BOLD}Test Suite Breakdown{Colors.END}")
    
    for suite_name, result in results.items():
        status = "✓ PASS" if result.wasSuccessful() else "✗ FAIL"
        color = Colors.GREEN if result.wasSuccessful() else Colors.RED
        print(f"  {color}{status}{Colors.END} {suite_name}: {result.testsRun} tests")
    
    cli_status = "✓ PASS" if cli_success else "✗ FAIL"
    cli_color = Colors.GREEN if cli_success else Colors.RED
    print(f"  {cli_color}{cli_status}{Colors.END} CLI Tests")
    
    print()
    
    # Overall status
    all_passed = all(r.wasSuccessful() for r in results.values()) and cli_success
    
    if all_passed:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 ALL EPIC 6 TESTS PASSED! 🎉{Colors.END}")
        print(f"{Colors.GREEN}Epic 6: Security & Privacy Controls is ready for deployment!{Colors.END}")
    else:
        print(f"{Colors.RED}{Colors.BOLD}⚠ SOME TESTS FAILED{Colors.END}")
        print(f"{Colors.RED}Please review the failures above and fix issues before deployment.{Colors.END}")
    
    print()
    
    return all_passed


def main():
    """Main test runner"""
    print_header("EPIC 6: SECURITY & PRIVACY CONTROLS - TEST SUITE")
    
    print(f"{Colors.BOLD}Testing Components:{Colors.END}")
    print("  • Authentication Service (JWT, MFA, Sessions)")
    print("  • Encryption Service (Data-at-rest, TLS)")
    print("  • Privacy Service (GDPR, Data Export/Deletion)")
    print("  • Integration Tests (Complete Workflows)")
    print("  • CLI Tool")
    print()
    
    start_time = datetime.now()
    results = {}
    
    # Run unit tests
    print_header("UNIT TESTS")
    
    unit_test_dir = project_root / "tests" / "unit"
    if unit_test_dir.exists():
        result = run_test_suite("Unit Tests", str(unit_test_dir))
        results['Unit Tests'] = result
    else:
        print_error("Unit test directory not found")
        return 1
    
    # Run integration tests
    print_header("INTEGRATION TESTS")
    
    integration_test_dir = project_root / "tests" / "integration"
    if integration_test_dir.exists():
        result = run_test_suite("Integration Tests", str(integration_test_dir))
        results['Integration Tests'] = result
    else:
        print_error("Integration test directory not found")
        return 1
    
    # Run CLI tests
    print_header("CLI TESTS")
    cli_success = run_cli_tests()
    
    # Generate report
    end_time = datetime.now()
    all_passed = generate_test_report(results, cli_success, start_time, end_time)
    
    # Save detailed report
    report_file = project_root / "tests" / "epic6_test_report.json"
    report_data = {
        'timestamp': start_time.isoformat(),
        'duration_seconds': (end_time - start_time).total_seconds(),
        'summary': {
            'total_tests': sum(r.testsRun for r in results.values()),
            'passed': sum(r.testsRun - len(r.failures) - len(r.errors) - len(r.skipped) for r in results.values()),
            'failed': sum(len(r.failures) for r in results.values()),
            'errors': sum(len(r.errors) for r in results.values()),
            'skipped': sum(len(r.skipped) for r in results.values()),
            'cli_passed': cli_success
        },
        'suites': {
            name: {
                'tests_run': r.testsRun,
                'failures': len(r.failures),
                'errors': len(r.errors),
                'skipped': len(r.skipped),
                'success': r.wasSuccessful()
            }
            for name, r in results.items()
        },
        'all_passed': all_passed
    }
    
    with open(report_file, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"\n{Colors.BOLD}Detailed report saved to: {report_file}{Colors.END}\n")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())

