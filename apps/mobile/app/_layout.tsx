import { Slot, usePathname, useRouter } from 'expo-router';
import { ShareIntentProvider, useShareIntentContext } from "expo-share-intent";
import { ThemeProvider } from '@react-navigation/native';
import "../global.css";
import { useEffect } from 'react';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { BottomSheetModalProvider } from '@gorhom/bottom-sheet';
import { useColorScheme, useInitialAndroidBarSync } from '@hooks/useColorScheme';
import { NAV_THEME } from '@theme/index';
import { StatusBar } from 'expo-status-bar';
import { ActionSheetProvider } from '@expo/react-native-action-sheet';
import { PortalHost } from '@rn-primitives/portal';
import { KeyboardProvider } from 'react-native-keyboard-controller';
import { Toaster } from 'sonner-native';
import { LogBox } from 'react-native';
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'
import advancedFormat from 'dayjs/plugin/advancedFormat'
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(utc)
dayjs.extend(timezone)
dayjs.extend(advancedFormat)
dayjs.extend(relativeTime)

/** Suppressing this for now - see https://github.com/meliorence/react-native-render-html/issues/661 */
LogBox.ignoreLogs([
    /Support for defaultProps will be removed/,
]);

if (__DEV__) {
    LogBox.ignoreLogs([
        /Support for defaultProps will be removed/,
    ]);
}

export default function RootLayout() {

    const router = useRouter();

    const { hasShareIntent } = useShareIntentContext();

    useEffect(() => {
        if (hasShareIntent) {
            // we want to handle share intent event in a specific page
            console.debug("[expo-router-index] redirect to ShareIntent screen");
            router.replace({
                pathname: "shareintent",
            });
        }
    }, [hasShareIntent]);

    const path = usePathname()
    console.log(path)

    useInitialAndroidBarSync();
    const { colorScheme, isDarkColorScheme } = useColorScheme();

    return (
        <ShareIntentProvider
            options={{
                debug: true,
                resetOnBackground: true,
                onResetShareIntent: () =>
                    // used when app going in background and when the reset button is pressed
                    router.replace({
                        pathname: "/",
                    }),
            }}
        >
            <StatusBar
                key={`root-status-bar-${isDarkColorScheme ? 'light' : 'dark'}`}
                style={isDarkColorScheme ? 'light' : 'dark'}
            />
            <GestureHandlerRootView style={{ flex: 1 }}>
                <BottomSheetModalProvider>
                    <ActionSheetProvider>
                        <KeyboardProvider statusBarTranslucent navigationBarTranslucent>
                            <ThemeProvider value={NAV_THEME[colorScheme]}>
                                <Slot />
                                <PortalHost />
                            </ThemeProvider>
                        </KeyboardProvider>
                    </ActionSheetProvider>
                </BottomSheetModalProvider>
                <Toaster
                    position="top-center"
                    duration={2000}
                    visibleToasts={4}
                    closeButton={true}
                    toastOptions={{}}
                    pauseWhenPageIsHidden
                    theme={isDarkColorScheme ? 'dark' : 'light'}
                    swipeToDismissDirection='up'
                />
            </GestureHandlerRootView>
        </ShareIntentProvider>
    )
}