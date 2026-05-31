import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_nilepay_data(n_transactions=1000, seed=42):
    np.random.seed(seed)
    random.seed(seed)

    cities = ['Cairo', 'Alexandria', 'Giza', 'Mansoura',
              'Aswan', 'Luxor', 'Tanta', 'Suez']
    methods = ['Wallet', 'Card', 'Bank Transfer', 'QR Code']
    devices = ['Mobile', 'Desktop', 'POS Terminal', 'ATM']
    vendors = [f'Vendor_{chr(65+i)}' for i in range(15)]
    statuses = ['Approved', 'Failed', 'Pending', 'Reversed']
    failure_reasons = ['Insufficient Funds', 'Timeout',
                       'Gateway Error', 'Invalid Card', None]

    base_time = datetime(2024, 1, 1)
    records = []

    for i in range(n_transactions):
        is_fraud = random.random() < 0.15
        ts = base_time + timedelta(
            days=random.randint(0, 180),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )

        if is_fraud:
            fraud_type = random.choice([
                'duplicate', 'after_hours',
                'just_below', 'high_chargeback'
            ])
            if fraud_type == 'duplicate':
                amount = round(random.choice([5000, 10000, 25000, 50000]), 2)
                ts = base_time + timedelta(
                    days=random.randint(0, 180),
                    hours=random.randint(9, 17),
                    minutes=random.randint(0, 4)
                )
                vendor = random.choice(vendors[:3])
                chargeback = 0
                refund = 0
            elif fraud_type == 'after_hours':
                amount = round(random.uniform(1000, 80000), 2)
                ts = base_time + timedelta(
                    days=random.randint(0, 180),
                    hours=random.choice([0, 1, 2, 3, 4, 23]),
                    minutes=random.randint(0, 59)
                )
                vendor = random.choice(vendors)
                chargeback = random.choice([0, 1])
                refund = random.choice([0, 1])
            elif fraud_type == 'just_below':
                threshold = random.choice([10000, 50000, 100000])
                amount = round(threshold * random.uniform(0.95, 0.999), 2)
                ts = base_time + timedelta(
                    days=random.randint(0, 180),
                    hours=random.randint(9, 17),
                    minutes=random.randint(0, 59)
                )
                vendor = random.choice(vendors)
                chargeback = 0
                refund = random.choice([0, 1])
            else:
                amount = round(random.uniform(500, 30000), 2)
                ts = base_time + timedelta(
                    days=random.randint(0, 180),
                    hours=random.randint(9, 17),
                    minutes=random.randint(0, 59)
                )
                vendor = random.choice(vendors[:2])
                chargeback = 1
                refund = 1
        else:
            amount = round(random.expovariate(1/3000) + 100, 2)
            amount = min(amount, 200000)
            ts = base_time + timedelta(
                days=random.randint(0, 180),
                hours=random.randint(8, 22),
                minutes=random.randint(0, 59)
            )
            vendor = random.choice(vendors)
            chargeback = 1 if random.random() < 0.03 else 0
            refund = 1 if random.random() < 0.05 else 0

        status = random.choices(
            statuses,
            weights=[0.75, 0.15, 0.05, 0.05]
        )[0]
        failure = random.choice(failure_reasons[:4]) \
            if status == 'Failed' else None

        records.append({
            'transaction_id':     f'TX{10000+i}',
            'customer_id':        f'CUST{random.randint(1000, 1200)}',
            'vendor_id':          vendor,
            'amount':             amount,
            'payment_method':     random.choice(methods),
            'timestamp':          ts,
            'city':               random.choice(cities),
            'device_type':        random.choice(devices),
            'transaction_status': status,
            'refund_flag':        refund,
            'chargeback_flag':    chargeback,
            'failure_reason':     failure,
            'is_fraud_planted':   is_fraud
        })

    # زرع duplicates واضحة
    for _ in range(30):
        base_rec = random.choice(records)
        dup = base_rec.copy()
        dup['transaction_id'] = f'TX{20000+_}'
        dup['timestamp'] = base_rec['timestamp'] + timedelta(minutes=random.randint(1, 4))
        records.append(dup)

    df = pd.DataFrame(records)
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df