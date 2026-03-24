import csv
from pathlib import Path

def create_master_csv():
    """Reads all GUJARAT CSVs, filters for installations > 10, and creates a master CSV."""
    districts_folder = Path(__file__).parent / "output" / "districts"
    output_file = Path(__file__).parent / "output" / "GUJARAT_Master.csv"
    
    all_vendors = []
    
    # Read all Gujarat district CSV files
    for file in districts_folder.glob("GUJARAT_*.csv"):
        district_name = file.stem.replace("GUJARAT_", "").replace("_", " ")
        
        with open(file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    installations = int(row.get('installations', 0))
                    # Apply filter: more than 10 installations
                    if installations > 10:
                        vendor = {
                            'state': 'GUJARAT',
                            'district': district_name,
                            'company': row.get('company_name', ''),
                            'brand_name': row.get('brand_name', ''),
                            'contact_person': row.get('contact_person', ''),
                            'email': row.get('email', ''),
                            'phone': row.get('phone', ''),
                            'installations': installations,
                            'capacity': float(row.get('capacity_kwp', 0))
                        }
                        all_vendors.append(vendor)
                except (ValueError, KeyError):
                    continue
    
    if not all_vendors:
        print("No vendors found for Gujarat with > 10 installations.")
        return
        
    # Sort by installations (descending)
    all_vendors = sorted(all_vendors, key=lambda x: x['installations'], reverse=True)
    
    # Write to master CSV
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        fieldnames = ['company', 'state', 'district', 'installations', 'capacity', 'phone', 'email', 'contact_person', 'brand_name']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(all_vendors)
        
    print(f"✅ Generated {output_file} with {len(all_vendors)} vendors.")

if __name__ == "__main__":
    create_master_csv()
