import React, { useEffect, useState } from 'react'
import { getReports, getReport } from '../api'
import { Link } from 'react-router-dom'

export default function Dashboard(){
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState(null)

  useEffect(()=>{
    setLoading(true)
    getReports().then(r=> setReports(r)).catch(e=> setError(e.message)).finally(()=> setLoading(false))
  },[])

  async function viewReport(id){
    try{
      const r = await getReport(id)
      setSelected(r)
    }catch(e){
      setError(e.message)
    }
  }

  return (
    <div className="page dashboard">
      <div className="dashboard-hero">
        <div style={{flex:1}}>
          <h2>CARES — Run Assessment Dashboard</h2>
          <p className="lead">Assess a child's readiness to use AI safely. CARES helps counsellors deliver evidence-based ratings, clear red-flag alerts, and a professional improvement plan parents can act on.</p>
          <div className="features">
            <ul>
              <li><strong>Evidence-based scoring</strong> — weighted pillars & clear red-flag rules</li>
              <li><strong>Concise professional reports</strong> — empathetic paragraph, 30/60/90 plan</li>
            </ul>
          </div>
        </div>
        <div style={{width:260}} className="cta">
          <Link className="btn" to="/">Start an Assessment</Link>
        </div>
      </div>

      <h3>Saved reports</h3>
      {loading && <p>Loading...</p>}
      {error && <p className="error">{error}</p>}
      <div className="reports-list">
        {reports.map(r => {
          const score = r.scores?.overall_score ?? r.scores?.overall ?? 0
          const cls = score >= 70 ? 'score-good' : (score >= 40 ? 'score-mid' : 'score-bad')
          return (
            <div key={r.id} className="report-card">
              <div className="meta">
                <strong>{r.child}</strong>
                <div style={{color:'var(--muted)',fontSize:13}}>{new Date(r.timestamp*1000).toLocaleString()}</div>
              </div>
              <div style={{display:'flex',alignItems:'center',gap:12}}>
                <div className={`score-badge ${cls}`}>{Math.round(score)}</div>
                <div>
                  <button className="ghost" onClick={() => viewReport(r.id)}>View</button>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {selected && (
        <div className="report-detail">
          <h3>Report for {selected.child?.child_name}</h3>
          <pre style={{whiteSpace:'pre-wrap'}}>{JSON.stringify(selected, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}
