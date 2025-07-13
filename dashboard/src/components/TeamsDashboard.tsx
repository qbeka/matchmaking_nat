import { AgGridReact } from 'ag-grid-react';
import useSWR from 'swr';
import { api } from '../api';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';

export function TeamsDashboard() {
  const { data: teams, error } = useSWR('/api/teams', api.getTeams);

  const columnDefs = [
    { field: 'team_id', headerName: 'Team ID' },
    { field: 'assigned_problem_title', headerName: 'Problem' },
    { field: 'coverage', headerName: 'Coverage %' },
    { field: 'diversity_score', headerName: 'Diversity' },
    { field: 'worst_skill_gap', headerName: 'Worst Skill Gap' },
  ];
  
  const getRowClass = (params) => {
    if (params.data.coverage >= 0.75) return 'bg-green-700';
    if (params.data.coverage >= 0.5) return 'bg-yellow-700';
    return 'bg-red-700';
  };

  if (error) return <div>Failed to load teams.</div>;
  if (!teams) return <div>Loading teams...</div>;

  return (
    <div>
      <h2 className="text-xl mb-4">Final Teams</h2>
      <div className="ag-theme-alpine-dark" style={{ height: 600, width: '100%' }}>
        <AgGridReact
          rowData={teams}
          columnDefs={columnDefs}
          getRowClass={getRowClass}
        />
      </div>
      <button 
        onClick={() => api.downloadTeamsCsv()}
        className="mt-4 px-4 py-2 bg-green-600 rounded hover:bg-green-700"
      >
        Download CSV
      </button>
    </div>
  );
} 