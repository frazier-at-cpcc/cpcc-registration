import requests
import csv
import time

API_URL = "http://localhost:8001/api/v1/enrollment"
CSV_FILE = "Active and Dropped student counts by section and delivery method.csv"

def read_csv_sections():
    """Read CSV and extract section names."""
    sections = set()
    with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            section_name = row.get('Section Name', '').strip()
            if section_name and '-' in section_name:
                sections.add(section_name)
    return sections

def test_api():
    print("Reading CSV...")
    csv_sections = read_csv_sections()
    print(f"CSV contains {len(csv_sections)} sections\n")
    
    # Test with term=None (should search all terms)
    print("Testing API with no term parameter (multi-term search)...")
    start = time.time()
    
    # Invalidate cache first
    try:
        requests.post(f"{API_URL}/cache/invalidate")
    except:
        pass
    
    # Get subjects from CSV
    subjects = set(s.split('-')[0] for s in csv_sections)
    subjects_str = ','.join(sorted(subjects))
    
    print(f"Requesting subjects: {subjects_str}\n")
    
    response = requests.get(
        f"{API_URL}?subjects={subjects_str}&use_cache=false"
    )
    
    elapsed = time.time() - start
    
    if response.status_code != 200:
        print(f"❌ API Error: {response.status_code}")
        print(response.text)
        return
    
    data = response.json()
    api_sections = set(s['section_number'] for s in data['sections'])
    
    print(f"API returned {len(api_sections)} sections in {elapsed:.1f}s")
    print(f"Processing time: {data.get('processing_time_seconds')}s\n")
    
    # Compare
    missing = csv_sections - api_sections
    extra = api_sections - csv_sections
    
    print("="*60)
    print("RESULTS")
    print("="*60)
    print(f"CSV sections: {len(csv_sections)}")
    print(f"API sections: {len(api_sections)}")
    print(f"Matched: {len(csv_sections & api_sections)}")
    print(f"Missing from API: {len(missing)}")
    print(f"Extra in API: {len(extra)}")
    
    if missing:
        print(f"\n❌ Missing sections (first 20):")
        for section in sorted(list(missing))[:20]:
            print(f"  - {section}")
        if len(missing) > 20:
            print(f"  ... and {len(missing) - 20} more")
    else:
        print("\n✅ ALL CSV SECTIONS FOUND IN API!")
    
    # Show subject breakdown
    subjects_found = {}
    for section in data['sections']:
        subj = section.get('subject_code', '')
        subjects_found[subj] = subjects_found.get(subj, 0) + 1
    
    print(f"\nSubjects found:")
    for subj, count in sorted(subjects_found.items()):
        print(f"  {subj}: {count} sections")

if __name__ == "__main__":
    test_api()
