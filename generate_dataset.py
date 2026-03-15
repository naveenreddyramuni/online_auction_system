import pandas as pd
import random

rows = []

categories = [
    "Electronics",
    "Furniture",
    "Vehicle",
    "Real Estate",
    "Antiques"
]

for i in range(5000):

    category = random.choice(categories)

    starting_price = random.randint(100,500000)

    market_avg = starting_price * random.uniform(1.1,2)

    seller_rating = round(random.uniform(3,5),2)

    duration = random.randint(1,7)

    bid_count = random.randint(0,25)

    popularity = random.uniform(0.5,1.5)

    condition_score = random.uniform(0.7,1.3)

    demand_factor = bid_count * popularity

    final_price = (
        starting_price *
        condition_score *
        (1 + demand_factor/10) *
        random.uniform(0.9,1.2)
    )

    rows.append([
        starting_price,
        market_avg,
        seller_rating,
        bid_count,
        duration,
        category,
        popularity,
        condition_score,
        final_price
    ])

columns = [
    "starting_price",
    "market_avg",
    "seller_rating",
    "bid_count",
    "duration",
    "category",
    "popularity",
    "condition_score",
    "final_price"
]

df = pd.DataFrame(rows,columns=columns)

df.to_csv("auction_dataset.csv",index=False)

print("Dataset generated with 5000 rows")