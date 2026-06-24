import React, { createContext, useState, useEffect, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

export const LoginContext = createContext();

export const LoginProvider = ({ children }) => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(null);

  const checkLoginStatus = useCallback(async () => {
    try {
      const t = await AsyncStorage.getItem('token');
      setToken(t);
      setIsLoggedIn(!!t);
    } catch (err) {
      setIsLoggedIn(false);
      setToken(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const login = async (newToken) => {
    try {
      await AsyncStorage.setItem('token', newToken);
      setToken(newToken);
      setIsLoggedIn(true);
    } catch (err) {
      console.log("Inloggning misslyckades:", err);
    }
  };

  const logout = async () => {
    try {
      await AsyncStorage.removeItem('token');
      setToken(null);
      setIsLoggedIn(false);
    } catch (err) {
      setToken(null);
      setIsLoggedIn(false);
    }
  };

  useEffect(() => {
    checkLoginStatus();
  }, [checkLoginStatus]);

  return (
    <LoginContext.Provider value={{ isLoggedIn, login, logout, loading, token }}>
      {children}
    </LoginContext.Provider>
  );
};

