import { Toaster } from 'react-hot-toast';
import { MatchDashboard } from './components/MatchDashboard';
import { TeamsDashboard } from './components/TeamsDashboard';

function App() {
  const
 
path = window.location.pathname;

  return (
    <div className="bg-gray-900 text-white min-h-screen">
      <Toaster />
      <header className="p-4 bg-gray-800 shadow-md">
        <h1 className="text-2xl font-bold">NAT Ignite Matchmaker</h1>
        <nav className="mt-2">
          <a href="/match" className={`mr-4 ${path === '/match' ? 'text-blue-400' : ''}`}>Match</a>
          <a href="/teams" className={path === '/teams' ? 'text-blue-400' : ''}>Teams</a>
        </nav>
      </header>
      <main className="p-4">
        {path === '/match' && <MatchDashboard />}
        {path === '/teams' && <TeamsDashboard />}
      </main>
    </div>
  );
}

export default App;
