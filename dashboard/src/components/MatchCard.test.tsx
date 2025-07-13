import { render, screen } from '@testing-library/react';
import { PhaseCard } from './PhaseCard';
import { SWRConfig } from 'swr';
import { vi } from 'vitest';

vi.mock('../api', () => ({
  api: {
    getStatus: vi.fn(),
  },
}));

describe('PhaseCard', () => {
  it('renders loading state', () => {
    render(
      <SWRConfig value={{ dedupingInterval: 0 }}>
        <PhaseCard phase="1" />
      </SWRConfig>
    );
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('renders with data', async () => {
    // Mock the SWR response
    const mockData = { progress: 50, status: 'running', total_cost: 12.34 };
    
    render(
      <SWRConfig value={{ provider: () => new Map([['/match/phase1/status', mockData]]) }}>
        <PhaseCard phase="1" />
      </SWRConfig>
    );

    // Using findBy queries to wait for async state updates
    expect(await screen.findByText('Status: running')).toBeInTheDocument();
    expect(await screen.findByText('Total Cost: 12.3400')).toBeInTheDocument();
    const rerunButton = await screen.findByRole('button', { name: /rerun/i });
    expect(rerunButton).toBeDisabled();
  });
}); 