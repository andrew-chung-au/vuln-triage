import { describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AppProvider } from '../app/AppContext';
import { DashboardScreen } from './DashboardScreen';
import { FindingDetailScreen } from './FindingDetailScreen';
import { mockServices } from '../services/mockServices';

// Helper: sign in once so screens that rely on the service are ready.
function signInDemo() {
  mockServices.signIn({
    email: 'dana.reyes@example.com',
    password: 'triage-demo',
  });
}

function renderWithProvider(ui: React.ReactNode) {
  return render(<AppProvider>{ui}</AppProvider>);
}

describe('DashboardScreen', () => {
  it('displays findings in the order the services layer returns them, with each tier shown', () => {
    signInDemo();
    const ordered = mockServices.listFindings();

    renderWithProvider(<DashboardScreen />);

    const rows = screen.getAllByRole('row');
    // First row is the header.
    const bodyRows = rows.slice(1);
    expect(bodyRows.length).toBe(ordered.length);

    // Each row shows the tier of the corresponding finding, in order.
    ordered.forEach((f, i) => {
      expect(within(bodyRows[i]).getByText(f.tier)).toBeInTheDocument();
    });

    // Tier sequence must be non-decreasing P1 -> P4.
    const tierSeq = ordered.map((f) => f.tier);
    const order = ['P1', 'P2', 'P3', 'P4'];
    for (let i = 0; i < tierSeq.length - 1; i++) {
      expect(order.indexOf(tierSeq[i])).toBeLessThanOrEqual(
        order.indexOf(tierSeq[i + 1]),
      );
    }
  });
});

describe('FindingDetailScreen affected ranges', () => {
  it('renders "no fixed version" for a range without one and "Fixed in" otherwise', () => {
    signInDemo();
    // finding-002 has one range with a fix and one without.
    renderWithProvider(<FindingDetailScreen findingId="finding-002" />);

    expect(screen.getByText('no fixed version')).toBeInTheDocument();
    expect(screen.getByText(/Fixed in/)).toBeInTheDocument();
  });
});

describe('RiskAcceptanceForm validation', () => {
  it('rejects a whitespace-only reason with a message and does not change status', async () => {
    signInDemo();
    const user = userEvent.setup();

    // Use an open finding.
    const open = mockServices
      .listFindings()
      .find((f) => f.status === 'open')!;
    renderWithProvider(<FindingDetailScreen findingId={open.id} />);

    const textarea = screen.getByLabelText(/Reason/);
    await user.type(textarea, '   ');
    await user.click(screen.getByRole('button', { name: /Accept risk/ }));

    expect(
      screen.getByText(/A reason is required to accept risk/),
    ).toBeInTheDocument();

    const after = mockServices.getFinding(open.id);
    expect(after?.status).toBe('open');
  });
});
