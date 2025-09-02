import { useFrappeGetCall } from 'frappe-react-sdk'
import { GetMessagesResponse } from '@/components/feature/chat/ChatStream/useChatStream'
import { Message } from '../../../types/Messaging/Message'

export const useLatestBotMessage = (channelID: string, botName?: string) => {
    const { data, error, isLoading } = useFrappeGetCall<GetMessagesResponse>('raven.api.chat_stream.get_messages', {
        channel_id: channelID,
        limit_start: 0,
        limit_page_length: 20 // Get last 20 messages to find the most recent bot message
    }, undefined, {
        revalidateOnFocus: true,
        refreshInterval: 2000 // Poll every 2 seconds for new messages
    })

    // Debug logging
    console.log('useLatestBotMessage Debug:', {
        channelID,
        botName,
        isLoading,
        error,
        messagesCount: data?.message?.messages?.length,
        messages: data?.message?.messages?.map(m => ({
            name: m.name,
            owner: m.owner,
            is_bot_message: m.is_bot_message,
            bot: m.bot,
            message_type: m.message_type,
            text: m.text?.substring(0, 100) + '...' // First 100 chars
        }))
    })

    const latestBotMessage = data?.message?.messages
        ?.slice() // Create a copy to avoid mutating original array
        ?.reverse() // Reverse to get most recent first (if they're in chronological order)
        ?.find((message: Message) => {
            const isBotMessage = message.is_bot_message === 1
            const matchesBot = !botName || message.bot === botName
            const isTextMessage = message.message_type === 'Text'
            const hasText = !!message.text
            
            console.log('Message check:', {
                name: message.name,
                isBotMessage,
                matchesBot,
                isTextMessage,
                hasText,
                bot: message.bot,
                text: message.text?.substring(0, 50)
            })
            
            return isBotMessage && matchesBot && isTextMessage && hasText
        })

    console.log('Found bot message:', latestBotMessage?.name)

    const parseMessageAsJSON = (message?: Message): any => {
        if (!message?.text) return null
        
        console.log('Parsing message text:', message.text)
        
        try {
            // Try to parse the message text as JSON
            const parsed = JSON.parse(message.text)
            console.log('Successfully parsed as JSON:', parsed)
            return parsed
        } catch (e) {
            console.log('Failed to parse as direct JSON, trying to extract:', e)
            // If it's not JSON, try to extract JSON from the text
            const jsonMatch = message.text.match(/\{[\s\S]*\}/)
            if (jsonMatch) {
                try {
                    const parsed = JSON.parse(jsonMatch[0])
                    console.log('Successfully extracted and parsed JSON:', parsed)
                    return parsed
                } catch (e2) {
                    console.log('Failed to parse extracted JSON:', e2)
                    return null
                }
            }
            console.log('No JSON pattern found in text')
            return null
        }
    }

    const jsonData = parseMessageAsJSON(latestBotMessage)

    return {
        latestBotMessage,
        jsonData,
        isLoading,
        error
    }
}
