import { useState } from 'react'
import { Box, Text, Button, Table } from '@radix-ui/themes'
import { Stack } from '@/components/layout/Stack'
import { useLatestBotMessage } from '@/hooks/useLatestBotMessage'

interface ShipmentPanelProps {
    channelID: string
}

export const ShipmentPanel = ({ channelID }: ShipmentPanelProps) => {
    const [isExpanded, setIsExpanded] = useState(true)
    const { latestBotMessage, jsonData, isLoading, error } = useLatestBotMessage(channelID, 'CargoWiseBot')

    // Debug logging
    console.log('ShipmentPanel Debug:', {
        channelID,
        isLoading,
        error,
        hasLatestBotMessage: !!latestBotMessage,
        latestBotMessageText: latestBotMessage?.text?.substring(0, 100),
        hasJsonData: !!jsonData,
        jsonData
    })

    const renderValue = (value: any) => {
        if (value === null || value === undefined) {
            return <Text size="1" color="gray">null</Text>
        }
        
        if (typeof value === 'boolean') {
            return <Text size="2">{value ? 'true' : 'false'}</Text>
        }
        
        if (typeof value === 'object') {
            if (Array.isArray(value)) {
                return <Text size="2">[{value.length} items]</Text>
            }
            return <Text size="2">{JSON.stringify(value)}</Text>
        }
        
        return <Text size="2">{String(value)}</Text>
    }

    return (
        <Box 
            className="m-2 border border-blue-300 rounded-lg bg-blue-50 dark:bg-blue-950/20 dark:border-blue-700"
        >
            <Box className="p-2 border-b border-blue-200 dark:border-blue-800">
                <Button
                    variant="ghost"
                    size="2"
                    className="w-full justify-between text-blue-700 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/30"
                    onClick={() => setIsExpanded(!isExpanded)}
                >
                    <Text size="3" weight="bold">
                        SHIPMENT PANEL
                    </Text>
                    <Text size="2">
                        {isExpanded ? '▲' : '▼'}
                    </Text>
                </Button>
            </Box>
            {isExpanded && (
                <Box className="p-4">
                    <Stack gap="3">
                        <Text size="2" className="text-blue-600 dark:text-blue-300">
                            Channel: {channelID}
                        </Text>
                        
                        {isLoading && (
                            <Text size="2" className="text-blue-600 dark:text-blue-300">
                                Loading latest shipment data...
                            </Text>
                        )}
                        
                        {jsonData ? (
                            <Box>
                                <Text size="3" weight="bold" className="text-blue-700 dark:text-blue-400 mb-3 block">
                                    Latest Shipment Data
                                </Text>
                                <Table.Root variant="surface" className="w-full">
                                    <Table.Header>
                                        <Table.Row>
                                            <Table.ColumnHeaderCell>Field</Table.ColumnHeaderCell>
                                            <Table.ColumnHeaderCell>Value</Table.ColumnHeaderCell>
                                        </Table.Row>
                                    </Table.Header>
                                    <Table.Body>
                                        {Object.entries(jsonData).map(([key, value], index) => (
                                            <Table.Row key={index}>
                                                <Table.Cell>
                                                    <Text size="2" weight="medium" className="text-blue-700 dark:text-blue-300">
                                                        {key}
                                                    </Text>
                                                </Table.Cell>
                                                <Table.Cell>
                                                    {renderValue(value)}
                                                </Table.Cell>
                                            </Table.Row>
                                        ))}
                                    </Table.Body>
                                </Table.Root>
                            </Box>
                        ) : latestBotMessage ? (
                            <Box>
                                <Text size="2" className="text-blue-600 dark:text-blue-300">
                                    Latest bot message doesn't contain valid JSON data
                                </Text>
                                <Text size="1" className="text-gray-500 mt-2 font-mono">
                                    Debug: Bot message text: {latestBotMessage.text?.substring(0, 200)}...
                                </Text>
                            </Box>
                        ) : (
                            <Box>
                                <Text size="2" className="text-blue-600 dark:text-blue-300">
                                    No bot messages found in this channel
                                </Text>
                                <Text size="1" className="text-gray-500 mt-2">
                                    Debug: Loading={isLoading ? 'true' : 'false'}, Error={error ? 'yes' : 'no'}
                                </Text>
                            </Box>
                        )}
                    </Stack>
                </Box>
            )}
        </Box>
    )
}
