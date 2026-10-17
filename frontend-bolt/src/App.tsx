import { AppProvider, useApp } from './app/AppContext';
import { AppShell } from './components/AppShell';
import { LoginScreen } from './screens/LoginScreen';
import { DashboardScreen } from './screens/DashboardScreen';
import { FindingDetailScreen } from './screens/FindingDetailScreen';
import { AssetListScreen } from './screens/AssetListScreen';
import { AssetRegistrationScreen } from './screens/AssetRegistrationScreen';

function Router() {
  const { user, route } = useApp();

  if (!user) {
    return <LoginScreen />;
  }

  return (
    <AppShell>
      {route.name === 'dashboard' && <DashboardScreen />}
      {route.name === 'finding' && (
        <FindingDetailScreen findingId={route.findingId} />
      )}
      {route.name === 'assets' && <AssetListScreen />}
      {route.name === 'register-asset' && <AssetRegistrationScreen />}
    </AppShell>
  );
}

export default function App() {
  return (
    <AppProvider>
      <Router />
    </AppProvider>
  );
}
