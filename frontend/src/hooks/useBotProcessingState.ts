import { useFrappeEventListener } from 'frappe-react-sdk'
import { useState } from 'react'

interface BotProcessingState {
    isProcessing: boolean
    botName?: string
}

/**
 * Hook to track bot processing state for a specific channel
 * Listens to bot_processing_start and bot_processing_end events
 */
export const useBotProcessingState = (channelID: string): BotProcessingState => {
    const [processingState, setProcessingState] = useState<BotProcessingState>({
        isProcessing: false,
        botName: undefined
    })

    // Listen for bot processing start events
    useFrappeEventListener("bot_processing_start", (data) => {
        if (data.channel_id === channelID) {
            console.log(`🔔 Frontend received bot_processing_start for channel ${channelID}:`, data)
            setProcessingState({
                isProcessing: true,
                botName: data.bot_name
            })
        }
    })

    // Listen for bot processing end events
    useFrappeEventListener("bot_processing_end", (data) => {
        if (data.channel_id === channelID) {
            console.log(`🔔 Frontend received bot_processing_end for channel ${channelID}:`, data)
            setProcessingState({
                isProcessing: false,
                botName: undefined
            })
        }
    })

    return processingState
}
