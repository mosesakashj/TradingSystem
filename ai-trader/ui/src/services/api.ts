// API Service for Trading Dashboard
import axios, { AxiosInstance, AxiosError } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class APIService {
  private client: AxiosInstance;
  private token: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for auth
    this.client.interceptors.request.use(
      (config) => {
        if (this.token) {
          config.headers.Authorization = `Bearer ${this.token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Unauthorized - clear token
          this.clearToken();
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );

    // Load token from localStorage
    const savedToken = localStorage.getItem('auth_token');
    if (savedToken) {
      this.token = savedToken;
    }
  }

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('auth_token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('auth_token');
  }

  // Authentication
  async login(username: string, password: string) {
    const response = await this.client.post('/auth/login', {
      username,
      password,
    });
    this.setToken(response.data.access_token);
    return response.data;
  }

  async logout() {
    this.clearToken();
  }

  // Health check
  async getHealth() {
    const response = await this.client.get('/health');
    return response.data;
  }

  // Statistics
  async getStats() {
    const response = await this.client.get('/stats');
    return response.data;
  }

  // Signals
  async getSignals(params?: {
    symbol?: string;
    status?: string;
    limit?: number;
  }) {
    const response = await this.client.get('/signals', { params });
    return response.data;
  }

  async getSignalById(id: number) {
    const response = await this.client.get(`/signals/${id}`);
    return response.data;
  }

  async getSignalDetails(id: number) {
    // Get signal with prediction and LLM reasoning
    const response = await this.client.get(`/signals/${id}/details`);
    return response.data;
  }

  // Trades
  async getTrades(params?: {
    symbol?: string;
    status?: string;
    limit?: number;
  }) {
    const response = await this.client.get('/trades', { params });
    return response.data;
  }

  async getTradeById(id: number) {
    const response = await this.client.get(`/trades/${id}`);
    return response.data;
  }

  // Positions
  async getOpenPositions() {
    const response = await this.client.get('/positions');
    return response.data;
  }

  async closePosition(positionId: number) {
    const response = await this.client.post(`/positions/${positionId}/close`);
    return response.data;
  }

  // Risk metrics
  async getRiskMetrics() {
    const response = await this.client.get('/risk/metrics');
    return response.data;
  }

  async activateKillSwitch(reason?: string) {
    const response = await this.client.post('/risk/kill-switch/activate', {
      reason,
    });
    return response.data;
  }

  async deactivateKillSwitch() {
    const response = await this.client.post('/risk/kill-switch/deactivate');
    return response.data;
  }

  // System health
  async getSystemHealth() {
    const response = await this.client.get('/system/health');
    return response.data;
  }

  // Models
  async getModels() {
    const response = await this.client.get('/models');
    return response.data;
  }

  async getModelMetrics(modelName: string) {
    const response = await this.client.get(`/models/${modelName}/metrics`);
    return response.data;
  }
}

export const api = new APIService();
