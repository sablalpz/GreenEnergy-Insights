"""
=================================================================================
MOTOR DE ANALÍTICA AVANZADA PARA DATOS DE ENERGÍA
=================================================================================

Este módulo integra:
1. Modelos de Predicción (Prophet, Random Forest, Gradient Boosting, LSTM)
2. Detector de Anomalías (Z-Score, IQR, Isolation Forest, Cambios Bruscos)
3. Sistema de Métricas (MAPE, SMAPE, RMSE, MAE, R², MSE, Drift Detection)

Uso:
    from motor_analitica import MotorAnalitica
    
    motor = MotorAnalitica()
    motor.entrenar(df_datos)
    predicciones = motor.predecir(24)
    anomalias = motor.detectar_anomalias(df_datos)
    metricas = motor.evaluar()
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from enum import Enum
import warnings
import pickle
import os
from pathlib import Path

# Importaciones para modelos
from prophet import Prophet
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, IsolationForest
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import tensorflow as tf
from tensorflow import keras

warnings.filterwarnings('ignore')


# =============================================================================
# ENUMS Y CONSTANTES
# =============================================================================

class TipoModelo(Enum):
    PROPHET = "prophet"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    LSTM = "lstm"


class TipoAnomalia(Enum):
    PICO = "pico"
    CAIDA = "caida"
    CAMBIO_BRUSCO = "cambio_brusco"
    PATRON_ANOMALO = "patron_anomalo"


# =============================================================================
# CLASE PRINCIPAL: MOTOR DE ANALÍTICA
# =============================================================================

class MotorAnalitica:
    """
    Motor completo de analítica avanzada que integra predicción, 
    detección de anomalías y evaluación de métricas.
    """
    
    def __init__(self, tipo_modelo='prophet', umbral_anomalia=3.0):
        """
        Args:
            tipo_modelo: 'prophet', 'random_forest', 'gradient_boosting', 'lstm'
            umbral_anomalia: Umbral para detección de anomalías (desv. estándar)
        """
        self.tipo_modelo = tipo_modelo
        self.umbral_anomalia = umbral_anomalia
        self.modelo = None
        self.scaler = None
        self.entrenado = False
        self.metricas_test = {}
        self.df_train = None
        self.df_test = None
        
    # =========================================================================
    # MÓDULO 1: PREDICCIÓN
    # =========================================================================
    
    def entrenar(self, df, test_size=0.2):
        """
        Entrena el modelo de predicción con los datos proporcionados.
        
        Args:
            df: DataFrame con columnas 'timestamp' y 'value'
            test_size: Proporción de datos para test (0.2 = 20%)
            
        Returns:
            dict con información del entrenamiento y métricas
        """
        if len(df) < 100:
            raise ValueError(f"Se necesitan al menos 100 registros para entrenar. Tienes {len(df)}")
        
        # Validar columnas requeridas
        if 'timestamp' not in df.columns or 'value' not in df.columns:
            raise ValueError("El DataFrame debe tener columnas 'timestamp' y 'value'")
        
        # Dividir en train/test
        split_idx = int(len(df) * (1 - test_size))
        self.df_train = df.iloc[:split_idx].copy()
        self.df_test = df.iloc[split_idx:].copy()
        
        print(f"Entrenando modelo {self.tipo_modelo}...")
        print(f"Datos train: {len(self.df_train)}, test: {len(self.df_test)}")
        
        # Entrenar según el tipo de modelo
        if self.tipo_modelo == 'prophet':
            self._entrenar_prophet()
        elif self.tipo_modelo == 'random_forest':
            self._entrenar_random_forest()
        elif self.tipo_modelo == 'gradient_boosting':
            self._entrenar_gradient_boosting()
        elif self.tipo_modelo == 'lstm':
            self._entrenar_lstm()
        else:
            raise ValueError(f"Tipo de modelo no soportado: {self.tipo_modelo}")
        
        self.entrenado = True
        
        # Evaluar en test
        predicciones_test = self.predecir(horizonte_horas=len(self.df_test))
        self.metricas_test = self._calcular_metricas(
            self.df_test['value'].values,
            predicciones_test['prediccion'].values
        )
        
        print(f"Modelo {self.tipo_modelo} entrenado exitosamente!")
        
        return {
            'modelo': self.tipo_modelo,
            'registros_train': len(self.df_train),
            'registros_test': len(self.df_test),
            'metricas_test': self.metricas_test,
            'entrenado': self.entrenado
        }
    
    def _entrenar_prophet(self):
        """Entrena modelo Prophet"""
        df_prophet = self.df_train.rename(columns={'timestamp': 'ds', 'value': 'y'})
        self.modelo = Prophet(
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10,
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=False
        )
        self.modelo.fit(df_prophet)
    
    def _entrenar_random_forest(self):
        """Entrena modelo Random Forest"""
        X_train = self._crear_features(self.df_train)
        y_train = self.df_train['value'].values
        
        self.modelo = RandomForestRegressor(
            n_estimators=100,
            max_depth=20,
            random_state=42,
            n_jobs=-1
        )
        self.modelo.fit(X_train, y_train)
    
    def _entrenar_gradient_boosting(self):
        """Entrena modelo Gradient Boosting"""
        X_train = self._crear_features(self.df_train)
        y_train = self.df_train['value'].values
        
        self.modelo = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        self.modelo.fit(X_train, y_train)
    
    def _entrenar_lstm(self):
        """Entrena modelo LSTM"""
        # Normalizar datos
        self.scaler = MinMaxScaler()
        valores_norm = self.scaler.fit_transform(
            self.df_train[['value']].values
        )
        
        # Crear secuencias
        X, y = self._crear_secuencias_lstm(valores_norm, seq_length=24)
        
        # Crear modelo LSTM
        self.modelo = keras.Sequential([
            keras.layers.LSTM(50, activation='relu', return_sequences=True, 
                             input_shape=(X.shape[1], X.shape[2])),
            keras.layers.Dropout(0.2),
            keras.layers.LSTM(50, activation='relu'),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(1)
        ])
        
        self.modelo.compile(optimizer='adam', loss='mse')
        self.modelo.fit(X, y, epochs=50, batch_size=32, verbose=0)
    
    def predecir(self, horizonte_horas=24):
        """
        Genera predicciones para las próximas N horas.
        
        Args:
            horizonte_horas: Número de horas a predecir
            
        Returns:
            DataFrame con predicciones y opcionalmente intervalos de confianza
        """
        if not self.entrenado:
            raise ValueError("El modelo no ha sido entrenado. Llama primero a entrenar()")
        
        ultimo_timestamp = self.df_train['timestamp'].max()
        
        if self.tipo_modelo == 'prophet':
            return self._predecir_prophet(horizonte_horas, ultimo_timestamp)
        elif self.tipo_modelo in ['random_forest', 'gradient_boosting']:
            return self._predecir_sklearn(horizonte_horas, ultimo_timestamp)
        elif self.tipo_modelo == 'lstm':
            return self._predecir_lstm(horizonte_horas, ultimo_timestamp)
    
    def _predecir_prophet(self, horizonte_horas, ultimo_timestamp):
        """Predicciones con Prophet"""
        future = self.modelo.make_future_dataframe(periods=horizonte_horas, freq='H')
        forecast = self.modelo.predict(future)
        
        # Filtrar solo predicciones futuras
        forecast_futuro = forecast[forecast['ds'] > ultimo_timestamp].head(horizonte_horas)
        
        return pd.DataFrame({
            'timestamp': forecast_futuro['ds'].values,
            'prediccion': forecast_futuro['yhat'].values,
            'limite_inferior': forecast_futuro['yhat_lower'].values,
            'limite_superior': forecast_futuro['yhat_upper'].values
        })
    
    def _predecir_sklearn(self, horizonte_horas, ultimo_timestamp):
        """Predicciones con Random Forest o Gradient Boosting"""
        predicciones = []
        timestamp_actual = ultimo_timestamp
        
        for _ in range(horizonte_horas):
            timestamp_actual += timedelta(hours=1)
            features = self._crear_features_timestamp(timestamp_actual)
            pred = self.modelo.predict(features)[0]
            predicciones.append({
                'timestamp': timestamp_actual,
                'prediccion': pred
            })
        
        return pd.DataFrame(predicciones)
    
    def _predecir_lstm(self, horizonte_horas, ultimo_timestamp):
        """Predicciones con LSTM"""
        # Obtener últimas 24 horas normalizadas
        ultimos_valores = self.df_train['value'].tail(24).values.reshape(-1, 1)
        ultimos_valores_norm = self.scaler.transform(ultimos_valores)
        
        predicciones = []
        secuencia = ultimos_valores_norm.copy()
        timestamp_actual = ultimo_timestamp
        
        for _ in range(horizonte_horas):
            timestamp_actual += timedelta(hours=1)
            X_pred = secuencia[-24:].reshape(1, 24, 1)
            pred_norm = self.modelo.predict(X_pred, verbose=0)[0]
            pred = self.scaler.inverse_transform(pred_norm.reshape(-1, 1))[0][0]
            
            predicciones.append({
                'timestamp': timestamp_actual,
                'prediccion': pred
            })
            
            # Actualizar secuencia
            secuencia = np.append(secuencia, pred_norm.reshape(1, 1), axis=0)
        
        return pd.DataFrame(predicciones)
    
    # =========================================================================
    # MÓDULO 2: DETECCIÓN DE ANOMALÍAS
    # =========================================================================
    
    def detectar_anomalias(self, df, metodos=['zscore', 'iqr', 'isolation_forest']):
        """
        Detecta anomalías usando múltiples métodos.
        
        Args:
            df: DataFrame con columnas 'timestamp' y 'value'
            metodos: Lista de métodos a usar
            
        Returns:
            DataFrame con anomalías detectadas
        """
        todas_anomalias = []
        
        for metodo in metodos:
            if metodo == 'zscore':
                anomalias = self._detectar_zscore(df)
            elif metodo == 'iqr':
                anomalias = self._detectar_iqr(df)
            elif metodo == 'isolation_forest':
                anomalias = self._detectar_isolation_forest(df)
            elif metodo == 'cambios_bruscos':
                anomalias = self._detectar_cambios_bruscos(df)
            else:
                continue
            
            if len(anomalias) > 0:
                anomalias['metodo_deteccion'] = metodo
                todas_anomalias.append(anomalias)
        
        if not todas_anomalias:
            return pd.DataFrame()
        
        # Combinar y eliminar duplicados
        df_anomalias = pd.concat(todas_anomalias, ignore_index=True)
        df_anomalias = df_anomalias.drop_duplicates(subset=['timestamp'], keep='first')
        
        return df_anomalias.sort_values('timestamp').reset_index(drop=True)
    
    def _detectar_zscore(self, df):
        """Detección usando Z-Score"""
        mean = df['value'].mean()
        std = df['value'].std()
        
        df_clean = df[df['value'].notna()].copy()
        df_clean['zscore'] = np.abs((df_clean['value'] - mean) / std)
        df_clean['es_anomalia'] = df_clean['zscore'] > self.umbral_anomalia
        
        anomalias = df_clean[df_clean['es_anomalia']].copy()
        
        if len(anomalias) > 0:
            anomalias['severidad'] = anomalias['zscore'].apply(
                lambda x: 'critica' if x > 4 else 'alta' if x > 3.5 else 'media'
            )
            anomalias['tipo_anomalia'] = anomalias['value'].apply(
                lambda x: TipoAnomalia.PICO.value if x > mean else TipoAnomalia.CAIDA.value
            )
            anomalias['anomaly_score'] = anomalias['zscore']
        
        return anomalias[['timestamp', 'value', 'tipo_anomalia', 'severidad', 'anomaly_score']]
    
    def _detectar_iqr(self, df):
        """Detección usando Rango Intercuartílico (IQR)"""
        Q1 = df['value'].quantile(0.25)
        Q3 = df['value'].quantile(0.75)
        IQR = Q3 - Q1
        
        limite_inferior = Q1 - 1.5 * IQR
        limite_superior = Q3 + 1.5 * IQR
        
        df_clean = df[df['value'].notna()].copy()
        df_clean['es_anomalia'] = (df_clean['value'] < limite_inferior) | (df_clean['value'] > limite_superior)
        
        anomalias = df_clean[df_clean['es_anomalia']].copy()
        
        if len(anomalias) > 0:
            anomalias['severidad'] = anomalias['value'].apply(
                lambda x: 'critica' if x < Q1 - 3*IQR or x > Q3 + 3*IQR else 'alta'
            )
            anomalias['tipo_anomalia'] = anomalias['value'].apply(
                lambda x: TipoAnomalia.CAIDA.value if x < limite_inferior else TipoAnomalia.PICO.value
            )
            anomalias['anomaly_score'] = np.abs(anomalias['value'] - df['value'].median()) / IQR
        
        return anomalias[['timestamp', 'value', 'tipo_anomalia', 'severidad', 'anomaly_score']]
    
    def _detectar_isolation_forest(self, df):
        """Detección usando Isolation Forest"""
        df_clean = df[df['value'].notna()].copy()
        
        if len(df_clean) < 10:
            return pd.DataFrame()
        
        modelo_if = IsolationForest(contamination=0.1, random_state=42)
        predicciones = modelo_if.fit_predict(df_clean[['value']])
        scores = modelo_if.score_samples(df_clean[['value']])
        
        df_clean['es_anomalia'] = predicciones == -1
        df_clean['anomaly_score'] = -scores
        
        anomalias = df_clean[df_clean['es_anomalia']].copy()
        
        if len(anomalias) > 0:
            anomalias['severidad'] = anomalias['anomaly_score'].apply(
                lambda x: 'critica' if x > 0.7 else 'alta' if x > 0.5 else 'media'
            )
            anomalias['tipo_anomalia'] = TipoAnomalia.PATRON_ANOMALO.value
        
        return anomalias[['timestamp', 'value', 'tipo_anomalia', 'severidad', 'anomaly_score']]
    
    def _detectar_cambios_bruscos(self, df):
        """Detección de cambios bruscos entre valores consecutivos"""
        df_clean = df[df['value'].notna()].copy()
        df_clean = df_clean.sort_values('timestamp')
        
        df_clean['diff'] = df_clean['value'].diff().abs()
        umbral_cambio = df_clean['diff'].std() * 2
        
        df_clean['es_anomalia'] = df_clean['diff'] > umbral_cambio
        anomalias = df_clean[df_clean['es_anomalia']].copy()
        
        if len(anomalias) > 0:
            anomalias['severidad'] = anomalias['diff'].apply(
                lambda x: 'critica' if x > umbral_cambio * 2 else 'alta'
            )
            anomalias['tipo_anomalia'] = TipoAnomalia.CAMBIO_BRUSCO.value
            anomalias['anomaly_score'] = anomalias['diff'] / umbral_cambio
        
        return anomalias[['timestamp', 'value', 'tipo_anomalia', 'severidad', 'anomaly_score']]
    
    # =========================================================================
    # MÓDULO 3: MÉTRICAS Y EVALUACIÓN
    # =========================================================================
    
    def _calcular_metricas(self, y_real, y_pred):
        """Calcula métricas de evaluación del modelo"""
        mae = mean_absolute_error(y_real, y_pred)
        mse = mean_squared_error(y_real, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_real, y_pred)
        
        # MAPE (Mean Absolute Percentage Error)
        mape = np.mean(np.abs((y_real - y_pred) / y_real)) * 100
        
        # SMAPE (Symmetric Mean Absolute Percentage Error)
        smape = np.mean(2 * np.abs(y_pred - y_real) / (np.abs(y_real) + np.abs(y_pred))) * 100
        
        return {
            'MAE': mae,
            'MSE': mse,
            'RMSE': rmse,
            'R2': r2,
            'MAPE': mape,
            'SMAPE': smape
        }
    
    def obtener_metricas(self):
        """Retorna las métricas del modelo"""
        if not self.entrenado:
            raise ValueError("El modelo no ha sido entrenado")
        return self.metricas_test
    
    # =========================================================================
    # MÉTODOS AUXILIARES
    # =========================================================================
    
    def _crear_features(self, df):
        """Crea features para modelos sklearn"""
        df_features = df.copy()
        df_features['hora'] = df_features['timestamp'].dt.hour
        df_features['dia_semana'] = df_features['timestamp'].dt.dayofweek
        df_features['mes'] = df_features['timestamp'].dt.month
        df_features['dia_mes'] = df_features['timestamp'].dt.day
        df_features['fin_semana'] = (df_features['dia_semana'] >= 5).astype(int)
        
        return df_features[['hora', 'dia_semana', 'mes', 'dia_mes', 'fin_semana']].values
    
    def _crear_features_timestamp(self, timestamp):
        """Crea features para un timestamp específico"""
        return np.array([[
            timestamp.hour,
            timestamp.weekday(),
            timestamp.month,
            timestamp.day,
            int(timestamp.weekday() >= 5)
        ]])
    
    def _crear_secuencias_lstm(self, data, seq_length=24):
        """Crea secuencias para entrenamiento LSTM"""
        X, y = [], []
        for i in range(len(data) - seq_length):
            X.append(data[i:i+seq_length])
            y.append(data[i+seq_length])
        return np.array(X), np.array(y)
    
    def guardar_modelo(self, ruta='models/motor_analitica.pkl'):
        """Guarda el modelo entrenado"""
        if not self.entrenado:
            raise ValueError("El modelo no ha sido entrenado")
        
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        
        with open(ruta, 'wb') as f:
            pickle.dump(self, f)
        
        print(f"Modelo guardado en: {ruta}")
    
    @staticmethod
    def cargar_modelo(ruta='models/motor_analitica.pkl'):
        """Carga un modelo previamente guardado"""
        with open(ruta, 'rb') as f:
            modelo = pickle.load(f)
        
        print(f"Modelo cargado desde: {ruta}")
        return modelo


# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def crear_dataframe_ejemplo(num_registros=200):
    """
    Crea un DataFrame de ejemplo para pruebas.
    
    Args:
        num_registros: Número de registros a generar
        
    Returns:
        DataFrame con datos sintéticos realistas
    """
    inicio = datetime.now() - timedelta(hours=num_registros)
    timestamps = [inicio + timedelta(hours=i) for i in range(num_registros)]
    
    # Generar valores con patrón diario realista
    valores = []
    for ts in timestamps:
        hora = ts.hour
        # Patrón de demanda típico
        base = 100 + 20 * np.sin(2 * np.pi * hora / 24)
        ruido = np.random.normal(0, 5)
        valores.append(base + ruido)
    
    return pd.DataFrame({
        'timestamp': timestamps,
        'value': valores
    })


if __name__ == "__main__":
    print("="*80)
    print("MOTOR DE ANALÍTICA AVANZADA")
    print("="*80)
    print("\nEjemplo de uso:\n")
    print("from motor_analitica import MotorAnalitica")
    print("motor = MotorAnalitica(tipo_modelo='prophet')")
    print("motor.entrenar(df_datos)")
    print("predicciones = motor.predecir(24)")
    print("anomalias = motor.detectar_anomalias(df_datos)")
    print("\nMódulo listo para usar.")
