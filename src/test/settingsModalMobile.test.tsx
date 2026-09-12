import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { RaisePage } from '../features/raise/RaisePage';

describe('Settings Modal Responsive & Mobile Behavior', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  const openSettings = () => {
    const userBtn = screen.queryByTestId('user-gateway-menu-btn');
    if (userBtn) {
      fireEvent.click(userBtn);
      const settingsBtn = screen.getByTestId('rail-settings-btn');
      fireEvent.click(settingsBtn);
    } else {
      const settingsBtn = screen.getByTestId('sidebar-settings-btn');
      fireEvent.click(settingsBtn);
    }
  };

  it('renders settings dialog with locked consistent height (h-[590px]) preventing size jumps', () => {
    render(<RaisePage />);

    // Open settings via user menu
    openSettings();

    const dialog = document.getElementById('settingsModalDialog');
    expect(dialog).not.toBeNull();
    // Verify fixed consistent sizing classes matching theme tab standard
    expect(dialog?.className).toContain('h-[590px]');
    expect(dialog?.className).toContain('max-h-[88vh]');
    expect(dialog?.className).toContain('max-w-3xl');
  });

  it('hides Grid & Light Tuner on mobile screens (hidden md:block)', () => {
    render(<RaisePage />);

    openSettings();

    // The heading for Grid & Light Tuner
    const tunerHeadings = screen.getAllByText(/Grid & Light Tuner/i);
    expect(tunerHeadings.length).toBeGreaterThan(0);

    // Find the container for Grid & Light Tuner section
    const tunerSection = tunerHeadings[0].closest('.space-y-3');
    expect(tunerSection).not.toBeNull();
    expect(tunerSection?.className).toContain('hidden');
    expect(tunerSection?.className).toContain('md:block');
  });

  it('supports mobile navigation: tapping a setting item navigates inside and reveals < Back button', () => {
    render(<RaisePage />);

    openSettings();

    // Initially on mobile menu, Back button is not visible
    expect(screen.queryByRole('button', { name: /Back to settings menu/i })).not.toBeInTheDocument();

    // Click Library to go inside that setting
    const libraryButtons = screen.getAllByRole('button', { name: /Library/i });
    fireEvent.click(libraryButtons[0]);

    // Back button should now be rendered for mobile screens
    const backBtn = screen.getByRole('button', { name: /Back to settings menu/i });
    expect(backBtn).toBeInTheDocument();

    // Clicking < Back leads user back to settings menu
    fireEvent.click(backBtn);
    expect(screen.queryByRole('button', { name: /Back to settings menu/i })).not.toBeInTheDocument();
  });

  it('switches between Theme and Library while maintaining scrollable inner content and consistent dialog size', () => {
    render(<RaisePage />);

    openSettings();

    const dialog = document.getElementById('settingsModalDialog');
    expect(dialog?.className).toContain('h-[590px]');

    // Navigate to Library
    const libraryButtons = screen.getAllByRole('button', { name: /Library/i });
    fireEvent.click(libraryButtons[0]);

    // Dialog size remains locked
    expect(dialog?.className).toContain('h-[590px]');
    expect(screen.getByPlaceholderText('Search documents...')).toBeInTheDocument();

    // Navigate to Theme
    const themeButtons = screen.getAllByRole('button', { name: /Theme/i });
    fireEvent.click(themeButtons[0]);

    // Dialog size still locked
    expect(dialog?.className).toContain('h-[590px]');
    expect(screen.getByText('Deep palette optimal for low light')).toBeInTheDocument();
  });
});
