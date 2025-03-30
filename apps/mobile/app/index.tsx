import { Stack, useRouter } from 'expo-router';
import FullPageLoader from '@components/layout/FullPageLoader';
import { useAsyncStorage } from '@react-native-async-storage/async-storage';
import { useEffect } from 'react';
import { getMessaging } from '@react-native-firebase/messaging';
import { setDefaultSite } from '@lib/auth';
const messaging = getMessaging()

export default function InitialScreen() {

    const router = useRouter();

    const { getItem } = useAsyncStorage(`default-site`)


    useEffect(() => {

        const onMount = async () => {
            // Get the defualt site from the async storage
            // Also check if the app was started by a notification
            const initialNotification = await messaging.getInitialNotification();

            if (initialNotification) {
                if (initialNotification.data?.channel_id && initialNotification.data?.sitename) {
                    setDefaultSite(initialNotification.data.sitename as string)
                    let path = 'chat'
                    if (initialNotification.data.is_thread) {
                        path = 'thread'
                    }
                    router.navigate(`/${initialNotification.data.sitename}/${path}/${initialNotification.data.channel_id}`, {
                        withAnchor: true
                    })

                    return
                }
            }

            // If not started by notification
            // On load, check if the user has a site set
            const defaultSite = await getItem()
            if (defaultSite) {
                router.replace(`/${defaultSite}`)
            } else {
                router.replace('/landing')
            }
        }

        // Handle notification open when app is in background
        const unsubscribeOnNotificationOpen = messaging.onNotificationOpenedApp(async (remoteMessage) => {
            console.log('Notification opened app from background state:', remoteMessage);
            if (remoteMessage.data?.channel_id && remoteMessage.data?.sitename) {
                setDefaultSite(remoteMessage.data.sitename as string)
                let path = 'chat'
                if (remoteMessage.data.is_thread) {
                    path = 'thread'
                }
                router.navigate(`/${remoteMessage.data.sitename}/${path}/${remoteMessage.data.channel_id}`, {
                    withAnchor: true
                })
            }
        });

        onMount()
        // Cleanup function
        return () => {
            unsubscribeOnNotificationOpen();
        };
    }, []);

    return (
        <>
            <Stack.Screen options={{ title: 'Raven' }} />
            <FullPageLoader />
        </>
    );
}