import React from 'react';
import { SettingsGatewayTab, SettingsGatewayTabProps } from '../../../components/settings/SettingsGatewayTab';

export type GatewayTabProps = SettingsGatewayTabProps;

export const GatewayTab: React.FC<GatewayTabProps> = (props) => {
  return <SettingsGatewayTab {...props} />;
};
