import json
import argparse


def generate_coverage_report(json_file):
    with open(json_file, 'r') as file:
        data = json.load(file)

    files = data['files']
    totals = data['totals']

    table = "| File | Covered Lines | Total Statements | Coverage (%) |\n"
    table += "|------|---------------|------------------|--------------|\n"

    for file, summary in files.items():
        table += f"| {file} | {summary['summary']['covered_lines']} | {summary['summary']['num_statements']} | {summary['summary']['percent_covered_display']}% |\n"

    table += f"| **Total** | **{totals['covered_lines']}** | **{totals['num_statements']}** | **{totals['percent_covered_display']}%** |\n"

    return table, totals['percent_covered']


def generate_badge_url(coverage: float):
    if coverage < 70:
        color = 'red'
    elif coverage < 80:
        color = 'orange'
    else:
        color = 'green'
    return f"https://img.shields.io/badge/Coverage-{coverage:.2f}%25-{color}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate a markdown table for the coverage report summaries.')
    parser.add_argument('json_file', type=str, help='Path to the JSON file containing the coverage report')
    args = parser.parse_args()

    report, coverage = generate_coverage_report(args.json_file)
    badge_url = generate_badge_url(coverage)

    print(f"![Coverage]({badge_url})")
    print()
    print(report)
