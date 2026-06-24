import React, { useEffect, useState } from 'react';
import {
  View, Text, FlatList, StyleSheet, ActivityIndicator, Alert
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { API_URL } from '@env';

const dummySchedule = [
  { id: '1', day: "Måndag", shift: "08:00 - 16:00" },
  { id: '2', day: "Tisdag", shift: "10:00 - 18:00" },
  { id: '3', day: "Onsdag", shift: "Ledig" },
  { id: '4', day: "Torsdag", shift: "12:00 - 20:00" },
  { id: '5', day: "Fredag", shift: "07:00 - 15:00" },
  { id: '6', day: "Lördag", shift: "Ledig" },
  { id: '7', day: "Söndag", shift: "Ledig" },
];

export default function ScheduleScreen() {
  const [schedule, setSchedule] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSchedule();
  }, []);

  const fetchSchedule = async () => {
    setLoading(true);
    try {
      const token = await AsyncStorage.getItem("token");
      if (!token) throw new Error("Ingen token hittad");

      console.log("🔐 Token:", token);
      console.log("📡 Anropar:", `${API_URL}/api/schema`);

      const res = await fetch(`${API_URL}/api/schema`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      const raw = await res.text();
      console.log("📥 Rådata:", raw);

      let data = {};
      try {
        data = JSON.parse(raw);
      } catch {
        throw new Error("Kunde inte tolka JSON-svar");
      }

      if (res.ok) {
        console.log("✅ Schema-data hämtad:", data);
        setSchedule(data.schema || []);
      } else {
        throw new Error(data?.error || "Fel från servern");
      }
    } catch (err) {
      console.warn("❌ Schemafel:", err.message);
      Alert.alert("Fel", "Kunde inte ladda schema: " + err.message);
      setSchedule(dummySchedule);
    } finally {
      setLoading(false);
    }
  };

  const renderItem = ({ item }) => {
    const title = item.day || item.Datum || "Okänd dag";
    const time = item.shift || (item.Starttid && item.Sluttid ? `${item.Starttid} - ${item.Sluttid}` : "Ingen tid");
    const address = item.Adress || "";
    const comment = item.Kommentar || "";

    return (
      <View style={styles.item}>
        <Text style={styles.day}>{title}</Text>
        <Text style={styles.shift}>{time}</Text>
        {address ? <Text style={styles.meta}>📍 {address}</Text> : null}
        {comment ? <Text style={styles.meta}>💬 {comment}</Text> : null}
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Ditt schema</Text>
      {loading ? (
        <ActivityIndicator size="large" color="#1abc9c" />
      ) : (
        <FlatList
          data={schedule}
          keyExtractor={(item, index) => `${item.Datum || item.day || index}-${item.Starttid || ""}`}
          renderItem={renderItem}
          ListEmptyComponent={
            <Text style={styles.empty}>Inget schema hittades.</Text>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, backgroundColor: "#fff" },
  title: { fontSize: 24, fontWeight: "bold", marginBottom: 15, color: "#222" },
  item: {
    paddingVertical: 12,
    borderBottomColor: '#eee',
    borderBottomWidth: 1,
  },
  day: { fontSize: 16, fontWeight: "600", color: "#333" },
  shift: { fontSize: 15, color: '#555' },
  meta: { fontSize: 13, color: '#777', marginTop: 4 },
  empty: { textAlign: "center", color: "#999", marginTop: 40 },
});









