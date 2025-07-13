import axios from 'axios';
import useSWR from 'swr';

const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api',
});

const fetcher = (url: string) => apiClient.get(url).then(res => res.data);

export const api = {
  getStatus: (url: string) => fetcher(url),
  getTeams: () => fetcher('/teams'),
  rerunPhase: (phase: string, options?: { override_weights?: any; random_seed?: number }) =>
    apiClient.post(`/match/phase${phase}`, options),
  downloadTeamsCsv: () => {
    window.open('http://localhost:8000/api/export/teams');
  },
};

export const useLogs = () => {
  const { data, error } = useSWR(
    'ws://localhost:8000/api/ws/logs',
    (url: string) => {
      const ws = new WebSocket(url);
      const messages: string[] = [];
      ws.onmessage = (event) => {
        messages.push(event.data);
      };
      // This is a simplified implementation for SWR.
      // A more robust solution might use a different library for websockets.
      return { messages };
    }
  );

  return {
    logs: data?.messages,
    isLoading: !error && !data,
    isError: error,
  };
}; 