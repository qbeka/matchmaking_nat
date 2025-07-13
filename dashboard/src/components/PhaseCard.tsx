import useSWR from 'swr';
import { api } from '../api';
import toast from 'react-hot-toast';

interface PhaseCardProps {
  phase: string;
}

export function PhaseCard({ phase }: PhaseCardProps) {
  const { data, error, mutate } = useSWR(`/match/phase${phase}/status`, api.getStatus);
  const isLoading = !data && !error;

  const handleRerun = async () => {
    try {
      await api.rerunPhase(phase);
      toast.success(`Phase ${phase} rerun initiated.`);
      mutate(); // Re-fetch status
    } catch (err) {
      toast.error(`Failed to rerun phase ${phase}.`);
    }
  };

  return (
    <div className="bg-gray-800 p-4 rounded-lg shadow-lg">
      <h3 className="font-bold text-lg">Phase {phase}</h3>
      {isLoading && <p>Loading...</p>}
      {error && <p className="text-red-400">Error loading status.</p>}
      {data && (
        <div>
          <div className="w-full bg-gray-700 rounded-full h-2.5 my-2">
            <div className="bg-blue-600 h-2.5 rounded-full" style={{ width: `${data.progress || 0}%` }}></div>
          </div>
          <p>Status: {data.status || 'Idle'}</p>
          <p>Total Cost: {data.total_cost?.toFixed(4) || 'N/A'}</p>
          <button
            onClick={handleRerun}
            disabled={data.status === 'running'}
            className="mt-2 px-4 py-2 bg-blue-600 rounded hover:bg-blue-700 disabled:bg-gray-500"
          >
            Rerun
          </button>
        </div>
      )}
    </div>
  );
} 