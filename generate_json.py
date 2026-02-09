import csv
import json
from pathlib import Path

def read_csv_files(districts_folder):
    """Read all Maharashtra CSV files and return consolidated data."""
    all_vendors = []
    
    for file in Path(districts_folder).glob("MAHARASHTRA_*.csv"):
        district_name = file.stem.replace("MAHARASHTRA_", "").replace("_", " ")
        
        with open(file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    vendor = {
                        'id': len(all_vendors) + 1,
                        'district': district_name,
                        'company': row.get('company_name', ''),
                        'email': row.get('email', ''),
                        'phone': row.get('phone', ''),
                        'installations': int(row.get('installations', 0)),
                        'capacity': float(row.get('capacity_kwp', 0))
                    }
                    all_vendors.append(vendor)
                except (ValueError, KeyError):
                    continue
    
    return sorted(all_vendors, key=lambda x: x['installations'], reverse=True)

def main():
    districts_folder = Path(__file__).parent / "output" / "districts"
    output_file = Path(__file__).parent / "vendor-filter" / "public" / "vendors.json"
    
    vendors = read_csv_files(districts_folder)
    
    # Get unique districts
    districts = sorted(set(v['district'] for v in vendors))
    
    data = {
        'vendors': vendors,
        'districts': districts,
        'stats': {
            'total': len(vendors),
            'totalInstallations': sum(v['installations'] for v in vendors),
            'totalCapacity': sum(v['capacity'] for v in vendors)
        }
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    
    print(f"Generated {output_file} with {len(vendors)} vendors")

if __name__ == "__main__":
    main()
