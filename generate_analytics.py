"""
Maharashtra Solar Vendors Analytics Dashboard Generator

Parses all Maharashtra district CSV files and generates an interactive
HTML analytics dashboard with charts, filters, and export functionality.
"""

import csv
import json
import os
from pathlib import Path
from datetime import datetime

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
                        'district': district_name,
                        'company': row.get('company_name', ''),
                        'brand': row.get('brand_name', ''),
                        'contact': row.get('contact_person', ''),
                        'email': row.get('email', ''),
                        'phone': row.get('phone', ''),
                        'installations': int(row.get('installations', 0)),
                        'capacity': float(row.get('capacity_kwp', 0))
                    }
                    all_vendors.append(vendor)
                except (ValueError, KeyError) as e:
                    continue
    
    return all_vendors

def calculate_statistics(vendors):
    """Calculate summary statistics."""
    total_vendors = len(vendors)
    total_installations = sum(v['installations'] for v in vendors)
    total_capacity = sum(v['capacity'] for v in vendors)
    
    # Tier distribution
    tiers = {
        'elite': len([v for v in vendors if v['installations'] >= 500]),
        'high': len([v for v in vendors if 200 <= v['installations'] < 500]),
        'medium': len([v for v in vendors if 100 <= v['installations'] < 200]),
        'standard': len([v for v in vendors if 50 <= v['installations'] < 100]),
        'emerging': len([v for v in vendors if 10 <= v['installations'] < 50])
    }
    
    # District statistics
    district_stats = {}
    for v in vendors:
        d = v['district']
        if d not in district_stats:
            district_stats[d] = {'vendors': 0, 'installations': 0, 'capacity': 0}
        district_stats[d]['vendors'] += 1
        district_stats[d]['installations'] += v['installations']
        district_stats[d]['capacity'] += v['capacity']
    
    # Sort districts by total installations
    district_ranking = sorted(
        [{'name': k, **v} for k, v in district_stats.items()],
        key=lambda x: x['installations'],
        reverse=True
    )
    
    return {
        'total_vendors': total_vendors,
        'total_installations': total_installations,
        'total_capacity': round(total_capacity, 2),
        'avg_installations': round(total_installations / total_vendors, 1) if total_vendors > 0 else 0,
        'tiers': tiers,
        'district_ranking': district_ranking
    }

def build_ranking_items(district_ranking):
    """Build HTML for district ranking items."""
    items = []
    for i, d in enumerate(district_ranking):
        if i == 0:
            badge_class = "gold"
        elif i == 1:
            badge_class = "silver"
        elif i == 2:
            badge_class = "bronze"
        else:
            badge_class = "default"
        
        items.append(f'''
                <div class="ranking-item">
                    <div class="rank-badge {badge_class}">#{i+1}</div>
                    <div class="ranking-info">
                        <div class="district-name">{d["name"]}</div>
                        <div class="district-stats">{d["installations"]:,} installations | {d["vendors"]} vendors</div>
                    </div>
                </div>''')
    return ''.join(items)

def build_district_options(district_ranking):
    """Build HTML options for district dropdown."""
    return ''.join([f'<option value="{d["name"]}">{d["name"]}</option>' for d in district_ranking])

def generate_html(vendors, stats):
    """Generate the interactive HTML dashboard."""
    
    # Sort vendors by installations (desc)
    vendors_sorted = sorted(vendors, key=lambda x: x['installations'], reverse=True)
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Maharashtra Solar Vendors Analytics Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: rgba(255, 255, 255, 0.03);
            --bg-glass: rgba(255, 255, 255, 0.05);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-primary: #ffffff;
            --text-secondary: rgba(255, 255, 255, 0.7);
            --text-muted: rgba(255, 255, 255, 0.4);
            --accent-gold: #f5a623;
            --accent-purple: #8b5cf6;
            --accent-cyan: #06b6d4;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --tier-elite: linear-gradient(135deg, #f5a623, #f59e0b);
            --tier-high: linear-gradient(135deg, #8b5cf6, #7c3aed);
            --tier-medium: linear-gradient(135deg, #06b6d4, #0891b2);
            --tier-standard: linear-gradient(135deg, #10b981, #059669);
            --tier-emerging: linear-gradient(135deg, #6b7280, #4b5563);
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        /* Header */
        .header {{
            text-align: center;
            margin-bottom: 3rem;
            padding: 2rem;
            background: var(--bg-glass);
            border-radius: 20px;
            border: 1px solid var(--border-color);
            backdrop-filter: blur(20px);
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-gold), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
        }}
        
        .header p {{
            color: var(--text-secondary);
            font-size: 1.1rem;
        }}
        
        .header .timestamp {{
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-top: 1rem;
        }}
        
        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        
        .stat-card {{
            background: var(--bg-glass);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            backdrop-filter: blur(20px);
            transition: all 0.3s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-4px);
            border-color: var(--accent-gold);
            box-shadow: 0 20px 40px rgba(245, 166, 35, 0.1);
        }}
        
        .stat-card .label {{
            font-size: 0.85rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 0.5rem;
        }}
        
        .stat-card .value {{
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-gold), var(--accent-cyan));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .stat-card .trend {{
            font-size: 0.9rem;
            color: var(--accent-green);
            margin-top: 0.5rem;
        }}
        
        /* Tier Cards */
        .tier-section {{
            margin-bottom: 2rem;
        }}
        
        .section-title {{
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 1.5rem;
            color: var(--text-primary);
        }}
        
        .tier-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
        }}
        
        .tier-card {{
            padding: 1.25rem;
            border-radius: 12px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            border: 2px solid transparent;
        }}
        
        .tier-card.elite {{ background: var(--tier-elite); }}
        .tier-card.high {{ background: var(--tier-high); }}
        .tier-card.medium {{ background: var(--tier-medium); }}
        .tier-card.standard {{ background: var(--tier-standard); }}
        .tier-card.emerging {{ background: var(--tier-emerging); }}
        
        .tier-card:hover {{
            transform: scale(1.05);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}
        
        .tier-card.active {{
            border-color: white;
            box-shadow: 0 0 20px rgba(255,255,255,0.3);
        }}
        
        .tier-card .tier-count {{
            font-size: 2rem;
            font-weight: 700;
            color: white;
        }}
        
        .tier-card .tier-name {{
            font-size: 0.85rem;
            color: rgba(255,255,255,0.9);
            margin-top: 0.25rem;
        }}
        
        .tier-card .tier-range {{
            font-size: 0.75rem;
            color: rgba(255,255,255,0.7);
        }}
        
        /* Controls */
        .controls {{
            background: var(--bg-glass);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            backdrop-filter: blur(20px);
        }}
        
        .controls-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            align-items: end;
        }}
        
        .control-group {{
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }}
        
        .control-group label {{
            font-size: 0.85rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .control-group input,
        .control-group select {{
            padding: 0.75rem 1rem;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: var(--text-primary);
            font-size: 0.95rem;
            transition: all 0.3s ease;
        }}
        
        .control-group input:focus,
        .control-group select:focus {{
            outline: none;
            border-color: var(--accent-gold);
            box-shadow: 0 0 10px rgba(245, 166, 35, 0.2);
        }}
        
        .range-display {{
            text-align: center;
            color: var(--accent-gold);
            font-weight: 600;
            margin-top: 0.5rem;
        }}
        input[type="range"] {{
            width: 100%;
            height: 6px;
            -webkit-appearance: none;
            background: var(--bg-secondary);
            border-radius: 3px;
        }}
        
        input[type="range"]::-webkit-slider-thumb {{
            -webkit-appearance: none;
            width: 18px;
            height: 18px;
            background: var(--accent-gold);
            border-radius: 50%;
            cursor: pointer;
        }}
        
        /* Action Buttons */
        .action-buttons {{
            display: flex;
            gap: 0.75rem;
            flex-wrap: wrap;
        }}
        
        .btn {{
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .btn-primary {{
            background: linear-gradient(135deg, var(--accent-gold), #d4942c);
            color: #000;
        }}
        
        .btn-secondary {{
            background: var(--bg-secondary);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
        }}
        
        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.3);
        }}
        
        /* Charts Section */
        .charts-section {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        
        .chart-card {{
            background: var(--bg-glass);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            backdrop-filter: blur(20px);
        }}
        
        .chart-card h3 {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: var(--text-primary);
        }}
        
        .chart-container {{
            position: relative;
            height: 300px;
        }}
        
        /* District Ranking */
        .ranking-section {{
            background: var(--bg-glass);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }}
        
        .ranking-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 1rem;
            max-height: 400px;
            overflow-y: auto;
        }}
        
        .ranking-item {{
            background: var(--bg-secondary);
            border-radius: 10px;
            padding: 1rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            border: 1px solid var(--border-color);
            transition: all 0.3s ease;
        }}
        
        .ranking-item:hover {{
            border-color: var(--accent-gold);
        }}
        
        .rank-badge {{
            width: 36px;
            height: 36px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.9rem;
        }}
        
        .rank-badge.gold {{ background: var(--tier-elite); color: #000; }}
        .rank-badge.silver {{ background: linear-gradient(135deg, #94a3b8, #64748b); color: #000; }}
        .rank-badge.bronze {{ background: linear-gradient(135deg, #cd7f32, #a0522d); color: #000; }}
        .rank-badge.default {{ background: var(--bg-card); color: var(--text-secondary); }}
        
        .ranking-info {{
            flex: 1;
        }}
        
        .ranking-info .district-name {{
            font-weight: 600;
            color: var(--text-primary);
        }}
        
        .ranking-info .district-stats {{
            font-size: 0.85rem;
            color: var(--text-muted);
        }}
        
        /* Data Table */
        .table-section {{
            background: var(--bg-glass);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            overflow: hidden;
        }}
        
        .table-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            flex-wrap: wrap;
            gap: 1rem;
        }}
        
        .result-count {{
            color: var(--text-secondary);
            font-size: 0.95rem;
        }}
        
        .table-wrapper {{
            overflow-x: auto;
            max-height: 600px;
            overflow-y: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }}
        
        thead {{
            position: sticky;
            top: 0;
            background: var(--bg-secondary);
            z-index: 10;
        }}
        
        th {{
            padding: 1rem;
            text-align: left;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 1px;
            border-bottom: 1px solid var(--border-color);
            cursor: pointer;
            white-space: nowrap;
        }}
        
        th:hover {{
            color: var(--accent-gold);
        }}
        
        td {{
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-secondary);
        }}
        
        tr:hover td {{
            background: rgba(245, 166, 35, 0.05);
        }}
        
        .tier-badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            color: white;
        }}
        
        .tier-badge.elite {{ background: var(--tier-elite); }}
        .tier-badge.high {{ background: var(--tier-high); }}
        .tier-badge.medium {{ background: var(--tier-medium); }}
        .tier-badge.standard {{ background: var(--tier-standard); }}
        .tier-badge.emerging {{ background: var(--tier-emerging); }}
        
        .contact-link {{
            color: var(--accent-cyan);
            text-decoration: none;
        }}
        
        .contact-link:hover {{
            text-decoration: underline;
        }}
        
        /* Scrollbar */
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: var(--bg-secondary);
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: var(--border-color);
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: var(--accent-gold);
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            .container {{
                padding: 1rem;
            }}
            
            .header h1 {{
                font-size: 1.75rem;
            }}
            
            .charts-section {{
                grid-template-columns: 1fr;
            }}
            
            .stat-card .value {{
                font-size: 2rem;
            }}
        }}
        
        /* Print / PDF styles */
        @media print {{
            body {{
                background: white;
                color: black;
            }}
            
            .controls, .action-buttons {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container" id="dashboard-content">
        <!-- Header -->
        <header class="header">
            <h1>🌞 Maharashtra Solar Vendors Analytics</h1>
            <p>Comprehensive analysis of solar installation vendors across Maharashtra districts</p>
            <div class="timestamp">Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</div>
        </header>
        
        <!-- Summary Stats -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="label">Total Vendors</div>
                <div class="value">{stats['total_vendors']:,}</div>
                <div class="trend">Across {len(stats['district_ranking'])} districts</div>
            </div>
            <div class="stat-card">
                <div class="label">Total Installations</div>
                <div class="value">{stats['total_installations']:,}</div>
                <div class="trend">Solar rooftop systems</div>
            </div>
            <div class="stat-card">
                <div class="label">Total Capacity</div>
                <div class="value">{stats['total_capacity']:,.0f}</div>
                <div class="trend">kWp installed</div>
            </div>
            <div class="stat-card">
                <div class="label">Avg. Per Vendor</div>
                <div class="value">{stats['avg_installations']}</div>
                <div class="trend">Installations per vendor</div>
            </div>
        </div>
        
        <!-- Tier Classification -->
        <section class="tier-section">
            <h2 class="section-title">📊 Vendor Classification by Installation Count</h2>
            <div class="tier-grid">
                <div class="tier-card elite active" data-tier="elite" onclick="toggleTier('elite')">
                    <div class="tier-count">{stats['tiers']['elite']}</div>
                    <div class="tier-name">🏆 Elite</div>
                    <div class="tier-range">500+ installations</div>
                </div>
                <div class="tier-card high active" data-tier="high" onclick="toggleTier('high')">
                    <div class="tier-count">{stats['tiers']['high']}</div>
                    <div class="tier-name">⭐ High</div>
                    <div class="tier-range">200-499 installations</div>
                </div>
                <div class="tier-card medium active" data-tier="medium" onclick="toggleTier('medium')">
                    <div class="tier-count">{stats['tiers']['medium']}</div>
                    <div class="tier-name">📈 Medium</div>
                    <div class="tier-range">100-199 installations</div>
                </div>
                <div class="tier-card standard active" data-tier="standard" onclick="toggleTier('standard')">
                    <div class="tier-count">{stats['tiers']['standard']}</div>
                    <div class="tier-name">📊 Standard</div>
                    <div class="tier-range">50-99 installations</div>
                </div>
                <div class="tier-card emerging active" data-tier="emerging" onclick="toggleTier('emerging')">
                    <div class="tier-count">{stats['tiers']['emerging']}</div>
                    <div class="tier-name">📋 Emerging</div>
                    <div class="tier-range">10-49 installations</div>
                </div>
            </div>
        </section>
        
        <!-- Controls -->
        <div class="controls">
            <div class="controls-grid">
                <div class="control-group">
                    <label>Search Vendor</label>
                    <input type="text" id="searchInput" placeholder="Type vendor name..." oninput="filterData()">
                </div>
                <div class="control-group">
                    <label>District</label>
                    <select id="districtFilter" onchange="filterData()">
                        <option value="">All Districts</option>
                        {build_district_options(stats['district_ranking'])}
                    </select>
                </div>
                <div class="control-group">
                    <label>Min Installations</label>
                    <input type="range" id="minInstallations" min="0" max="500" value="0" oninput="updateRangeDisplay(); filterData()">
                    <div class="range-display" id="minDisplay">0</div>
                </div>
                <div class="control-group">
                    <label>Max Installations</label>
                    <input type="range" id="maxInstallations" min="10" max="4000" value="4000" oninput="updateRangeDisplay(); filterData()">
                    <div class="range-display" id="maxDisplay">4000+</div>
                </div>
                <div class="control-group action-buttons">
                    <button class="btn btn-primary" onclick="exportCSV()">📥 Export CSV</button>
                    <button class="btn btn-secondary" onclick="exportPDF()">📄 Export PDF</button>
                    <button class="btn btn-secondary" onclick="resetFilters()">🔄 Reset</button>
                </div>
            </div>
        </div>
        
        <!-- Charts -->
        <section class="charts-section">
            <div class="chart-card">
                <h3>🏆 Top 20 Vendors by Installations</h3>
                <div class="chart-container">
                    <canvas id="topVendorsChart"></canvas>
                </div>
            </div>
            <div class="chart-card">
                <h3>📊 Vendor Distribution by Tier</h3>
                <div class="chart-container">
                    <canvas id="tierChart"></canvas>
                </div>
            </div>
        </section>
        
        <!-- District Ranking -->
        <section class="ranking-section">
            <h2 class="section-title">🗺️ District Ranking by Total Installations</h2>
            <div class="ranking-grid">
                {build_ranking_items(stats['district_ranking'])}
            </div>
        </section>
        
        <!-- Data Table -->
        <section class="table-section">
            <div class="table-header">
                <h2 class="section-title">📋 Vendor Directory</h2>
                <div class="result-count" id="resultCount">Showing {len(vendors_sorted)} vendors</div>
            </div>
            <div class="table-wrapper">
                <table id="vendorTable">
                    <thead>
                        <tr>
                            <th onclick="sortTable(0)">Rank</th>
                            <th onclick="sortTable(1)">Company</th>
                            <th onclick="sortTable(2)">District</th>
                            <th onclick="sortTable(3)">Tier</th>
                            <th onclick="sortTable(4)">Installations ▼</th>
                            <th onclick="sortTable(5)">Capacity (kWp)</th>
                            <th>Email</th>
                            <th>Phone</th>
                        </tr>
                    </thead>
                    <tbody id="vendorTableBody">
                    </tbody>
                </table>
            </div>
        </section>
    </div>
    
    <script>
        // Vendor data
        const allVendors = {json.dumps(vendors_sorted)};
        
        // Tier configuration
        function getTier(installations) {{
            if (installations >= 500) return {{ name: 'Elite', class: 'elite' }};
            if (installations >= 200) return {{ name: 'High', class: 'high' }};
            if (installations >= 100) return {{ name: 'Medium', class: 'medium' }};
            if (installations >= 50) return {{ name: 'Standard', class: 'standard' }};
            return {{ name: 'Emerging', class: 'emerging' }};
        }}
        
        // Active tiers
        let activeTiers = ['elite', 'high', 'medium', 'standard', 'emerging'];
        
        // Toggle tier filter
        function toggleTier(tier) {{
            const card = document.querySelector(`.tier-card.${{tier}}`);
            const index = activeTiers.indexOf(tier);
            
            if (index > -1) {{
                activeTiers.splice(index, 1);
                card.classList.remove('active');
            }} else {{
                activeTiers.push(tier);
                card.classList.add('active');
            }}
            
            filterData();
        }}
        
        // Filter data
        function filterData() {{
            const search = document.getElementById('searchInput').value.toLowerCase();
            const district = document.getElementById('districtFilter').value;
            const minInst = parseInt(document.getElementById('minInstallations').value);
            const maxInst = parseInt(document.getElementById('maxInstallations').value);
            
            const filtered = allVendors.filter(v => {{
                const tier = getTier(v.installations);
                
                if (!activeTiers.includes(tier.class)) return false;
                if (search && !v.company.toLowerCase().includes(search)) return false;
                if (district && v.district !== district) return false;
                if (v.installations < minInst || v.installations > maxInst) return false;
                
                return true;
            }});
            
            renderTable(filtered);
            updateResultCount(filtered.length);
        }}
        
        // Render table
        function renderTable(data) {{
            const tbody = document.getElementById('vendorTableBody');
            
            tbody.innerHTML = data.map((v, i) => {{
                const tier = getTier(v.installations);
                return `
                    <tr>
                        <td>${{i + 1}}</td>
                        <td><strong>${{v.company}}</strong></td>
                        <td>${{v.district}}</td>
                        <td><span class="tier-badge ${{tier.class}}">${{tier.name}}</span></td>
                        <td><strong>${{v.installations.toLocaleString()}}</strong></td>
                        <td>${{v.capacity.toLocaleString()}}</td>
                        <td><a href="mailto:${{v.email}}" class="contact-link">${{v.email}}</a></td>
                        <td><a href="tel:${{v.phone}}" class="contact-link">${{v.phone}}</a></td>
                    </tr>
                `;
            }}).join('');
        }}
        
        // Update result count
        function updateResultCount(count) {{
            document.getElementById('resultCount').textContent = `Showing ${{count.toLocaleString()}} vendors`;
        }}
        
        // Update range display
        function updateRangeDisplay() {{
            const min = document.getElementById('minInstallations').value;
            const max = document.getElementById('maxInstallations').value;
            document.getElementById('minDisplay').textContent = min;
            document.getElementById('maxDisplay').textContent = max >= 4000 ? '4000+' : max;
        }}
        
        // Reset filters
        function resetFilters() {{
            document.getElementById('searchInput').value = '';
            document.getElementById('districtFilter').value = '';
            document.getElementById('minInstallations').value = 0;
            document.getElementById('maxInstallations').value = 4000;
            activeTiers = ['elite', 'high', 'medium', 'standard', 'emerging'];
            
            document.querySelectorAll('.tier-card').forEach(card => card.classList.add('active'));
            updateRangeDisplay();
            filterData();
        }}
        
        // Sort table
        let sortDirection = {{}};
        function sortTable(column) {{
            // Implementation for table sorting
            const tbody = document.getElementById('vendorTableBody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            
            sortDirection[column] = !sortDirection[column];
            
            rows.sort((a, b) => {{
                let aVal = a.cells[column].textContent;
                let bVal = b.cells[column].textContent;
                
                // Numeric columns
                if ([0, 4, 5].includes(column)) {{
                    aVal = parseFloat(aVal.replace(/,/g, '')) || 0;
                    bVal = parseFloat(bVal.replace(/,/g, '')) || 0;
                    return sortDirection[column] ? aVal - bVal : bVal - aVal;
                }}
                
                return sortDirection[column] 
                    ? aVal.localeCompare(bVal) 
                    : bVal.localeCompare(aVal);
            }});
            
            rows.forEach(row => tbody.appendChild(row));
        }}
        
        // Export CSV
        function exportCSV() {{
            const search = document.getElementById('searchInput').value.toLowerCase();
            const district = document.getElementById('districtFilter').value;
            const minInst = parseInt(document.getElementById('minInstallations').value);
            const maxInst = parseInt(document.getElementById('maxInstallations').value);
            
            const filtered = allVendors.filter(v => {{
                const tier = getTier(v.installations);
                if (!activeTiers.includes(tier.class)) return false;
                if (search && !v.company.toLowerCase().includes(search)) return false;
                if (district && v.district !== district) return false;
                if (v.installations < minInst || v.installations > maxInst) return false;
                return true;
            }});
            
            let csv = 'Rank,Company,District,Tier,Installations,Capacity (kWp),Email,Phone\\n';
            filtered.forEach((v, i) => {{
                const tier = getTier(v.installations);
                csv += `${{i+1}},"${{v.company}}","${{v.district}}","${{tier.name}}",${{v.installations}},${{v.capacity}},${{v.email}},${{v.phone}}\\n`;
            }});
            
            const blob = new Blob([csv], {{ type: 'text/csv' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'maharashtra_solar_vendors.csv';
            a.click();
        }}
        
        // Export PDF
        function exportPDF() {{
            const element = document.getElementById('dashboard-content');
            const opt = {{
                margin: 10,
                filename: 'maharashtra_solar_analytics.pdf',
                image: {{ type: 'jpeg', quality: 0.98 }},
                html2canvas: {{ scale: 2 }},
                jsPDF: {{ unit: 'mm', format: 'a3', orientation: 'landscape' }}
            }};
            
            html2pdf().set(opt).from(element).save();
        }}
        
        // Initialize charts
        function initCharts() {{
            // Top Vendors Chart
            const topVendors = allVendors.slice(0, 20);
            new Chart(document.getElementById('topVendorsChart'), {{
                type: 'bar',
                data: {{
                    labels: topVendors.map(v => v.company.substring(0, 20) + (v.company.length > 20 ? '...' : '')),
                    datasets: [{{
                        label: 'Installations',
                        data: topVendors.map(v => v.installations),
                        backgroundColor: topVendors.map(v => {{
                            if (v.installations >= 500) return '#f5a623';
                            if (v.installations >= 200) return '#8b5cf6';
                            if (v.installations >= 100) return '#06b6d4';
                            return '#10b981';
                        }}),
                        borderRadius: 6
                    }}]
                }},
                options: {{
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ display: false }}
                    }},
                    scales: {{
                        x: {{
                            grid: {{ color: 'rgba(255,255,255,0.1)' }},
                            ticks: {{ color: 'rgba(255,255,255,0.6)' }}
                        }},
                        y: {{
                            grid: {{ display: false }},
                            ticks: {{ 
                                color: 'rgba(255,255,255,0.8)',
                                font: {{ size: 10 }}
                            }}
                        }}
                    }}
                }}
            }});
            
            // Tier Distribution Chart
            new Chart(document.getElementById('tierChart'), {{
                type: 'doughnut',
                data: {{
                    labels: ['Elite (500+)', 'High (200-499)', 'Medium (100-199)', 'Standard (50-99)', 'Emerging (10-49)'],
                    datasets: [{{
                        data: [{stats['tiers']['elite']}, {stats['tiers']['high']}, {stats['tiers']['medium']}, {stats['tiers']['standard']}, {stats['tiers']['emerging']}],
                        backgroundColor: ['#f5a623', '#8b5cf6', '#06b6d4', '#10b981', '#6b7280'],
                        borderWidth: 0
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'right',
                            labels: {{
                                color: 'rgba(255,255,255,0.8)',
                                padding: 15,
                                font: {{ size: 11 }}
                            }}
                        }}
                    }},
                    cutout: '60%'
                }}
            }});
        }}
        
        // Initialize
        document.addEventListener('DOMContentLoaded', () => {{
            renderTable(allVendors);
            initCharts();
        }});
    </script>
</body>
</html>
'''
    return html

def main():
    # Paths
    districts_folder = Path(__file__).parent / "output" / "districts"
    output_file = Path(__file__).parent / "output" / "analytics_report.html"
    
    print("📊 Maharashtra Solar Vendors Analytics Dashboard Generator")
    print("=" * 60)
    
    # Read data
    print("📂 Reading CSV files...")
    vendors = read_csv_files(districts_folder)
    print(f"   Found {len(vendors)} vendors")
    
    # Calculate stats
    print("📈 Calculating statistics...")
    stats = calculate_statistics(vendors)
    print(f"   Total installations: {stats['total_installations']:,}")
    print(f"   Elite vendors: {stats['tiers']['elite']}")
    print(f"   High tier vendors: {stats['tiers']['high']}")
    
    # Generate HTML
    print("🎨 Generating dashboard...")
    html = generate_html(vendors, stats)
    
    # Save
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n✅ Dashboard generated successfully!")
    print(f"   📁 Location: {output_file}")
    print(f"\n🌐 Open in browser to view the interactive dashboard")

if __name__ == "__main__":
    main()
