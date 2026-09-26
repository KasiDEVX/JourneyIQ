# data/

This directory holds **generated data files** (CSV, Parquet, etc.).

## Contents (after running the generator)

| File | Description |
|------|-------------|
| `customers.csv` | 500 synthetic customer records |
| `customer_events.csv` | 3,000–5,000 customer touchpoint events |

## How to regenerate

```bash
# From the project root (JourneyIQ/)
python backend/scripts/generate_data.py
```

## Git note

`*.csv` files are excluded from Git (see `.gitignore`).  
Always regenerate locally or download from shared storage.
