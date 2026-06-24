import React, { useContext } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Image,
  TouchableOpacity,
  Alert,
} from 'react-native';
import {
  createDrawerNavigator,
  DrawerContentScrollView,
} from '@react-navigation/drawer';

import { LoginContext } from '../context/LoginContext';
import CheckinScreen from '../screens/CheckinScreen';
import ChatScreen from '../screens/ChatScreen';
import ScheduleScreen from '../screens/ScheduleScreen';
import HistoryScreen from '../screens/HistoryScreen';

const Drawer = createDrawerNavigator();

export default function DrawerNavigator() {
  return (
    <Drawer.Navigator
      initialRouteName="Checkin"
      drawerContent={(props) => <CustomDrawerContent {...props} />}
    >
      <Drawer.Screen name="Schema" component={ScheduleScreen} />
      <Drawer.Screen name="Historik" component={HistoryScreen} />
      <Drawer.Screen name="Chat" component={ChatScreen} />
      <Drawer.Screen name="Checkin" component={CheckinScreen} />
    </Drawer.Navigator>
  );
}

function CustomDrawerContent(props) {
  const { logout } = useContext(LoginContext);
  const { navigation, state } = props;

  const handleLogout = () => {
    Alert.alert("Logga ut", "Är du säker på att du vill logga ut?", [
      { text: "Avbryt", style: "cancel" },
      { text: "Ja", onPress: async () => await logout() },
    ]);
  };

  const menuItems = [
    { label: '📅 Schema', route: 'Schema' },
    { label: '🕒 Historik', route: 'Historik' },
    { label: '💬 Chat', route: 'Chat' },
    { label: '✅ Checkin', route: 'Checkin' }
  ];

  return (
    <DrawerContentScrollView {...props} contentContainerStyle={styles.scroll}>
      <View style={styles.menuContainer}>
        {menuItems.map((item, index) => {
          const isActive = state.routeNames[state.index] === item.route;
          return (
            <TouchableOpacity
              key={index}
              style={[styles.menuItem, isActive && styles.activeMenu]}
              onPress={() => navigation.navigate(item.route)}
            >
              <Text style={[styles.menuText, isActive && styles.activeText]}>
                {item.label}
              </Text>
            </TouchableOpacity>
          );
        })}

        <TouchableOpacity style={styles.logoutItem} onPress={handleLogout}>
          <Text style={styles.logoutText}>🔒 Logga ut</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.logoContainer}>
        <Image
          source={require('../assets/logo.png')}
          style={styles.logo}
          resizeMode="contain"
        />
      </View>
    </DrawerContentScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: {
    flexGrow: 1,
    justifyContent: 'space-between',
    paddingTop: 50,
    paddingBottom: 50,
  },
  menuContainer: {
    paddingHorizontal: 20,
    paddingTop: 20,
  },
  menuItem: {
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderRadius: 12,
    marginBottom: 12,
  },
  activeMenu: {
    backgroundColor: '#e6f0ff',
  },
  menuText: {
    fontSize: 16,
  },
  activeText: {
    fontWeight: 'bold',
    color: '#007aff',
  },
  logoutItem: {
    paddingVertical: 14,
    paddingHorizontal: 20,
    marginTop: 30,
    borderRadius: 12,
    backgroundColor: '#ffecec',
  },
  logoutText: {
    color: 'red',
    fontWeight: '600',
    fontSize: 16,
  },
  logoContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 40,
    marginBottom: 30,
  },
  logo: {
    width: 380,
    height: 300,
    borderRadius: 20,
  },
});


