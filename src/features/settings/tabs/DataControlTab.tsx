import type React from 'react';
import {
  SettingsDataControlTab,
  type SettingsDataControlTabProps,
} from '../../../components/settings/SettingsDataControlTab';

export type DataControlTabProps = SettingsDataControlTabProps;

export const DataControlTab: React.FC<DataControlTabProps> = (props) => {
  return <SettingsDataControlTab {...props} />;
};
