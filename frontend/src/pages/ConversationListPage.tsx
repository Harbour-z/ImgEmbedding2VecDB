import React from 'react';
import { Layout, Typography } from 'antd';
import { ConversationHistory } from '../components/conversation/ConversationHistory';

const { Content } = Layout;
const { Title } = Typography;

export const ConversationListPage: React.FC = () => {
    return (
            <Content style={{ padding: '24px', minHeight: 'calc(100vh - 64px)' }}>
                <Title level={2} style={{ marginBottom: 24 }}>
                    对话历史
                </Title>
                <ConversationHistory />
            </Content>
    );
};
