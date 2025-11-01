import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { QUESTIONS, OPTIONS } from '../questions'
import { submitAssessment } from '../api'

export default function Assessment(){
  const [childName, setChildName] = useState('')
  const [childAge, setChildAge] = useState(10)
  const [parentContact, setParentContact] = useState('')
  const [answers, setAnswers] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  function setAnswer(qid, option){
    setAnswers(prev => ({ ...prev, [qid]: option }))
  }

  async function onSubmit(e){
    e.preventDefault()
    setError(null)
    const payload = {
      child_name: childName,
      child_age: Number(childAge),
      parent_contact: parentContact,
      answers: Object.keys(answers).map(k => ({ qid: Number(k), option: answers[k] }))
    }
    setLoading(true)
    try{
      const res = await submitAssessment(payload)
      // pass response in state via navigation
      navigate('/results', { state: { result: res } })
    }catch(err){
      console.error(err)
      setError(err?.response?.data?.detail || err.message)
    }finally{
      setLoading(false)
    }
  }

  return (
    <div className="page assessment">
      <div className="header-compact">
        <div>
          <h2>Assessment</h2>
          <p style={{color:'var(--muted)'}}>Complete the 20-item questionnaire to generate a professional safety & readiness report.</p>
        </div>
        <div>
          <div style={{fontSize:12,color:'var(--muted)'}}>Fields marked required</div>
        </div>
      </div>

      <form onSubmit={onSubmit}>
        <div style={{display:'grid',gridTemplateColumns:'1fr 120px',gap:12,marginTop:12}}>
          <label>
            Child name
            <input value={childName} onChange={e => setChildName(e.target.value)} required />
          </label>
          <label>
            Child age
            <input type="number" value={childAge} onChange={e => setChildAge(e.target.value)} required min={3} max={25} />
          </label>
          <label style={{gridColumn:'1 / -1'}}>
            Parent contact
            <input value={parentContact} onChange={e => setParentContact(e.target.value)} required />
          </label>
        </div>

        <h3 style={{marginTop:18}}>Questions</h3>
        {QUESTIONS.map(q => (
          <div key={q.id} className="question">
            <p><strong>Q{q.id}.</strong> {q.text}</p>
            <div className="options" style={{display:'flex',gap:10,flexWrap:'wrap'}}>
              {(() => {
                const keys = ['A','B','C','D']
                const opts = q.choices ? keys.map(k => ({ key: k, label: q.choices[k] })) : OPTIONS
                return opts.map(o => (
                  <label key={o.key} style={{background:'#fff',border:'1px solid #eef4ff',padding:'8px 10px',borderRadius:8,display:'flex',alignItems:'center',gap:8}}>
                    <input
                      type="radio"
                      name={`q${q.id}`}
                      value={o.key}
                      checked={answers[q.id] === o.key}
                      onChange={() => setAnswer(q.id, o.key)}
                      required
                    /> <span style={{fontSize:13}}>{o.label}</span>
                  </label>
                ))
              })()}
            </div>
          </div>
        ))}

        <div className="actions">
          <button className="primary" type="submit" disabled={loading}>{loading ? 'Submitting...' : 'Submit Assessment'}</button>
        </div>
        {error && <div className="error">{error}</div>}
      </form>
    </div>
  )
}
