#!/usr/bin/env python3
"""
Comprehensive Test Runner for LLM Training Page

This script runs all test suites for the training page implementation
and generates a comprehensive test report.
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
import subprocess
from typing import Dict, List, Tuple

from utils.project_init import init_project
project_root = init_project(__file__, levels_up=2)

from utils.logger import logger

class TestRunner:
    """Comprehensive test runner for the training page"""

    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0

    def run_test_suite(self, test_path: str, test_name: str, markers: str = None) -> Dict:
        """Run a specific test suite and return results"""

        print(f"\n{'='*60}")
        print(f"Running {test_name}")
        print(f"{'='*60}")

        # Build pytest command
        cmd = ['python', '-m', 'pytest', test_path, '-v', '--tb=short']

        if markers:
            cmd.extend(['-m', markers])

        # Add coverage if available
        try:
            import coverage
            cmd.extend(['--cov=src', '--cov=webapp', '--cov-report=term-missing'])
        except ImportError:
            pass

        # Run tests
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=project_root,
                timeout=300  # 5 minute timeout per test suite
            )

            end_time = time.time()
            duration = end_time - start_time

            # Parse results
            output_lines = result.stdout.split('\n')
            error_lines = result.stderr.split('\n')

            # Extract test counts from pytest output
            passed = 0
            failed = 0
            skipped = 0
            errors = 0

            for line in output_lines:
                if 'passed' in line and 'failed' in line:
                    # Parse line like "5 passed, 2 failed, 1 skipped in 10.23s"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'passed' and i > 0:
                            passed = int(parts[i-1])
                        elif part == 'failed' and i > 0:
                            failed = int(parts[i-1])
                        elif part == 'skipped' and i > 0:
                            skipped = int(parts[i-1])
                        elif part == 'error' and i > 0:
                            errors = int(parts[i-1])

            test_result = {
                'name': test_name,
                'path': test_path,
                'duration': duration,
                'return_code': result.returncode,
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'errors': errors,
                'total': passed + failed + skipped + errors,
                'success_rate': (passed / (passed + failed + errors)) * 100 if (passed + failed + errors) > 0 else 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }

            # Update totals
            self.total_tests += test_result['total']
            self.passed_tests += passed
            self.failed_tests += failed + errors
            self.skipped_tests += skipped

            # Print summary
            print(f"\n{test_name} Results:")
            print(f"  Passed: {passed}")
            print(f"  Failed: {failed}")
            print(f"  Errors: {errors}")
            print(f"  Skipped: {skipped}")
            print(f"  Duration: {duration:.2f}s")
            print(f"  Success Rate: {test_result['success_rate']:.1f}%")

            if result.returncode != 0:
                print(f"  ⚠️  Test suite failed with return code {result.returncode}")
                if result.stderr:
                    print(f"  Error output: {result.stderr[:500]}...")
            else:
                print(f"  ✅ Test suite completed successfully")

            return test_result

        except subprocess.TimeoutExpired:
            print(f"  ❌ Test suite timed out after 5 minutes")
            return {
                'name': test_name,
                'path': test_path,
                'duration': 300,
                'return_code': -1,
                'passed': 0,
                'failed': 1,
                'skipped': 0,
                'errors': 0,
                'total': 1,
                'success_rate': 0,
                'stdout': '',
                'stderr': 'Test suite timed out'
            }

        except Exception as e:
            print(f"  ❌ Error running test suite: {e}")
            return {
                'name': test_name,
                'path': test_path,
                'duration': 0,
                'return_code': -1,
                'passed': 0,
                'failed': 1,
                'skipped': 0,
                'errors': 0,
                'total': 1,
                'success_rate': 0,
                'stdout': '',
                'stderr': str(e)
            }

    def run_all_tests(self) -> Dict:
        """Run all test suites"""

        self.start_time = time.time()

        print("🚀 Starting Comprehensive Test Suite for LLM Training Page")
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Define test suites
        test_suites = [
            {
                'path': 'tests/unit/test_training_models.py',
                'name': 'Database Models Unit Tests',
                'description': 'Test database models and relationships'
            },
            {
                'path': 'tests/unit/test_training_service.py',
                'name': 'Training Service Unit Tests',
                'description': 'Test training service functionality'
            },
            {
                'path': 'tests/unit/test_training_report_service.py',
                'name': 'Report Service Unit Tests',
                'description': 'Test report generation service'
            },
            {
                'path': 'tests/integration/test_training_integration.py',
                'name': 'Integration Tests',
                'description': 'Test service integration and workflows'
            },
            {
                'path': 'tests/system/test_training_system.py',
                'name': 'System Tests',
                'description': 'End-to-end system functionality tests'
            },
            {
                'path': 'tests/performance/test_training_performance.py',
                'name': 'Performance Tests',
                'description': 'Performance and scalability tests'
            },
            {
                'path': 'tests/security/test_training_security.py',
                'name': 'Security Tests',
                'description': 'Security and vulnerability tests'
            },
            {
                'path': 'tests/accessibility/test_training_accessibility.py',
                'name': 'Accessibility Tests',
                'description': 'Accessibility compliance tests'
            }
        ]

        # Run each test suite
        for suite in test_suites:
            if os.path.exists(suite['path']):
                result = self.run_test_suite(suite['path'], suite['name'])
                self.test_results[suite['name']] = result
            else:
                print(f"\n⚠️  Test suite not found: {suite['path']}")
                self.test_results[suite['name']] = {
                    'name': suite['name'],
                    'path': suite['path'],
                    'duration': 0,
                    'return_code': -1,
                    'passed': 0,
                    'failed': 0,
                    'skipped': 1,
                    'errors': 0,
                    'total': 1,
                    'success_rate': 0,
                    'stdout': '',
                    'stderr': 'Test file not found'
                }

        self.end_time = time.time()

        return self.generate_report()

    def generate_report(self) -> Dict:
        """Generate comprehensive test report"""

        total_duration = self.end_time - self.start_time
        overall_success_rate = (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0

        report = {
            'summary': {
                'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
                'end_time': datetime.fromtimestamp(self.end_time).isoformat(),
                'total_duration': total_duration,
                'total_tests': self.total_tests,
                'passed_tests': self.passed_tests,
                'failed_tests': self.failed_tests,
                'skipped_tests': self.skipped_tests,
                'overall_success_rate': overall_success_rate,
                'test_suites_run': len(self.test_results)
            },
            'test_suites': self.test_results,
            'requirements_coverage': self.analyze_requirements_coverage(),
            'recommendations': self.generate_recommendations()
        }

        return report

    def analyze_requirements_coverage(self) -> Dict:
        """Analyze test coverage against requirements"""

        # This would ideally parse the requirements document and map tests to requirements
        # For now, we'll provide a basic analysis based on test results

        coverage_analysis = {
            'file_upload_management': {
                'covered': self.test_results.get('System Tests', {}).get('passed', 0) > 0,
                'test_suites': ['System Tests', 'Security Tests'],
                'confidence': 'High' if self.test_results.get('System Tests', {}).get('success_rate', 0) > 80 else 'Medium'
            },
            'llm_guide_analysis': {
                'covered': self.test_results.get('Integration Tests', {}).get('passed', 0) > 0,
                'test_suites': ['Integration Tests', 'Unit Tests'],
                'confidence': 'High' if self.test_results.get('Integration Tests', {}).get('success_rate', 0) > 80 else 'Medium'
            },
            'training_configuration': {
                'covered': self.test_results.get('Training Service Unit Tests', {}).get('passed', 0) > 0,
                'test_suites': ['Training Service Unit Tests', 'System Tests'],
                'confidence': 'High' if self.test_results.get('Training Service Unit Tests', {}).get('success_rate', 0) > 80 else 'Medium'
            },
            'session_management': {
                'covered': self.test_results.get('Database Models Unit Tests', {}).get('passed', 0) > 0,
                'test_suites': ['Database Models Unit Tests', 'System Tests'],
                'confidence': 'High' if self.test_results.get('Database Models Unit Tests', {}).get('success_rate', 0) > 80 else 'Medium'
            },
            'report_generation': {
                'covered': self.test_results.get('Report Service Unit Tests', {}).get('passed', 0) > 0,
                'test_suites': ['Report Service Unit Tests', 'System Tests'],
                'confidence': 'High' if self.test_results.get('Report Service Unit Tests', {}).get('success_rate', 0) > 80 else 'Medium'
            },
            'model_testing': {
                'covered': self.test_results.get('System Tests', {}).get('passed', 0) > 0,
                'test_suites': ['System Tests', 'Integration Tests'],
                'confidence': 'Medium'  # This is complex functionality
            },
            'confidence_monitoring': {
                'covered': self.test_results.get('System Tests', {}).get('passed', 0) > 0,
                'test_suites': ['System Tests', 'Unit Tests'],
                'confidence': 'Medium'
            },
            'security_file_management': {
                'covered': self.test_results.get('Security Tests', {}).get('passed', 0) > 0,
                'test_suites': ['Security Tests', 'System Tests'],
                'confidence': 'High' if self.test_results.get('Security Tests', {}).get('success_rate', 0) > 80 else 'Medium'
            },
            'accessibility': {
                'covered': self.test_results.get('Accessibility Tests', {}).get('passed', 0) > 0,
                'test_suites': ['Accessibility Tests'],
                'confidence': 'High' if self.test_results.get('Accessibility Tests', {}).get('success_rate', 0) > 80 else 'Medium'
            },
            'performance': {
                'covered': self.test_results.get('Performance Tests', {}).get('passed', 0) > 0,
                'test_suites': ['Performance Tests'],
                'confidence': 'Medium'  # Performance testing is inherently variable
            }
        }

        return coverage_analysis

    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""

        recommendations = []

        # Overall success rate recommendations
        if self.total_tests == 0:
            recommendations.append("❌ No tests were executed. Ensure test files exist and are properly configured.")
        elif overall_success_rate := (self.passed_tests / self.total_tests) * 100 < 80:
            recommendations.append(f"⚠️  Overall success rate is {overall_success_rate:.1f}%. Aim for >90% success rate.")

        # Individual test suite recommendations
        for suite_name, results in self.test_results.items():
            if results['return_code'] != 0:
                recommendations.append(f"❌ {suite_name} failed to run properly. Check test configuration and dependencies.")
            elif results['success_rate'] < 80:
                recommendations.append(f"⚠️  {suite_name} has low success rate ({results['success_rate']:.1f}%). Review failing tests.")
            elif results['total'] == 0:
                recommendations.append(f"⚠️  {suite_name} has no tests. Consider adding test cases.")

        # Performance recommendations
        perf_results = self.test_results.get('Performance Tests', {})
        if perf_results.get('failed', 0) > 0:
            recommendations.append("🐌 Performance tests are failing. Review system performance and optimize bottlenecks.")

        # Security recommendations
        sec_results = self.test_results.get('Security Tests', {})
        if sec_results.get('failed', 0) > 0:
            recommendations.append("🔒 Security tests are failing. Address security vulnerabilities immediately.")

        # Accessibility recommendations
        acc_results = self.test_results.get('Accessibility Tests', {})
        if acc_results.get('failed', 0) > 0:
            recommendations.append("♿ Accessibility tests are failing. Improve accessibility compliance.")

        # General recommendations
        if self.failed_tests == 0 and self.total_tests > 0:
            recommendations.append("✅ All tests are passing! Consider adding more edge case tests.")

        if not recommendations:
            recommendations.append("✅ Test suite is in good shape. Continue monitoring and adding tests as features evolve.")

        return recommendations

    def print_final_report(self, report: Dict):
        """Print final test report"""

        print(f"\n{'='*80}")
        print("🎯 COMPREHENSIVE TEST REPORT - LLM TRAINING PAGE")
        print(f"{'='*80}")

        summary = report['summary']
        print(f"\n📊 SUMMARY")
        print(f"  Start Time: {summary['start_time']}")
        print(f"  End Time: {summary['end_time']}")
        print(f"  Total Duration: {summary['total_duration']:.2f} seconds")
        print(f"  Test Suites Run: {summary['test_suites_run']}")
        print(f"  Total Tests: {summary['total_tests']}")
        print(f"  Passed: {summary['passed_tests']} ✅")
        print(f"  Failed: {summary['failed_tests']} ❌")
        print(f"  Skipped: {summary['skipped_tests']} ⏭️")
        print(f"  Overall Success Rate: {summary['overall_success_rate']:.1f}%")

        print(f"\n📋 TEST SUITE DETAILS")
        for suite_name, results in report['test_suites'].items():
            status = "✅" if results['return_code'] == 0 and results['failed'] == 0 else "❌"
            print(f"  {status} {suite_name}")
            print(f"    Duration: {results['duration']:.2f}s")
            print(f"    Tests: {results['total']} (P:{results['passed']}, F:{results['failed']}, S:{results['skipped']})")
            print(f"    Success Rate: {results['success_rate']:.1f}%")

        print(f"\n🎯 REQUIREMENTS COVERAGE")
        coverage = report['requirements_coverage']
        for req_name, req_info in coverage.items():
            status = "✅" if req_info['covered'] else "❌"
            confidence = req_info['confidence']
            print(f"  {status} {req_name.replace('_', ' ').title()} ({confidence} confidence)")

        print(f"\n💡 RECOMMENDATIONS")
        for recommendation in report['recommendations']:
            print(f"  {recommendation}")

        print(f"\n{'='*80}")

        # Overall assessment
        if summary['overall_success_rate'] >= 90:
            print("🎉 EXCELLENT: Test suite is in excellent condition!")
        elif summary['overall_success_rate'] >= 80:
            print("👍 GOOD: Test suite is in good condition with room for improvement.")
        elif summary['overall_success_rate'] >= 60:
            print("⚠️  NEEDS ATTENTION: Test suite needs significant improvement.")
        else:
            print("🚨 CRITICAL: Test suite requires immediate attention!")

        print(f"{'='*80}")

    def save_report(self, report: Dict, filename: str = None):
        """Save test report to file"""

        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'test_report_{timestamp}.json'

        report_path = Path('tests') / 'reports' / filename
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"\n📄 Test report saved to: {report_path}")

        # Also save a human-readable version
        txt_filename = filename.replace('.json', '.txt')
        txt_path = report_path.parent / txt_filename

        with open(txt_path, 'w') as f:
            f.write("COMPREHENSIVE TEST REPORT - LLM TRAINING PAGE\n")
            f.write("=" * 80 + "\n\n")

            summary = report['summary']
            f.write("SUMMARY\n")
            f.write(f"Start Time: {summary['start_time']}\n")
            f.write(f"End Time: {summary['end_time']}\n")
            f.write(f"Total Duration: {summary['total_duration']:.2f} seconds\n")
            f.write(f"Test Suites Run: {summary['test_suites_run']}\n")
            f.write(f"Total Tests: {summary['total_tests']}\n")
            f.write(f"Passed: {summary['passed_tests']}\n")
            f.write(f"Failed: {summary['failed_tests']}\n")
            f.write(f"Skipped: {summary['skipped_tests']}\n")
            f.write(f"Overall Success Rate: {summary['overall_success_rate']:.1f}%\n\n")

            f.write("TEST SUITE DETAILS\n")
            for suite_name, results in report['test_suites'].items():
                f.write(f"{suite_name}:\n")
                f.write(f"  Duration: {results['duration']:.2f}s\n")
                f.write(f"  Tests: {results['total']} (Passed: {results['passed']}, Failed: {results['failed']}, Skipped: {results['skipped']})\n")
                f.write(f"  Success Rate: {results['success_rate']:.1f}%\n")
                f.write(f"  Return Code: {results['return_code']}\n\n")

            f.write("RECOMMENDATIONS\n")
            for recommendation in report['recommendations']:
                f.write(f"- {recommendation}\n")

        print(f"📄 Human-readable report saved to: {txt_path}")

def main():
    """Main function to run comprehensive tests"""

    # Check if we're in the right directory
    if not os.path.exists('webapp') or not os.path.exists('src'):
        print("❌ Please run this script from the project root directory")
        sys.exit(1)

    # Create test runner
    runner = TestRunner()

    try:
        # Run all tests
        report = runner.run_all_tests()

        # Print final report
        runner.print_final_report(report)

        # Save report
        runner.save_report(report)

        # Exit with appropriate code
        if report['summary']['failed_tests'] > 0:
            sys.exit(1)  # Exit with error if any tests failed
        else:
            sys.exit(0)  # Exit successfully

    except KeyboardInterrupt:
        print("\n\n⏹️  Test execution interrupted by user")
        sys.exit(130)

    except Exception as e:
        print(f"\n\n❌ Error running comprehensive tests: {e}")
        logger.error(f"Comprehensive test execution failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()