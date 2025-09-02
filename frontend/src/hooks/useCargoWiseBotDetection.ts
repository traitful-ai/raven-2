import { useEffect, useState } from 'react'
import useFetchChannelMembers, { Member } from './fetchers/useFetchChannelMembers'
import { useFrappeGetCall } from 'frappe-react-sdk'

/**
 * Hook to detect if the current channel is a DM with CargoWiseBot
 */
export const useCargoWiseBotDetection = (channelID: string, isDirectMessage: boolean) => {
    const [isCargoWiseBotChannel, setIsCargoWiseBotChannel] = useState(false)
    const { channelMembers } = useFetchChannelMembers(channelID)

    useEffect(() => {
        const checkForCargoWiseBot = async () => {
            if (!isDirectMessage || !channelMembers) {
                setIsCargoWiseBotChannel(false)
                return
            }

            try {
                // Get all members and check if any are bots
                const members = Object.values(channelMembers) as Member[]
                
                for (const member of members) {
                    if (member.type === 'Bot') {
                        // Get the bot details to check if it's CargoWiseBot
                        const response = await fetch(`/api/resource/Raven User/${member.name}`, {
                            headers: {
                                'Accept': 'application/json',
                                'Content-Type': 'application/json',
                            }
                        })
                        
                        if (response.ok) {
                            const ravenUser = await response.json()
                            if (ravenUser.data.bot) {
                                // Get the bot name
                                const botResponse = await fetch(`/api/resource/Raven Bot/${ravenUser.data.bot}`, {
                                    headers: {
                                        'Accept': 'application/json',
                                        'Content-Type': 'application/json',
                                    }
                                })
                                
                                if (botResponse.ok) {
                                    const botData = await botResponse.json()
                                    if (botData.data.bot_name === 'CargoWiseBot') {
                                        setIsCargoWiseBotChannel(true)
                                        return
                                    }
                                }
                            }
                        }
                    }
                }
                
                setIsCargoWiseBotChannel(false)
            } catch (error) {
                console.error('Error checking for CargoWiseBot:', error)
                setIsCargoWiseBotChannel(false)
            }
        }

        checkForCargoWiseBot()
    }, [isDirectMessage, channelMembers])

    return { isCargoWiseBotChannel }
}
