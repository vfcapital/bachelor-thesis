import pandas as pd
import yaml


def single_trade_files_to_one():
    with open("collections.yaml", "r") as stream:
        collections = yaml.safe_load(stream)
    trades_list = []
    for collection in list(collections.keys()):
        path = collections[collection]["nft_trades_path"]
        if path != None:
            df = pd.read_csv("etherscan_csv_files/" + path)
            trades_list.append(df)
    return pd.concat(trades_list).drop("Unnamed: 0", axis=1)


def keep_multiple_trades_nfts(df):
    df_formatted = df[
        (df.nft_id.isin(list(df[df.nft_id.duplicated(keep=False)].nft_id.unique())))
    ]
    return df_formatted


def format_trades_df(df):
    df_formatted = (
        df.drop("Unnamed: 0", axis=1)
        .reset_index(drop=True)
        .rename(columns={"Date Time (UTC)": "timestamp", "Txn hash": "hash"})
    )
    df_formatted["nft_id"] = (
        df_formatted["NFT"] + "_" + df_formatted["Token ID"].astype(str)
    )
    df_formatted["timestamp"] = pd.to_datetime(df_formatted["timestamp"], utc=True)
    df_formatted["Price"] = df_formatted["Price"].str.replace("WETH", "ETH")
    df_formatted["date"] = df_formatted["timestamp"].dt.date
    df_formatted = (
        df_formatted[
            (df_formatted["Market"] == "OpenSea")
            & (df_formatted["Action"] == "Bought")
            & (df_formatted["Type"] == 721)
            & (df_formatted["Price"] != "0 ETH ")
            & (df_formatted.Price.str.contains("$"))
            & (df_formatted["Price"].str.contains("ETH"))
        ]
        .pipe(keep_multiple_trades_nfts)
        .drop_duplicates(subset=["timestamp", "nft_id"], keep="first")
        .drop_duplicates(subset=["Txn Hash", "nft_id"], keep="first")
    )
    df_formatted["price_usd"] = (
        df_formatted["Price"]
        .apply(lambda st: st[st.find("($") + 2 : st.find(")")])
        .str.replace(",", "")
        .astype(float)
    )
    df_formatted["price_eth"] = (
        df_formatted["Price"]
        .str.split()
        .apply(lambda x: x[0])
        .str.replace(",", "")
        .astype(float)
    )
    df_formatted = (
        df_formatted[(df_formatted.price_eth < 1000) & (df_formatted.price_usd > 0)]
        .pipe(keep_multiple_trades_nfts)
        .sort_values(["nft_id", "timestamp"])
        .reset_index(drop=True)
        .drop("UnixTimestamp", axis=1)
    )
    return df_formatted[["date", "nft_id", "price_eth", "price_usd", "NFT", "Buyer"]]


def plot_total_nft_volume(nft_trades):
    return nft_trades[["date", "price_usd"]].rename(columns={"price_usd": "USD"}).groupby(
        "date"
    ).sum().plot(grid=True, logy=True, title="Total NFT volume per [log values]")


def calculated_trade_profits(nft_trades):
    profits = nft_trades.copy()
    return profits