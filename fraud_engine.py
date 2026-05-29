import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder

def detect_duplicates(df):
    flagged = []
    df_sorted = df.sort_values('timestamp')
    for i, row in df_sorted.iterrows():
        window_start = row['timestamp'] - pd.Timedelta(minutes=5)
        window_end   = row['timestamp'] + pd.Timedelta(minutes=5)
        same = df_sorted[
            (df_sorted['vendor_id']  == row['vendor_id']) &
            (df_sorted['amount']     == row['amount']) &
            (df_sorted['timestamp']  >= window_start) &
            (df_sorted['timestamp']  <= window_end) &
            (df_sorted['transaction_id'] != row['transaction_id'])
        ]
        if len(same) > 0:
            flagged.append(row['transaction_id'])
    return flagged

def detect_after_hours(df):
    hours = pd.to_datetime(df['timestamp']).dt.hour
    mask  = (hours >= 23) | (hours < 6)
    return df[mask]['transaction_id'].tolist()

def detect_just_below_threshold(df):
    thresholds = [10000, 50000, 100000]
    flagged = []
    for t in thresholds:
        mask = (df['amount'] >= t * 0.95) & (df['amount'] < t)
        flagged.extend(df[mask]['transaction_id'].tolist())
    return flagged

def detect_high_risk_vendors(df):
    vendor_stats = df.groupby('vendor_id').agg(
        total=('transaction_id', 'count'),
        chargebacks=('chargeback_flag', 'sum'),
        refunds=('refund_flag', 'sum')
    ).reset_index()
    vendor_stats['chargeback_rate'] = \
        vendor_stats['chargebacks'] / vendor_stats['total']
    risky = vendor_stats[vendor_stats['chargeback_rate'] > 0.30]
    flagged = df[df['vendor_id'].isin(risky['vendor_id'])
                ]['transaction_id'].tolist()
    return flagged, vendor_stats

def detect_ml_anomalies(df):
    try:
        features = df[['amount', 'refund_flag', 'chargeback_flag']].copy()
        features['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        le = LabelEncoder()
        features['method_enc'] = le.fit_transform(
            df['payment_method'].astype(str))
        clf = IsolationForest(contamination=0.05, random_state=42)
        preds = clf.fit_predict(features)
        anomaly_ids = df[preds == -1]['transaction_id'].tolist()
        return anomaly_ids
    except Exception:
        return []

def calculate_risk_scores(df):
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    dup_ids    = set(detect_duplicates(df))
    ah_ids     = set(detect_after_hours(df))
    jb_ids     = set(detect_just_below_threshold(df))
    hrv_ids, vendor_stats = detect_high_risk_vendors(df)
    hrv_ids    = set(hrv_ids)
    ml_ids     = set(detect_ml_anomalies(df))

    def score(tx_id):
        s = 0
        flags = []
        if tx_id in dup_ids:
            s += 1; flags.append("Duplicate")
        if tx_id in ah_ids:
            s += 1; flags.append("After Hours")
        if tx_id in jb_ids:
            s += 1; flags.append("Just-Below Threshold")
        if tx_id in hrv_ids:
            s += 1; flags.append("High Risk Vendor")
        if tx_id in ml_ids:
            s += 1; flags.append("ML Anomaly")
        return s, ", ".join(flags) if flags else "Clean"

    scores = df['transaction_id'].apply(
        lambda x: pd.Series(score(x),
                            index=['risk_score', 'flags']))
    df = pd.concat([df, scores], axis=1)

    df['risk_level'] = df['risk_score'].apply(
        lambda x: "🔴 High Risk"   if x >= 3
             else "🟡 Medium Risk" if x >= 2
             else "🟢 Low Risk"
    )
    return df, vendor_stats