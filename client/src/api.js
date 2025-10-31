import axios from 'axios'

const API = axios.create({
  baseURL: 'http://localhost:8000',
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
