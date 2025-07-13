import { PhaseCard } from './PhaseCard';

export function MatchDashboard() {
  return (
    <div>
      <h2 className="text-xl mb-4">Matching Phases</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <PhaseCard phase="1" />
        <PhaseCard phase="2" />
        <PhaseCard phase="3" />
      </div>
    </div>
  );
} 