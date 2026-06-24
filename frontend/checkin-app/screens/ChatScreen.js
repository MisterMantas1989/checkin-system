import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, TextInput, Button, FlatList,
  StyleSheet, KeyboardAvoidingView, Platform,
  Alert, SafeAreaView
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { API_URL } from '@env';

export default function ChatScreen() {
  const [messages, setMessages] = useState([]);
  const [newMsg, setNewMsg] = useState("");
  const [sending, setSending] = useState(false);
  const flatListRef = useRef(null);

  useEffect(() => {
    loadMessages();
    const interval = setInterval(loadMessages, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadMessages = async () => {
    try {
      const token = await AsyncStorage.getItem("token");
      if (!token) {
        console.warn("❌ Ingen token hittad");
        Alert.alert("Fel", "Du är inte inloggad");
        return;
      }

      console.log("🔁 Hämtar meddelanden...");
      console.log("📡 API:", `${API_URL}/api/messages`);
      console.log("📦 Token:", token);

      const res = await fetch(`${API_URL}/api/messages`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        const text = await res.text();
        console.warn("⚠️ Felaktigt svar:", text);
        throw new Error("Fel vid hämtning av meddelanden");
      }

      const data = await res.json();
      console.log("✅ Svar från backend:", data);
      setMessages((data.messages || []).reverse());
    } catch (err) {
      console.warn("🔥 Fel vid hämtning:", err.message);
      Alert.alert("Fel", "Kunde inte ladda chattmeddelanden");
    }
  };

  const sendMessage = async () => {
    const messageToSend = newMsg.trim();
    if (!messageToSend || sending) return;

    setNewMsg("");
    setSending(true);

    try {
      const token = await AsyncStorage.getItem("token");
      if (!token) {
        Alert.alert("Fel", "Du är inte inloggad");
        return;
      }

      console.log("✉️ Skickar meddelande:", messageToSend);

      const res = await fetch(`${API_URL}/api/messages`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: messageToSend }),
      });

      const data = await res.json();
      console.log("🧾 Svar på POST:", data);

      if (res.ok) {
        await loadMessages();
        setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
      } else {
        Alert.alert("Fel", data?.error || "Kunde inte skicka meddelande");
      }
    } catch (err) {
      console.warn("🔥 Nätverksfel vid POST:", err.message);
      Alert.alert("Fel", "Nätverksproblem vid skickande");
    } finally {
      setSending(false);
    }
  };

  const renderItem = ({ item }) => {
    let time = "";
    try {
      time = new Date(item.timestamp).toLocaleTimeString("sv-SE");
    } catch {
      time = "";
    }

    return (
      <View style={styles.messageContainer}>
        <View style={styles.bubble}>
          <Text style={styles.username}>{item.user || 'Okänd'}:</Text>
          <Text style={styles.msg}>{item.message}</Text>
        </View>
        <Text style={styles.timestamp}>{time}</Text>
      </View>
    );
  };

  return (
    <SafeAreaView style={{ flex: 1 }}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={90}
        style={{ flex: 1 }}
      >
        <View style={styles.container}>
          <FlatList
            ref={flatListRef}
            data={messages}
            keyExtractor={(_, index) => index.toString()}
            renderItem={renderItem}
            contentContainerStyle={{ paddingBottom: 80 }}
            ListEmptyComponent={<Text style={styles.empty}>Inga meddelanden ännu</Text>}
            onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
          />
          <View style={styles.inputRow}>
            <TextInput
              value={newMsg}
              onChangeText={setNewMsg}
              placeholder="Skriv meddelande..."
              style={styles.input}
              returnKeyType="send"
              onSubmitEditing={sendMessage}
            />
            <Button title="Skicka" onPress={sendMessage} disabled={sending} />
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 10 },
  messageContainer: { marginBottom: 16 },
  bubble: {
    backgroundColor: '#eef6f9',
    borderRadius: 12,
    padding: 10,
  },
  username: {
    fontWeight: 'bold',
    marginBottom: 4,
    color: '#005f73',
  },
  msg: { fontSize: 16, color: '#333' },
  timestamp: {
    fontSize: 11,
    color: '#888',
    marginTop: 4,
    marginLeft: 6,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 8,
    backgroundColor: '#f0f0f0',
    borderTopWidth: 1,
    borderColor: '#ccc',
    position: 'absolute',
    bottom: 0,
    width: '100%',
  },
  input: {
    flex: 1,
    borderColor: '#ccc',
    borderWidth: 1,
    marginRight: 8,
    paddingHorizontal: 12,
    borderRadius: 18,
    height: 40,
    backgroundColor: "#fff",
  },
  empty: {
    textAlign: "center",
    marginTop: 20,
    fontStyle: "italic",
    color: "#999"
  }
});












