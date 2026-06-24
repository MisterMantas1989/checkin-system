import React, { useContext } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { ActivityIndicator, View } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

import LoginScreen from './screens/LoginScreen';
import MainDrawer from './navigation/DrawerNavigator';
import { LoginProvider, LoginContext } from './context/LoginContext';

const Stack = createNativeStackNavigator();

function AppNavigator() {
  const { isLoggedIn, loading } = useContext(LoginContext);

  if (loading) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color="#1abc9c" />
      </View>
    );
  }

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      {isLoggedIn ? (
        <Stack.Screen name="MainDrawer" component={MainDrawer} />
      ) : (
        <Stack.Screen name="Login" component={LoginScreen} />
      )}
    </Stack.Navigator>
  );
}

export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <LoginProvider>
        <NavigationContainer>
          <AppNavigator />
        </NavigationContainer>
      </LoginProvider>
    </GestureHandlerRootView>
  );
}





