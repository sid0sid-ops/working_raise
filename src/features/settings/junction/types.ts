export type SettingsTab =
  | 'theme'
  | 'library'
  | 'data-control'
  | 'gateway'
  | 'voice'
  | 'help'
  | 'about';

export type SettingsMobileView = 'menu' | 'detail';

export interface SettingsJunctionState {
  isOpen: boolean;
  activeTab: SettingsTab;
  mobileView: SettingsMobileView;
  isTunerMode: boolean;
  showOutsideClickTip: boolean;
}

export interface SettingsJunctionActions {
  open: (tab?: SettingsTab) => void;
  close: () => void;
  toggle: (tab?: SettingsTab) => void;
  setTab: (tab: SettingsTab) => void;
  setMobileView: (view: SettingsMobileView) => void;
  setTunerMode: (isTuner: boolean) => void;
  setShowOutsideClickTip: (show: boolean) => void;
  reset: () => void;
}

export type SettingsJunctionStore = SettingsJunctionState & SettingsJunctionActions;
