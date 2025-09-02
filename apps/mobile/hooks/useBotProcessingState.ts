import { useFrappeEventListener } from '@raven/lib/hooks/useFrappeEventListener'
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
    useFrappeEventListener("bot_processing_start", (data: any) => {
        if (data.channel_id === channelID) {
            setProcessingState({
                isProcessing: true,
                botName: data.bot_name
            })
        }
    })

    // Listen for bot processing end events
    useFrappeEventListener("bot_processing_end", (data: any) => {
        if (data.channel_id === channelID) {
            setProcessingState({
                isProcessing: false,
                botName: undefined
            })
        }
    })

    return processingState
}
