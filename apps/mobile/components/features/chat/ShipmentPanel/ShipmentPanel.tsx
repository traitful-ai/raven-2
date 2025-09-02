import { useState } from 'react'
import { View, Text, TouchableOpacity, ScrollView } from 'react-native'
import { useLatestBotMessage } from '../../../hooks/useLatestBotMessage'

interface ShipmentPanelProps {
    channelID: string
}

export const ShipmentPanel = ({ channelID }: ShipmentPanelProps) => {
    const [isExpanded, setIsExpanded] = useState(true)
    const { latestBotMessage, jsonData, isLoading } = useLatestBotMessage(channelID, 'CargoWiseBot')

    const renderTableRow = (key: string, value: any, index: number) => {
        let displayValue = ''
        
        if (value === null || value === undefined) {
            displayValue = 'null'
        } else if (typeof value === 'boolean') {
            displayValue = value ? 'true' : 'false'
        } else if (typeof value === 'object') {
            if (Array.isArray(value)) {
                displayValue = `[${value.length} items]`
            } else {
                displayValue = JSON.stringify(value)
            }
        } else {
            displayValue = String(value)
        }

        return (
            <View 
                key={index}
                style={{
                    flexDirection: 'row',
                    borderBottomWidth: 1,
                    borderBottomColor: '#E5E7EB',
                    paddingVertical: 8
                }}
            >
                <View style={{ flex: 1, paddingRight: 8 }}>
                    <Text style={{ 
                        fontSize: 14, 
                        fontWeight: '500', 
                        color: '#1D4ED8' 
                    }}>
                        {key}
                    </Text>
                </View>
                <View style={{ flex: 2 }}>
                    <Text style={{ 
                        fontSize: 14, 
                        color: '#374151' 
                    }}>
                        {displayValue}
                    </Text>
                </View>
            </View>
        )
    }

    return (
        <View 
            style={{
                margin: 8,
                borderWidth: 1,
                borderColor: '#93C5FD',
                borderRadius: 8,
                backgroundColor: '#EFF6FF'
            }}
        >
            <View style={{
                padding: 8,
                borderBottomWidth: 1,
                borderBottomColor: '#BFDBFE'
            }}>
                <TouchableOpacity
                    style={{
                        flexDirection: 'row',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                    }}
                    onPress={() => setIsExpanded(!isExpanded)}
                >
                    <Text style={{
                        fontSize: 16,
                        fontWeight: 'bold',
                        color: '#1D4ED8'
                    }}>
                        SHIPMENT PANEL
                    </Text>
                    <Text style={{
                        fontSize: 14,
                        color: '#1D4ED8'
                    }}>
                        {isExpanded ? '▲' : '▼'}
                    </Text>
                </TouchableOpacity>
            </View>
            
            {isExpanded && (
                <View style={{ padding: 16 }}>
                    <Text style={{
                        fontSize: 14,
                        color: '#2563EB',
                        marginBottom: 12
                    }}>
                        Channel: {channelID}
                    </Text>
                    
                    {isLoading && (
                        <Text style={{
                            fontSize: 14,
                            color: '#2563EB'
                        }}>
                            Loading latest shipment data...
                        </Text>
                    )}
                    
                    {jsonData ? (
                        <View>
                            <Text style={{
                                fontSize: 16,
                                fontWeight: 'bold',
                                color: '#1D4ED8',
                                marginBottom: 12
                            }}>
                                Latest Shipment Data
                            </Text>
                            
                            <View style={{
                                borderWidth: 1,
                                borderColor: '#E5E7EB',
                                borderRadius: 4,
                                overflow: 'hidden'
                            }}>
                                {/* Table Header */}
                                <View style={{
                                    flexDirection: 'row',
                                    backgroundColor: '#F3F4F6',
                                    paddingVertical: 8,
                                    paddingHorizontal: 12
                                }}>
                                    <View style={{ flex: 1 }}>
                                        <Text style={{ 
                                            fontSize: 14, 
                                            fontWeight: 'bold',
                                            color: '#374151' 
                                        }}>
                                            Field
                                        </Text>
                                    </View>
                                    <View style={{ flex: 2 }}>
                                        <Text style={{ 
                                            fontSize: 14, 
                                            fontWeight: 'bold',
                                            color: '#374151' 
                                        }}>
                                            Value
                                        </Text>
                                    </View>
                                </View>
                                
                                {/* Table Body */}
                                <ScrollView style={{ maxHeight: 300 }}>
                                    <View style={{ paddingHorizontal: 12 }}>
                                        {Object.keys(jsonData).map((key, index) => 
                                            renderTableRow(key, jsonData[key], index)
                                        )}
                                    </View>
                                </ScrollView>
                            </View>
                        </View>
                    ) : latestBotMessage ? (
                        <Text style={{
                            fontSize: 14,
                            color: '#2563EB'
                        }}>
                            Latest bot message doesn't contain valid JSON data
                        </Text>
                    ) : (
                        <Text style={{
                            fontSize: 14,
                            color: '#2563EB'
                        }}>
                            No bot messages found in this channel
                        </Text>
                    )}
                </View>
            )}
        </View>
    )
}
