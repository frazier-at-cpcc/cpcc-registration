#!/usr/bin/env python3
"""Compare CSV sections with API results to find missing courses."""

import csv
import json
from collections import defaultdict

# Load CSV data
csv_sections = set()
csv_by_subject = defaultdict(set)
csv_courses = defaultdict(set)  # subject -> course numbers

with open("Active and Dropped student counts by section and delivery method.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        section_name = row["Section Name"].strip()
        csv_sections.add(section_name)
        # Extract subject code (everything before first hyphen)
        parts = section_name.split("-")
        if len(parts) >= 2:
            subject = parts[0]
            course_num = parts[1] if len(parts) > 1 else ""
            csv_by_subject[subject].add(section_name)
            csv_courses[subject].add(course_num)

# Load API data
with open("/tmp/api_response.json", "r") as f:
    api_data = json.load(f)

api_sections = set()
api_by_subject = defaultdict(set)
api_courses = defaultdict(set)

# Filter to Spring 2026 term only to match CSV
for section in api_data.get("sections", []):
    section_name = section.get("section_number", "")
    term = section.get("term", "")

    # Only look at Spring 2026 (current term that matches CSV)
    if "Spring 2026" in term:
        api_sections.add(section_name)
        subject = section.get("subject_code", "")
        course_num = section.get("course_number", "")
        api_by_subject[subject].add(section_name)
        api_courses[subject].add(course_num)

print("=" * 80)
print("CSV vs API Comparison (Spring 2026 Term)")
print("=" * 80)

print(f"\nTotal CSV sections: {len(csv_sections)}")
print(f"Total API sections (Spring 2026): {len(api_sections)}")

# Find sections in CSV but not in API
missing_from_api = csv_sections - api_sections
print(f"\nSections in CSV but NOT in API: {len(missing_from_api)}")

# Group missing by subject
missing_by_subject = defaultdict(list)
for section in sorted(missing_from_api):
    parts = section.split("-")
    if len(parts) >= 1:
        subject = parts[0]
        missing_by_subject[subject].append(section)

print("\n" + "-" * 80)
print("Missing sections by subject:")
print("-" * 80)

for subject in sorted(missing_by_subject.keys()):
    sections = missing_by_subject[subject]
    print(f"\n{subject} ({len(sections)} missing):")
    for s in sorted(sections)[:10]:  # Show first 10
        print(f"  - {s}")
    if len(sections) > 10:
        print(f"  ... and {len(sections) - 10} more")

# Also check for missing courses (not just sections)
print("\n" + "=" * 80)
print("Missing COURSES by subject (courses in CSV but not in API for Spring 2026):")
print("=" * 80)

for subject in sorted(csv_courses.keys()):
    csv_course_nums = csv_courses[subject]
    api_course_nums = api_courses.get(subject, set())
    missing_courses = csv_course_nums - api_course_nums
    if missing_courses:
        print(f"\n{subject}: Missing course numbers: {sorted(missing_courses)}")
        # Show example sections for these missing courses
        for course_num in sorted(missing_courses):
            examples = [s for s in csv_by_subject[subject] if f"-{course_num}-" in s][:3]
            print(f"  Course {subject}-{course_num}: {examples}")

# Show what's in API but not CSV (extra sections - might be different terms)
extra_in_api = api_sections - csv_sections
print(f"\n\nSections in API (Spring 2026) but not in CSV: {len(extra_in_api)}")
if extra_in_api:
    for s in sorted(list(extra_in_api))[:10]:
        print(f"  - {s}")
