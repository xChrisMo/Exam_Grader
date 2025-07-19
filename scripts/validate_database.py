#!/usr/bin/env python3
"""Database validation script for the Exam Grader application.

This script validates the database schema, indexes, constraints, and performance
optimizations to ensure everything is properly configured.
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.optimization_utils import DatabaseOptimizer
from src.config.unified_config import Config


def validate_database(database_url: str, verbose: bool = False) -> dict:
    """Validate database configuration and optimizations.
    
    Args:
        database_url: Database connection URL
        verbose: Whether to show detailed output
        
    Returns:
        Dictionary containing validation results
    """
    optimizer = DatabaseOptimizer(database_url)
    
    print("🔍 Validating database configuration...")
    print("=" * 50)
    
    # Generate comprehensive report
    report = optimizer.generate_optimization_report()
    
    # Validation results
    validation_results = {
        'timestamp': datetime.utcnow().isoformat(),
        'database_url': database_url,
        'overall_status': 'PASS',
        'issues': [],
        'warnings': [],
        'recommendations': [],
        'statistics': {
            'total_indexes': len(report['indexes']['existing']),
            'missing_indexes': len(report['indexes']['missing']),
            'total_foreign_keys': len(report['foreign_keys']['existing']),
            'missing_foreign_keys': len(report['foreign_keys']['missing']),
            'total_constraints': len(report['constraints']['existing']),
            'missing_constraints': len(report['constraints']['missing']),
            'total_views': len(report['views']['existing']),
            'missing_views': len(report['views']['missing'])
        }
    }
    
    # Check indexes
    print("📊 Index Validation:")
    if report['indexes']['existing']:
        print(f"  ✅ Found {len(report['indexes']['existing'])} indexes")
        if verbose:
            for idx in report['indexes']['existing']:
                print(f"    - {idx}")
    
    if report['indexes']['missing']:
        print(f"  ❌ Missing {len(report['indexes']['missing'])} indexes")
        validation_results['overall_status'] = 'FAIL'
        for idx in report['indexes']['missing']:
            print(f"    - {idx}")
            validation_results['issues'].append(f"Missing index: {idx}")
    
    # Check foreign keys
    print("\n🔗 Foreign Key Validation:")
    if report['foreign_keys']['existing']:
        print(f"  ✅ Found {len(report['foreign_keys']['existing'])} foreign keys")
        if verbose:
            for fk in report['foreign_keys']['existing']:
                print(f"    - {fk}")
    
    if report['foreign_keys']['missing']:
        print(f"  ❌ Missing {len(report['foreign_keys']['missing'])} foreign keys")
        validation_results['overall_status'] = 'FAIL'
        for fk in report['foreign_keys']['missing']:
            print(f"    - {fk}")
            validation_results['issues'].append(f"Missing foreign key: {fk}")
    
    # Check constraints
    print("\n🛡️  Constraint Validation:")
    if report['constraints']['existing']:
        print(f"  ✅ Found {len(report['constraints']['existing'])} validation triggers")
        if verbose:
            for constraint in report['constraints']['existing']:
                print(f"    - {constraint}")
    
    if report['constraints']['missing']:
        print(f"  ⚠️  Missing {len(report['constraints']['missing'])} validation triggers")
        if validation_results['overall_status'] != 'FAIL':
            validation_results['overall_status'] = 'WARNING'
        for constraint in report['constraints']['missing']:
            print(f"    - {constraint}")
            validation_results['warnings'].append(f"Missing constraint: {constraint}")
    
    # Check views
    print("\n📈 Performance View Validation:")
    if report['views']['existing']:
        print(f"  ✅ Found {len(report['views']['existing'])} performance views")
        if verbose:
            for view in report['views']['existing']:
                print(f"    - {view}")
    
    if report['views']['missing']:
        print(f"  ⚠️  Missing {len(report['views']['missing'])} performance views")
        if validation_results['overall_status'] not in ['FAIL', 'WARNING']:
            validation_results['overall_status'] = 'INFO'
        for view in report['views']['missing']:
            print(f"    - {view}")
            validation_results['warnings'].append(f"Missing view: {view}")
    
    # Add recommendations
    validation_results['recommendations'] = report['recommendations']
    
    # Summary
    print("\n" + "=" * 50)
    if validation_results['overall_status'] == 'PASS':
        print("🎉 Database validation PASSED! All optimizations are in place.")
    elif validation_results['overall_status'] == 'WARNING':
        print("⚠️  Database validation completed with WARNINGS.")
    elif validation_results['overall_status'] == 'INFO':
        print("ℹ️  Database validation completed with minor issues.")
    else:
        print("❌ Database validation FAILED! Critical issues found.")
    
    print(f"\nStatistics:")
    stats = validation_results['statistics']
    print(f"  - Indexes: {stats['total_indexes']} (missing: {stats['missing_indexes']})")
    print(f"  - Foreign Keys: {stats['total_foreign_keys']} (missing: {stats['missing_foreign_keys']})")
    print(f"  - Constraints: {stats['total_constraints']} (missing: {stats['missing_constraints']})")
    print(f"  - Views: {stats['total_views']} (missing: {stats['missing_views']})")
    
    return validation_results


def test_database_performance(database_url: str) -> dict:
    """Run basic performance tests on the database.
    
    Args:
        database_url: Database connection URL
        
    Returns:
        Dictionary containing performance test results
    """
    from sqlalchemy import create_engine, text
    import time
    
    print("\n🚀 Running performance tests...")
    print("=" * 50)
    
    engine = create_engine(database_url)
    performance_results = {
        'timestamp': datetime.utcnow().isoformat(),
        'tests': []
    }
    
    # Test queries with timing
    test_queries = [
        {
            'name': 'User lookup by username',
            'query': "SELECT * FROM users WHERE username = 'admin' LIMIT 1",
            'expected_time': 0.01  # 10ms
        },
        {
            'name': 'Active users count',
            'query': "SELECT COUNT(*) FROM users WHERE is_active = 1",
            'expected_time': 0.05  # 50ms
        },
        {
            'name': 'Recent submissions',
            'query': "SELECT * FROM submissions ORDER BY created_at DESC LIMIT 10",
            'expected_time': 0.02  # 20ms
        },
        {
            'name': 'Grading results with mappings',
            'query': """SELECT gr.*, m.match_score 
                       FROM grading_results gr 
                       JOIN mappings m ON gr.mapping_id = m.id 
                       LIMIT 5""",
            'expected_time': 0.03  # 30ms
        }
    ]
    
    try:
        with engine.connect() as conn:
            for test in test_queries:
                start_time = time.time()
                try:
                    result = conn.execute(text(test['query']))
                    rows = result.fetchall()
                    end_time = time.time()
                    
                    execution_time = end_time - start_time
                    status = "PASS" if execution_time <= test['expected_time'] else "SLOW"
                    
                    test_result = {
                        'name': test['name'],
                        'execution_time': execution_time,
                        'expected_time': test['expected_time'],
                        'status': status,
                        'row_count': len(rows)
                    }
                    
                    performance_results['tests'].append(test_result)
                    
                    status_icon = "✅" if status == "PASS" else "⚠️"
                    print(f"  {status_icon} {test['name']}: {execution_time:.4f}s (expected: <{test['expected_time']}s)")
                    
                except Exception as e:
                    test_result = {
                        'name': test['name'],
                        'execution_time': None,
                        'expected_time': test['expected_time'],
                        'status': 'ERROR',
                        'error': str(e)
                    }
                    performance_results['tests'].append(test_result)
                    print(f"  ❌ {test['name']}: ERROR - {str(e)}")
    
    except Exception as e:
        print(f"❌ Performance testing failed: {str(e)}")
        performance_results['error'] = str(e)
    
    return performance_results


def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(description='Validate Exam Grader database')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    parser.add_argument('--performance', '-p', action='store_true', help='Run performance tests')
    parser.add_argument('--output', '-o', help='Output results to JSON file')
    parser.add_argument('--database-url', help='Override database URL')
    
    args = parser.parse_args()
    
    # Get database URL
    if args.database_url:
        database_url = args.database_url
    else:
        config = Config()
        database_url = config.get_database_url()
    
    print("🔍 Exam Grader Database Validation")
    print("=" * 50)
    print(f"Database: {database_url}")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print()
    
    # Run validation
    validation_results = validate_database(database_url, args.verbose)
    
    # Run performance tests if requested
    performance_results = None
    if args.performance:
        performance_results = test_database_performance(database_url)
    
    # Combine results
    final_results = {
        'validation': validation_results,
        'performance': performance_results
    }
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(final_results, f, indent=2, default=str)
        print(f"\n📄 Results saved to: {args.output}")
    
    # Exit with appropriate code
    if validation_results['overall_status'] == 'FAIL':
        sys.exit(1)
    elif validation_results['overall_status'] in ['WARNING', 'INFO']:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()