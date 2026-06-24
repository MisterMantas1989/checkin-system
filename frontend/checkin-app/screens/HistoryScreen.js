import React, { useEffect, useState } from 'react';
import {
  View, Text, FlatList, StyleSheet, ActivityIndicator, Alert
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useIsFocused } from '@react-navigation/native';

import { API_URL } from '@env';

export default function HistoryScreen() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const isFocused = useIsFocused();

  useEffect(() => {
    if (isFocused) {
      fetchHistory();
    }
  }, [isFocused]);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const token = await AsyncStorage.getItem("token");
      if (!token) throw new Error("Ingen token sparad");

      const res = await fetch(`${API_URL}/api/history`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      const text = await res.text();
      let data = {};
      try {
        data = JSON.parse(text);
      } catch (jsonErr) {
        console.error("❌ JSON-fel:", jsonErr);
        throw new Error("Fel vid tolkning av svar från servern");
      }

      if (res.ok) {
        const sorted = [...(data.entries || [])].sort((a, b) => {
          const aTime = new Date(a.checkin_time || a["Checkin-datum"]);
          const bTime = new Date(b.checkin_time || b["Checkin-datum"]);
          return bTime - aTime; // nyast först
        });
        setEntries(sorted);
      } else {
        throw new Error(data?.error || "Fel vid hämtning");
      }
    } catch (err) {
      console.warn("❌ Fel vid historik:", err.message);
      Alert.alert("Fel", "Kunde inte hämta historik: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const getValue = (item, fieldA, fieldB) =>
    item?.[fieldA] || item?.[fieldB] || "-";

  const formatDate = (raw) => {
    if (!raw || raw === "NaN" || raw === "undefined") return "-";
    try {
      const d = new Date(raw);
      if (isNaN(d.getTime())) return "-";
      return d.toLocaleString("sv-SE", {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch (err) {
      return "-";
    }
  };

  const renderItem = ({ item }) => {
    const inTime = getValue(item, "checkin_time", "Checkin-datum");
    const inAddress = getValue(item, "checkin_address", "Checkin-adress");
    const outAddress = getValue(item, "checkout_address", "Checkout-adress");
    const workTime = item?.work_time_minutes || item?.["Total tid (minuter)"];

    return (
      <View style={styles.item}>
        <Text style={styles.date}>{formatDate(inTime)}</Text>
        <Text style={styles.text}>📍 In: {inAddress}</Text>
        <Text style={styles.text}>🚪 Ut: {outAddress}</Text>
        {workTime && workTime !== "NaN" && (
          <Text style={styles.duration}>🕒 Tid: {workTime} min</Text>
        )}
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Historik</Text>
      {loading ? (
        <ActivityIndicator size="large" color="#1abc9c" />
      ) : entries.length === 0 ? (
        <Text style={styles.empty}>Ingen historik ännu</Text>
      ) : (
        <FlatList
          data={entries}
          keyExtractor={(item, index) =>
            `${item?.checkin_time || item?.["Checkin-datum"] || "nodate"}-${index}`
          }
          renderItem={renderItem}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, backgroundColor: '#fff' },
  title: { fontSize: 24, fontWeight: 'bold', marginBottom: 15, color: '#222' },
  item: {
    paddingVertical: 12,
    paddingHorizontal: 10,
    marginBottom: 10,
    backgroundColor: '#f9f9f9',
    borderRadius: 8,
    borderColor: '#ddd',
    borderWidth: 1,
  },
  date: { fontSize: 16, fontWeight: '600', marginBottom: 6 },
  text: { fontSize: 14, color: '#333' },
  duration: { fontSize: 13, color: '#555', marginTop: 4 },
  empty: {
    textAlign: 'center',
    fontStyle: 'italic',
    color: '#777',
    marginTop: 30
  },
});










