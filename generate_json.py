import csv
import json
from pathlib import Path

def read_csv_files(districts_folder):
    """Read all Maharashtra CSV files and return consolidated data."""
    all_vendors = []
    
    for file in Path(districts_folder).glob("*.csv"):
        # File format: STATE_District_Name.csv
        parts = file.stem.split("_", 1)
        state_name = parts[0] if len(parts) > 1 else "Unknown"
        district_name = parts[1].replace("_", " ") if len(parts) > 1 else file.stem

        
        with open(file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    installations = int(row.get('installations', 0))
                    if installations > 10:
                        vendor = {
                            'id': len(all_vendors) + 1,
                            'state': state_name,
                            'district': district_name,
                            'company': row.get('company_name', ''),
                            'email': row.get('email', ''),
                            'phone': row.get('phone', ''),
                            'installations': installations,
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
    
    # Get unique districts and states
    districts = sorted(set(v['district'] for v in vendors))
    states = sorted(set(v['state'] for v in vendors))
    
    data = {
        'vendors': vendors,
        'districts': districts,
        'states': states,
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
