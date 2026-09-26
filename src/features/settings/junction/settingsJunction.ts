import { create } from 'zustand';
import type { SettingsJunctionStore, SettingsMobileView, SettingsTab } from './types';

export const useSettingsJunctionStore = create<SettingsJunctionStore>((set, get) => ({
  isOpen: false,
  activeTab: 'theme',
  mobileView: 'menu',
  isTunerMode: false,
  showOutsideClickTip: false,

  open: (tab?: SettingsTab) => {
    set({
      isOpen: true,
      activeTab: tab || get().activeTab,
      mobileView: tab ? 'detail' : 'menu',
      isTunerMode: false,
      showOutsideClickTip: false,
    });
  },

  close: () => {
    set({
      isOpen: false,
      isTunerMode: false,
      showOutsideClickTip: false,
      mobileView: 'menu',
    });
  },

  toggle: (tab?: SettingsTab) => {
    const { isOpen } = get();
    if (isOpen) {
      get().close();
    } else {
      get().open(tab);
    }
  },

  setTab: (tab: SettingsTab) => {
    set({
      activeTab: tab,
      mobileView: 'detail',
    });
  },

  setMobileView: (mobileView: SettingsMobileView) => {
    set({ mobileView });
  },

  setTunerMode: (isTunerMode: boolean) => {
    set({ isTunerMode, showOutsideClickTip: false });
  },

  setShowOutsideClickTip: (showOutsideClickTip: boolean) => {
    set({ showOutsideClickTip });
  },

  reset: () => {
    set({
      isOpen: false,
      activeTab: 'theme',
      mobileView: 'menu',
      isTunerMode: false,
      showOutsideClickTip: false,
    });
  },
}));

/**
 * Systematic Junction Point API
 * Allows calling settings from anywhere across the application (React components,
 * global event listeners, services, hotkeys, banners).
 */
export const settingsJunction = {
  open: (tab?: SettingsTab) => useSettingsJunctionStore.getState().open(tab),
  close: () => useSettingsJunctionStore.getState().close(),
  toggle: (tab?: SettingsTab) => useSettingsJunctionStore.getState().toggle(tab),
  setTab: (tab: SettingsTab) => useSettingsJunctionStore.getState().setTab(tab),
  setMobileView: (view: SettingsMobileView) =>
    useSettingsJunctionStore.getState().setMobileView(view),
  setTunerMode: (isTuner: boolean) => useSettingsJunctionStore.getState().setTunerMode(isTuner),
  setShowOutsideClickTip: (show: boolean) =>
    useSettingsJunctionStore.getState().setShowOutsideClickTip(show),
  getState: () => useSettingsJunctionStore.getState(),
  subscribe: useSettingsJunctionStore.subscribe,
};

export const useSettingsJunction = useSettingsJunctionStore;
