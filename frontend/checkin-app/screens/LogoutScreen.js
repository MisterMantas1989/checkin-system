import React, { useEffect, useContext } from 'react';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { LoginContext } from '../context/LoginContext';

export default function LogoutScreen() {
  const { logout } = useContext(LoginContext);

  useEffect(() => {
    logout(); // 👈 Triggar navigationen via context
  }, []);

  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center' },
});



