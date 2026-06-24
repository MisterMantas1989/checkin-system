import React, { useEffect, useState, useContext } from 'react';
import {
  View, Text, StyleSheet, ActivityIndicator, Alert, TouchableOpacity
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';
import MapView, { Marker } from 'react-native-maps';
import { API_URL } from '@env';
import { useIsFocused } from '@react-navigation/native';
import { LoginContext } from '../context/LoginContext';
import * as Notifications from 'expo-notifications';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: false,
    shouldSetBadge: false,
  }),
});

export default function CheckinScreen() {
  const [location, setLocation] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [address, setAddress] = useState(null);

  const { logout } = useContext(LoginContext);
  const isFocused = useIsFocused();

  useEffect(() => {
    Notifications.requestPermissionsAsync();
  }, []);

  useEffect(() => {
    let mounted = true;

    const fetchAll = async () => {
      setLoading(true);
      try {
        const token = await AsyncStorage.getItem('token');
        if (!token) return logout();

        const { status: locStatus } = await Location.requestForegroundPermissionsAsync();
        if (locStatus !== 'granted') {
          Alert.alert('Platsåtkomst nekad');
          return;
        }

        const loc = await Location.getCurrentPositionAsync({});
        if (mounted) setLocation(loc.coords);

        const res = await fetch(`${API_URL}/api/status`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (res.status === 401) return logout();

        const data = await res.json();
        setStatus(data.status);
        setAddress(data.checkin_address || null);
      } catch (err) {
        Alert.alert('Fel', 'Kunde inte hämta plats eller status.');
      } finally {
        setLoading(false);
      }
    };

    if (isFocused) fetchAll();
    return () => { mounted = false; };
  }, [isFocused]);

  const sendLocalNotification = async (title, body) => {
    await Notifications.scheduleNotificationAsync({
      content: { title, body },
      trigger: null,
    });
  };

  const handleCheck = async (type) => {
    setLoading(true);
    try {
      const token = await AsyncStorage.getItem('token');
      if (!token) return logout();

      if (!location) {
        Alert.alert('Fel', 'Platsdata saknas');
        return;
      }

      const res = await fetch(`${API_URL}/api/${type === 'in' ? 'checkin' : 'checkout'}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          lat: location.latitude,
          lon: location.longitude,
        }),
      });

      const data = await res.json();

      if (res.status === 401) return logout();

      if (res.ok) {
        const action = type === 'in' ? 'incheckning' : 'utcheckning';
        await sendLocalNotification(`✅ Lyckad ${action}`, data.message);
        Alert.alert('OK', data.message);
        setStatus(type === 'in' ? 'in' : 'out');
        if (data.checkin_address) setAddress(data.checkin_address);
      } else {
        Alert.alert('Fel', data.error || 'Något gick fel');
      }
    } catch (err) {
      Alert.alert('Fel', 'Kunde inte kontakta servern');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#007aff" />
      </View>
    );
  }

  if (!location) {
    return (
      <View style={styles.centered}>
        <Text>Platsdata saknas.</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Din plats</Text>

      <MapView
        style={styles.map}
        initialRegion={{
          latitude: location.latitude,
          longitude: location.longitude,
          latitudeDelta: 0.005,
          longitudeDelta: 0.005,
        }}
      >
        <Marker coordinate={location} title="Du är här" />
      </MapView>

      {address && <Text style={styles.address}>Senaste plats: {address}</Text>}

      <TouchableOpacity
        style={[styles.button, status === 'in' ? styles.outBtn : styles.inBtn]}
        onPress={() => handleCheck(status === 'in' ? 'out' : 'in')}
      >
        <Text style={styles.btnText}>
          {status === 'in' ? 'Checka Ut' : 'Checka In'}
        </Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#fff' },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 12 },
  map: {
    width: '100%',
    height: 500,
    borderRadius: 16,
    marginBottom: 16,
    overflow: 'hidden',
  },
  address: {
    fontSize: 14,
    fontStyle: 'italic',
    color: '#555',
    marginBottom: 20,
    textAlign: 'center',
  },
  button: {
    paddingVertical: 16,
    borderRadius: 50,
    alignItems: 'center',
    marginHorizontal: 40,
    elevation: 4,
    shadowColor: '#000',
    shadowOpacity: 0.15,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 6,
  },
  inBtn: {
    backgroundColor: '#2ecc71',
  },
  outBtn: {
    backgroundColor: '#e74c3c',
  },
  btnText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    letterSpacing: 1,
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
});








