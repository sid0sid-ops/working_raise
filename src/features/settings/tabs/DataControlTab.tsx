import React from 'react';
import { SettingsDataControlTab, SettingsDataControlTabProps } from '../../../components/settings/SettingsDataControlTab';

export type DataControlTabProps = SettingsDataControlTabProps;

export const DataControlTab: React.FC<DataControlTabProps> = (props) => {
  return <SettingsDataControlTab {...props} />;
};
