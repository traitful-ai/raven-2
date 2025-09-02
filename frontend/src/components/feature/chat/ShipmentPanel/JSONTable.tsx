import { useState } from 'react'
import { Table, Text, Box } from '@radix-ui/themes'

interface JSONTableProps {
    data: any
    title?: string
}

export const JSONTable = ({ data, title }: JSONTableProps) => {
    if (!data || typeof data !== 'object') {
        return (
            <Text size="2" className="text-blue-600 dark:text-blue-300">
                No valid JSON data to display
            </Text>
        )
    }

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

    const entries = Object.entries(data)

    if (entries.length === 0) {
        return (
            <Text size="2" className="text-blue-600 dark:text-blue-300">
                Empty data object
            </Text>
        )
    }

    return (
        <Box>
            {title && (
                <Text size="3" weight="bold" className="text-blue-700 dark:text-blue-400 mb-3 block">
                    {title}
                </Text>
            )}
            <Table.Root variant="surface" className="w-full">
                <Table.Header>
                    <Table.Row>
                        <Table.ColumnHeaderCell>Field</Table.ColumnHeaderCell>
                        <Table.ColumnHeaderCell>Value</Table.ColumnHeaderCell>
                    </Table.Row>
                </Table.Header>
                <Table.Body>
                    {entries.map(([key, value], index) => (
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
    )
}
