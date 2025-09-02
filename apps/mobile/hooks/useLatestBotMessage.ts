import { useFrappeGetCall } from 'frappe-react-sdk'
import { Message } from '../../../types/Messaging/Message'

interface GetMessagesResponse {
    message: {
        messages: Message[],
        has_old_messages: boolean
        has_new_messages: boolean
    }
}

export const useLatestBotMessage = (channelID: string, botName?: string) => {
    const { data, error, isLoading } = useFrappeGetCall<GetMessagesResponse>('raven.api.chat_stream.get_messages', {
        channel_id: channelID,
        limit_start: 0,
        limit_page_length: 20 // Get last 20 messages to find the most recent bot message
    }, undefined, {
        revalidateOnFocus: true,
        refreshInterval: 2000 // Poll every 2 seconds for new messages
    })

    const latestBotMessage = data?.message?.messages?.find((message: Message) => 
        message.is_bot_message === 1 && 
        (!botName || message.bot === botName) &&
        message.message_type === 'Text' &&
        message.text
    )

    const parseMessageAsJSON = (message?: Message): any => {
        if (!message?.text) return null
        
        try {
            // Try to parse the message text as JSON
            return JSON.parse(message.text)
        } catch (e) {
            // If it's not JSON, try to extract JSON from the text
            const jsonMatch = message.text.match(/\{[\s\S]*\}/)
            if (jsonMatch) {
                try {
                    return JSON.parse(jsonMatch[0])
                } catch (e2) {
                    return null
                }
            }
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
