import type React from 'react';
import {
  SettingsLibraryTab,
  type SettingsLibraryTabProps,
} from '../../../components/settings/SettingsLibraryTab';

export type LibraryTabProps = SettingsLibraryTabProps;

export const LibraryTab: React.FC<LibraryTabProps> = (props) => {
  return <SettingsLibraryTab {...props} />;
};
