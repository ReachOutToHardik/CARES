import axios from 'axios'

// Use Vite environment variable in production (Vercel). Fallback to localhost for local dev.
const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const API = axios.create({
  baseURL: BASE,
  // increase timeout to 60s to accommodate slower AI responses
  timeout: 60000,
})

export async function submitAssessment(payload){
  const resp = await API.post('/assess', payload)
  return resp.data
}

export async function getReports(){
  const resp = await API.get('/reports')
  return resp.data
}

export async function getReport(id){
  const resp = await API.get(`/reports/${id}`)
  return resp.data
}

export default API
