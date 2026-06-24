import React, { useState, useContext, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  Pressable,
  StyleSheet,
  Alert,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
  Image,
  TouchableOpacity,
  Animated,
} from 'react-native';
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import { LoginContext } from '../context/LoginContext';

import { API_URL } from '@env';

export default function LoginScreen() {
  const [namn, setNamn] = useState('');
  const [lösenord, setLösenord] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loginSuccess, setLoginSuccess] = useState(false);
  const [pushToken, setPushToken] = useState(null);
  const [buttonAnim] = useState(new Animated.Value(1));

  const { login } = useContext(LoginContext);

  useEffect(() => {
    const registerForPush = async () => {
      if (!Device.isDevice) return;
      const { status } = await Notifications.getPermissionsAsync();
      let finalStatus = status;

      if (status !== 'granted') {
        const res = await Notifications.requestPermissionsAsync();
        finalStatus = res.status;
      }

      if (finalStatus !== 'granted') {
        Alert.alert('Notiser', 'Tillåt pushnotiser för att få schemaändringar.');
        return;
      }

      const tokenRes = await Notifications.getExpoPushTokenAsync();
      setPushToken(tokenRes.data);
      console.log("📱 Push-token från Expo:", tokenRes.data);
    };

    registerForPush();
  }, []);

  const animateButton = (toValue) => {
    Animated.timing(buttonAnim, {
      toValue,
      duration: 300,
      useNativeDriver: true,
    }).start();
  };

  const handleLogin = async () => {
    if (!namn || !lösenord) {
      Alert.alert("Fel", "Fyll i både användarnamn och lösenord");
      return;
    }

    const trimmedNamn = namn.trim();
    const trimmedLösenord = lösenord.trim();
    const body = { name: trimmedNamn, password: trimmedLösenord, pushToken };

    console.log("🧪 Skickas till servern:", JSON.stringify(body));

    setLoading(true);
    animateButton(0.95);
    try {
      const res = await fetch(`${API_URL}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });

      const rawText = await res.text();
      let data;
      try {
        data = JSON.parse(rawText);
      } catch {
        Alert.alert("Fel", "Ogiltigt svar från servern");
        return;
      }

      if (res.ok) {
        animateButton(1);
        setLoginSuccess(true);
        await login(data.token);
      } else {
        animateButton(1);
        Alert.alert("Fel", data.error || "Inloggning misslyckades");
      }
    } catch (err) {
      animateButton(1);
      Alert.alert("Fel", "Kunde inte ansluta till servern. Kontrollera WiFi.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={styles.wrapper}
      >
        <View style={styles.container}>
          <Image source={require('../assets/logo.png')} style={styles.logo} />
          <Text style={styles.title}>Logga in</Text>

          <TextInput
            placeholder="Användarnamn"
            style={styles.input}
            value={namn}
            onChangeText={setNamn}
            autoCapitalize="none"
          />

          <View style={styles.passwordWrapper}>
            <TextInput
              placeholder="Lösenord"
              style={[styles.input, { flex: 1, borderWidth: 0, marginBottom: 0 }]}
              value={lösenord}
              onChangeText={setLösenord}
              secureTextEntry={!showPassword}
              autoCapitalize="none"
            />
            <TouchableOpacity onPress={() => setShowPassword(!showPassword)}>
              <Text style={{ marginLeft: 10, fontSize: 16 }}>
                {showPassword ? '🙈' : '👁'}
              </Text>
            </TouchableOpacity>
          </View>

          <Animated.View style={{ transform: [{ scale: buttonAnim }], width: '100%' }}>
            <Pressable style={styles.button} onPress={handleLogin} disabled={loading}>
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : loginSuccess ? (
                <Text style={styles.buttonText}>✔ Klart</Text>
              ) : (
                <Text style={styles.buttonText}>Logga in</Text>
              )}
            </Pressable>
          </Animated.View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#f8f9fa" },
  wrapper: { flex: 1 },
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },
logo: {
  width: 280,         
  height: 200,        
  resizeMode: 'contain',
  marginBottom: 40,
  },
  title: {
    fontSize: 32,
    marginBottom: 32,
    fontWeight: 'bold',
    color: "#222",
  },
  input: {
    width: "100%",
    height: 50,
    borderColor: "#ddd",
    borderWidth: 1,
    marginBottom: 18,
    paddingHorizontal: 16,
    borderRadius: 14,
    fontSize: 18,
    backgroundColor: "#fff",
  },
  passwordWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    width: '100%',
    borderColor: '#ddd',
    borderWidth: 1,
    borderRadius: 14,
    backgroundColor: '#fff',
    marginBottom: 18,
    paddingHorizontal: 12,
  },
  button: {
    width: "100%",
    height: 52,
    backgroundColor: "#1abc9c",
    borderRadius: 16,
    justifyContent: "center",
    alignItems: "center",
    marginTop: 10,
    shadowColor: "#1abc9c",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.23,
    shadowRadius: 4.62,
    elevation: 4,
  },
  buttonText: {
    color: "#fff",
    fontSize: 20,
    fontWeight: "bold",
    letterSpacing: 1,
  },
});
















