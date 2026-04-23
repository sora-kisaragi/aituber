import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL ?? '/api'

export const api = axios.create({ baseURL: API_BASE })

export const MEDIA_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/media`
  : '/media'
