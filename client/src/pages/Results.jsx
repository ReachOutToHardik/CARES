import React from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

export default function Results(){
  const location = useLocation()
  const navigate = useNavigate()
  const res = location.state?.result

  if(!res) return <div className="page">No result data. Please complete an assessment first.</div>

  const plan = res.improvement_plan || res.improvement_plan || {}
  const getPlan = key => plan[key] || plan[key.replace('_days','')] || []

  return (
    <div className="page results">
      <div className="results-hero">
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
          <div>
            <h2 style={{margin:0}}>{res.header_summary || `${res.category} — Score: ${res.score}`}</h2>
            {res.professional_paragraph && (
              <p className="professional-paragraph">{res.professional_paragraph}</p>
            )}
          </div>
          <div style={{textAlign:'right'}}>
            <div style={{fontSize:24,fontWeight:700}}>{res.score}</div>
            <div style={{fontSize:13,color:'var(--muted)'}}>{res.category}</div>
            <div style={{height:8,background:'#eef4ff',borderRadius:8,overflow:'hidden',marginTop:8,width:120}}>
              <div style={{height:8,background:'linear-gradient(90deg,var(--accent),var(--accent-2))',width:`${Math.min(100,Math.max(0,res.score))}%`}} />
            </div>
            <div style={{marginTop:8,fontSize:12,color:'var(--muted)'}}>Confidence: {res.monitor_confidence ?? '—'}/100</div>
          </div>
        </div>
      </div>

      <section>
        <h3>Observations</h3>
        {res.observations ? (
          <ul>{res.observations.map((o,i) => <li key={i}>{o}</li>)}</ul>
        ) : (
          <p>{res.raw_ai?.text || res.ai_parsed?.narrative || 'No observations returned by AI.'}</p>
        )}
      </section>

      <section>
        <h3>Why this matters</h3>
        <p>{res.why_this_matters || ''}</p>
      </section>

      <section>
        <h3>Improvement Plan</h3>
        { (getPlan('30_days').length || getPlan('60_days').length || getPlan('90_days').length) ? (
          <div className="plan">
            <div className="plan-block">
              <h4>30 days</h4>
              <ul>{getPlan('30_days').map((b,i)=> <li key={i}>{b}</li>)}</ul>
            </div>
            <div className="plan-block">
              <h4>60 days</h4>
              <ul>{getPlan('60_days').map((b,i)=> <li key={i}>{b}</li>)}</ul>
            </div>
            <div className="plan-block">
              <h4>90 days</h4>
              <ul>{getPlan('90_days').map((b,i)=> <li key={i}>{b}</li>)}</ul>
            </div>
          </div>
        ) : (
          <p>No structured plan returned by AI.</p>
        )}
      </section>

      <section>
        <h3>Recommended Family AI Rules</h3>
        {res.recommended_family_rules ? (
          <ol>{res.recommended_family_rules.map((r,i)=> <li key={i}>{r}</li>)}</ol>
        ) : <p>No rules returned</p>}
      </section>

      <section>
        <h3>Counselor Notes & Resources</h3>
        <p><strong>Counselor notes:</strong> {res.counselor_notes || '—'}</p>
        {res.suggested_resources && res.suggested_resources.length ? (
          <ul>{res.suggested_resources.map((r,i)=> <li key={i}><a href={r.url} target="_blank" rel="noreferrer">{r.title}</a></li>)}</ul>
        ) : <p>No suggested resources.</p>}
      </section>

      <section>
        <h3>Follow up</h3>
        <p>Next assessment recommended: {res.follow_up?.next_assessment_date || '—'}</p>
        <p>Consultant recommended: {res.follow_up?.consultant_recommended || '—'}</p>
      </section>

      <section>
        <h3>Technical Details</h3>
        <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}>
          <div>
            <h4 style={{marginBottom:6}}>Pillar scores</h4>
            <pre>{JSON.stringify(res.pillars || res.scores?.pillar_percentages || {}, null, 2)}</pre>
          </div>
          <div>
            <h4 style={{marginBottom:6}}>Risk summary</h4>
            <pre>{JSON.stringify(res.risks || {}, null, 2)}</pre>
          </div>
        </div>
      </section>

      <div className="actions" style={{display:'flex',gap:12,marginTop:16}}>
        <button className="ghost" onClick={()=> navigate('/dashboard')}>Back to Dashboard</button>
        <button className="primary" onClick={()=> alert('PDF export is a stub in this MVP')}>Download PDF</button>
      </div>
    </div>
  )
}
