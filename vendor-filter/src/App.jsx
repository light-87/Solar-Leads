import { useState, useEffect, useMemo } from 'react'
import './App.css'

function App() {
  const [data, setData] = useState({ vendors: [], districts: [], stats: {} })
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [district, setDistrict] = useState('')
  const [stateFilter, setStateFilter] = useState('')
  const [minInstallations, setMinInstallations] = useState(0)
  const [maxInstallations, setMaxInstallations] = useState(10000)
  const [activeTiers, setActiveTiers] = useState(['elite', 'high', 'medium', 'standard', 'emerging'])
  const [sortConfig, setSortConfig] = useState({ key: 'installations', direction: 'desc' })

  // Load data
  useEffect(() => {
    fetch('/vendors.json')
      .then(res => res.json())
      .then(d => {
        setData(d)
        setLoading(false)
      })
      .catch(err => {
        console.error('Error loading data:', err)
        setLoading(false)
      })
  }, [])

  // Get tier from installations
  const getTier = (installations) => {
    if (installations >= 500) return 'elite'
    if (installations >= 200) return 'high'
    if (installations >= 100) return 'medium'
    if (installations >= 50) return 'standard'
    return 'emerging'
  }

  const getTierLabel = (tier) => {
    const labels = {
      elite: '🏆 Elite (500+)',
      high: '⭐ High (200-499)',
      medium: '📈 Medium (100-199)',
      standard: '📊 Standard (50-99)',
      emerging: '📋 Emerging (10-49)'
    }
    return labels[tier] || tier
  }

  // Filter and sort vendors
  const filteredVendors = useMemo(() => {
    let result = data.vendors.filter(v => {
      const tier = getTier(v.installations)
      if (!activeTiers.includes(tier)) return false
      if (search && !v.company.toLowerCase().includes(search.toLowerCase())) return false
      if (stateFilter && v.state !== stateFilter) return false
      if (district && v.district !== district) return false
      if (v.installations < minInstallations || v.installations > maxInstallations) return false
      return true
    })

    // Sort
    result.sort((a, b) => {
      const aVal = a[sortConfig.key]
      const bVal = b[sortConfig.key]
      if (typeof aVal === 'number') {
        return sortConfig.direction === 'asc' ? aVal - bVal : bVal - aVal
      }
      return sortConfig.direction === 'asc' 
        ? String(aVal).localeCompare(String(bVal))
        : String(bVal).localeCompare(String(aVal))
    })

    return result
  }, [data.vendors, search, stateFilter, district, minInstallations, maxInstallations, activeTiers, sortConfig])

  // Toggle tier filter
  const toggleTier = (tier) => {
    setActiveTiers(prev => 
      prev.includes(tier) 
        ? prev.filter(t => t !== tier)
        : [...prev, tier]
    )
  }

  // Sort handler
  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc'
    }))
  }

  const resetFilters = () => {
    setSearch('')
    setStateFilter('')
    setDistrict('')
    setMinInstallations(0)
    setMaxInstallations(10000)
    setActiveTiers(['elite', 'high', 'medium', 'standard', 'emerging'])
  }

  // Stats for filtered data
  const filteredStats = useMemo(() => ({
    count: filteredVendors.length,
    installations: filteredVendors.reduce((sum, v) => sum + v.installations, 0),
    capacity: filteredVendors.reduce((sum, v) => sum + v.capacity, 0)
  }), [filteredVendors])

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '4rem' }}>Loading vendors...</div>
  }

  return (
    <>
      <header className="app-header">
        <h1>☀️ Solar Vendors Directory</h1>
        <p>Filter and sort vendor data</p>
      </header>

      {/* Filters */}
      <section className="filters-section">
        <div className="filters-grid">
          <div className="filter-group">
            <label>Search Company</label>
            <input 
              type="text" 
              placeholder="Type to search..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div className="filter-group">
            <label>State</label>
            <select value={stateFilter} onChange={(e) => setStateFilter(e.target.value)}>
              <option value="">All States</option>
              {data.states?.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label>District</label>
            <select value={district} onChange={(e) => setDistrict(e.target.value)}>
              <option value="">All Districts</option>
              {data.districts
                .filter(d => !stateFilter || data.vendors.find(v => v.district === d && v.state === stateFilter))
                .map(d => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label>Min Installations</label>
            <input 
              type="number" 
              value={minInstallations}
              onChange={(e) => setMinInstallations(Number(e.target.value))}
              min="0"
            />
          </div>

          <div className="filter-group">
            <label>Max Installations</label>
            <input 
              type="number" 
              value={maxInstallations}
              onChange={(e) => setMaxInstallations(Number(e.target.value))}
              min="0"
            />
          </div>
        </div>

        <div className="filter-group" style={{ marginTop: '1rem' }}>
          <label>Filter by Tier (click to toggle)</label>
          <div className="tier-filters">
            {['elite', 'high', 'medium', 'standard', 'emerging'].map(tier => (
              <button 
                key={tier}
                className={`tier-btn ${tier} ${activeTiers.includes(tier) ? 'active' : 'inactive'}`}
                onClick={() => toggleTier(tier)}
              >
                {getTierLabel(tier)}
              </button>
            ))}
          </div>
        </div>

        <div className="action-buttons">
          <button className="btn btn-secondary" onClick={resetFilters}>
            🔄 Reset Filters
          </button>
        </div>
      </section>

      {/* Stats */}
      <div className="stats-bar">
        <div className="stat-item">
          <span className="stat-value">{filteredStats.count.toLocaleString()}</span>
          <span className="stat-label">Vendors</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{filteredStats.installations.toLocaleString()}</span>
          <span className="stat-label">Total Installations</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{Math.round(filteredStats.capacity).toLocaleString()}</span>
          <span className="stat-label">Capacity (kWp)</span>
        </div>
      </div>

      {/* Table */}
      <div className="table-container">
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th onClick={() => handleSort('company')}>
                  Company {sortConfig.key === 'company' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : ''}
                </th>
                <th onClick={() => handleSort('state')}>
                  State {sortConfig.key === 'state' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : ''}
                </th>
                <th onClick={() => handleSort('district')}>
                  District {sortConfig.key === 'district' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : ''}
                </th>
                <th>Tier</th>
                <th onClick={() => handleSort('installations')}>
                  Installations {sortConfig.key === 'installations' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : ''}
                </th>
                <th onClick={() => handleSort('capacity')}>
                  Capacity {sortConfig.key === 'capacity' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : ''}
                </th>
                <th>Email</th>
                <th>Phone</th>
              </tr>
            </thead>
            <tbody>
              {filteredVendors.map(vendor => {
                const tier = getTier(vendor.installations)
                return (
                  <tr key={vendor.id}>
                    <td><strong>{vendor.company}</strong></td>
                    <td>{vendor.state}</td>
                    <td>{vendor.district}</td>
                    <td><span className={`tier-badge ${tier}`}>{tier}</span></td>
                    <td><strong>{vendor.installations.toLocaleString()}</strong></td>
                    <td>{vendor.capacity.toLocaleString()}</td>
                    <td>{vendor.email}</td>
                    <td>{vendor.phone}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}

export default App
